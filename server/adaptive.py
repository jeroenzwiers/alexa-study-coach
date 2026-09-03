"""Reading the student, not just the answer.

Two things a human tutor does that a quiz does not: push harder when it is all
going in too easily, and back off - or hand over a hint - when the student is
losing heart. Both need a read on HOW an answer arrived, not merely whether it
was right.

WHERE THAT SIGNAL COMES FROM
----------------------------
It would be convenient to read the tone of voice directly. We cannot. The
Alexa+ MCP toolkit hands a server tool arguments, and nothing in its documented
contract carries audio, prosody or affect - the server never hears the student.
So this module reads what it can genuinely see, and asks the platform for the
rest:

    observed here    the transcript itself (hesitation and give-up markers),
                     how long the answer took, and the run of right and wrong.
    asked of Alexa+  an optional `manner` argument on submit_answer. Alexa+ did
                     hear the student, so the tool description invites it to
                     report what the student DID - paused, asked to stop,
                     answered instantly - and never how they felt. It is a hint
                     that sharpens the read, never a requirement: every rule
                     below works with it absent, the same way the screen card is
                     additive to voice.

That split is the honest version of "notice that the student is struggling",
it puts each half where it belongs: perception with the platform that has the
audio, policy with the server that has the history.

No model call happens here either. This is a weighted sum over signals already
in hand by the time the answer has been graded - microseconds, inside the same
500 ms round trip.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

# Sounds of thinking out loud. The grader throws these away as filler; here they
# are the point - the same token means "ignore me" to one half of the server and
# "this was effortful" to the other.
_HESITATION = frozenset({"um", "umm", "uh", "uhh", "erm", "err", "er", "hmm", "hm"})

# Hedges. Weaker evidence than a stall, but they stack.
_UNSURE = frozenset({
    "maybe", "perhaps", "probably", "guess", "guessing", "dunno",
    "unsure", "possibly", "something", "whatever",
})

# Giving up outright. Checked as phrases, since the words alone are innocent.
_GIVE_UP = (
    "i don't know", "i dont know", "don't know", "dont know", "no idea",
    "no clue", "not a clue", "give up", "giving up", "i quit", "skip",
    "pass on this", "next one", "can we stop", "i'm done", "im done",
)

# What Alexa+ may report in `manner`. These are DELIBERATELY descriptions of
# observable conversational behaviour, not emotion labels: "long pause",
# "asked to stop", "answered instantly". Two reasons, and the second is the
# binding one.
#
#   It works better. "Paused for eight seconds and then asked to move on" is
#   something the platform can actually observe. "Frustrated" is a guess about
#   an inner state, and Recital 44 of the EU AI Act is blunt about how well
#   those guesses generalise.
#
#   It stays inside the law. Article 5(1)(f) prohibits AI systems that infer
#   emotions of a person in the workplace or in education, in force since
#   2 February 2025, with only medical and safety exceptions. A revision coach
#   is squarely in that domain. Reading behaviour is not inferring emotion, and
#   this module never acts on an emotion word even if one arrives.
#
# The signal is not weaker for it. Everything the session needs to decide - push,
# hold, or ease off - is carried by what the student DID.
_MANNER_EFFORTFUL = (
    "long pause", "paused", "pause before", "silence", "went quiet", "no answer",
    "took a while", "took a long time", "slow to answer", "slowly", "very slow",
    "trailing off", "tailed off", "false start", "started over", "restarted",
    "several attempts", "asked to stop", "asked for a break", "wants to stop",
    "asked to move on", "asked to skip", "gave up", "giving up",
    "asked me to repeat", "repeated the question", "mumbled", "muttered",
    "sighed", "sigh",
)
_MANNER_FLUENT = (
    "instant", "instantly", "immediately", "straight away", "right away",
    "without hesitating", "no hesitation", "no pause", "quick", "quickly",
    "fast", "answered over", "interrupted", "before i finished",
    "answered early", "steady", "fluent", "unprompted",
)
_MANNER_HESITANT = (
    "hesitant", "hesitated", "tentative", "long pause", "paused", "pause before",
    "trailing off", "tailed off", "false start", "restarted", "slowly",
    "thinking out loud", "changed their answer", "changed the answer",
)

# Alexa reads the question aloud before the student can begin, so wall-clock
# time between turns is mostly speech. Subtract an estimate of it before calling
# anything slow. ~2.6 words per second, plus a beat of overhead.
_MS_PER_WORD = 380
_SPEECH_OVERHEAD_MS = 700

_SLOW_THINKING_MS = 6000
_QUICK_THINKING_MS = 1800

# Above this the student is struggling in a way worth acting on; below the lower
# mark they are settled enough to be pushed. The gap between them is deliberate:
# it stops the session oscillating between easier and harder every turn.
STRAINED = 0.60
SETTLED = 0.25

_DECAY = 0.72          # strain eases as the session recovers
_STRETCH_STREAK = 3    # consecutive correct answers before offering a step up

MIN_DIFFICULTY = 1
MAX_DIFFICULTY = 3
MIN_SCAFFOLD = 0
MAX_SCAFFOLD = 2


@dataclass(frozen=True)
class Signals:
    """What one answer revealed about the student's state, beyond correctness."""

    hesitant: bool = False
    unsure: bool = False
    gave_up: bool = False
    slow: bool = False
    quick: bool = False
    manner: str | None = None
    manner_effortful: bool = False
    manner_fluent: bool = False
    thinking_ms: int | None = None

    @property
    def strained(self) -> bool:
        return self.gave_up or self.manner_effortful or (self.hesitant and self.slow)


@dataclass(frozen=True)
class Adjustment:
    """What the session should do differently on the next question."""

    direction: str          # "ease", "stretch" or "hold"
    difficulty: int
    scaffold: int           # 0 ask plainly, 1 add a hint, 2 offer two options
    strain: float
    line: str | None = None  # something to say about the change, if anything


def expected_speech_ms(question: str) -> int:
    """Roughly how long Alexa spends reading a question aloud."""
    words = len((question or "").split())
    return _SPEECH_OVERHEAD_MS + words * _MS_PER_WORD


def read_signals(
    response: str,
    *,
    question: str = "",
    elapsed_ms: float | None = None,
    manner: str | None = None,
) -> Signals:
    """Everything observable about how this answer arrived.

    `response` is the raw transcript, deliberately unnormalised - the filler the
    grader discards is exactly the evidence wanted here.
    """
    raw = (response or "").lower().strip()
    # Split on word characters, not whitespace: a transcript arrives as
    # "um, uh, the... mitochondria?", and "um," is not "um".
    words = set(re.findall(r"[a-z]+", raw))

    gave_up = any(phrase in raw for phrase in _GIVE_UP)
    hesitant = bool(words & _HESITATION)
    unsure = bool(words & _UNSURE)

    thinking_ms = None
    slow = quick = False
    if elapsed_ms is not None:
        thinking_ms = int(elapsed_ms - expected_speech_ms(question))
        slow = thinking_ms > _SLOW_THINKING_MS
        quick = thinking_ms < _QUICK_THINKING_MS

    hint = (manner or "").lower()
    manner_effortful = any(k in hint for k in _MANNER_EFFORTFUL)
    manner_fluent = any(k in hint for k in _MANNER_FLUENT)
    if any(k in hint for k in _MANNER_HESITANT):
        hesitant = True

    return Signals(
        hesitant=hesitant,
        unsure=unsure,
        gave_up=gave_up,
        slow=slow,
        quick=quick,
        manner=manner or None,
        manner_effortful=manner_effortful,
        manner_fluent=manner_fluent,
        thinking_ms=thinking_ms,
    )


def _strain_delta(correct: bool, signals: Signals, wrong_streak: int) -> float:
    """How much this single turn adds to (or takes off) the running strain."""
    if correct:
        # Getting one right is the strongest evidence that the student is fine,
        # and more so if it came easily.
        return -0.15 if signals.quick else -0.05

    delta = 0.22
    delta += 0.10 * max(0, wrong_streak - 1)   # a run hurts more than a one-off
    if signals.gave_up:
        delta += 0.30
    if signals.hesitant:
        delta += 0.10
    if signals.unsure:
        delta += 0.06
    if signals.slow:
        delta += 0.12
    if signals.manner_effortful:
        delta += 0.35
    if signals.manner_fluent:
        delta -= 0.15
    return delta


_EASE_LINES = (
    "Let's take that one down a notch.",
    "That one was a big ask. Here's an easier one.",
    "No harm done - let's back up a step.",
)
_STRETCH_LINES = (
    "You're making this look easy. Let's go up a level.",
    "Right, that's too easy for you. Harder one coming.",
    "You've earned a tougher one.",
)
_STEADY_LINES = (
    "Take your time with this one.",
    "No rush.",
)


def update(
    *,
    correct: bool,
    signals: Signals,
    strain: float,
    correct_streak: int,
    wrong_streak: int,
    difficulty: int,
    scaffold: int,
    rng: random.Random | None = None,
) -> Adjustment:
    """Decide the next question's difficulty and how much help to give with it.

    Rules are ordered, first match wins. Relief always outranks challenge: a
    student who is struggling never gets pushed because of an old streak.
    """
    picker = rng or random
    level = max(0.0, min(1.0, strain * _DECAY + _strain_delta(correct, signals, wrong_streak)))

    # 1. Struggling. Ease the material and add help, and say so - an unexplained
    #    drop in difficulty reads as being patronised.
    if level >= STRAINED:
        eased = max(MIN_DIFFICULTY, difficulty - 1)
        helped = min(MAX_SCAFFOLD, scaffold + 1)
        changed = eased != difficulty or helped != scaffold
        return Adjustment(
            direction="ease",
            difficulty=eased,
            scaffold=helped,
            strain=level,
            line=picker.choice(_EASE_LINES) if changed else picker.choice(_STEADY_LINES),
        )

    # 2. Recovering. Take the help away one rung at a time, and BEFORE making
    #    anything harder: a student who has just clawed their way back should
    #    not lose the hints and get a steeper question in the same breath.
    if correct and scaffold > MIN_SCAFFOLD and level <= SETTLED:
        return Adjustment("hold", difficulty, scaffold - 1, level, None)

    # 3. Cruising, and standing on their own. Only push when the student is both
    #    accurate AND comfortable: a streak scraped through slowly is not an
    #    invitation to make it harder.
    if (
        correct
        and correct_streak >= _STRETCH_STREAK
        and level <= SETTLED
        and scaffold == MIN_SCAFFOLD
        and not signals.hesitant
        and (signals.quick or signals.manner_fluent or signals.thinking_ms is None)
        and difficulty < MAX_DIFFICULTY
    ):
        return Adjustment(
            direction="stretch",
            difficulty=difficulty + 1,
            scaffold=MIN_SCAFFOLD,
            strain=level,
            line=picker.choice(_STRETCH_LINES),
        )

    return Adjustment("hold", difficulty, scaffold, level, None)
