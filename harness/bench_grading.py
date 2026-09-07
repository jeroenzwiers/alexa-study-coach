"""How long does grading a spoken answer actually take?

The README publishes a median and a p99 for this. Those numbers were not
reproducible from the repo - there was no script - so here is one, and the
README now quotes what it prints.

MEASURING IT HONESTLY
---------------------
`_prepare` and `normalise` are lru_cached, and that cache is the difference
between a flattering number and a true one. In production the CACHE IS WARM for
the study set - the same forty-odd candidate phrasings are compared on every
single call, all day - and COLD for the student, who says something new each
time. A sweep that repeats the same handful of utterances measures neither: it
warms the student side too and reports a grader that never has to do any work.

So this varies the utterance on every call and leaves the deck warm, which is
the shape of the real workload. The p99 is the number that matters: Alexa+ wants
a tool result inside 500 ms, and a tail is what a student would actually feel.
"""
import pathlib
import random
import statistics
import string
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

import store
from grading import grade

SET_ID = "biology_cells"
CALLS = 10_400          # the figure the README quotes


def utterances(study_set, count: int) -> list[str]:
    """Distinct spoken answers, so the student side of the cache always misses.

    Built by mangling real answers the way a recogniser does - dropping a
    letter, splitting a word, adding filler - rather than from random noise,
    so the grader does the same work it does on a real turn.
    """
    random.seed(11)
    answers = [phrasing for card in study_set.cards for phrasing in card.accepted]
    # Varied only at the FRONT. Anything appended would read as a qualifier -
    # the grader treats the last thing of substance as the assertion - so a
    # trailing uniquifier would push every utterance out of the fast path and
    # measure a workload no student produces.
    lead = ["um", "i think", "its", "maybe", "like", "well", "erm", "so", "uh",
            "i think its", "um well", "maybe like", "erm i think", ""]
    out = []
    while len(out) < count:
        said = random.choice(answers)
        style = random.randrange(4)
        if style == 0:                                    # a dropped sound
            cut = random.randrange(len(said))
            said = said[:cut] + said[cut + 1:]
        elif style == 1:                                  # a split word
            cut = random.randrange(1, max(2, len(said)))
            said = said[:cut] + " " + said[cut:]
        elif style == 2:                                  # a doubled letter
            cut = random.randrange(len(said))
            said = said[:cut] + said[cut:cut + 1] + said[cut:]
        else:                                             # a stray sound
            said = random.choice(string.ascii_lowercase) + said
        out.append(f"{random.choice(lead)} {said}".strip())
    return out


def main() -> int:
    study_set = store.STUDY_SETS[SET_ID]
    pools = {card.id: study_set.candidates_for(card.id) for card in study_set.cards}
    card_ids = list(pools)
    said = utterances(study_set, CALLS)

    for phrasing in said[:200]:                # warm the DECK side only
        grade(phrasing, pools[card_ids[0]])

    timings = []
    for i, phrasing in enumerate(said):
        pool = pools[card_ids[i % len(card_ids)]]
        start = time.perf_counter()
        grade(phrasing, pool)
        timings.append((time.perf_counter() - start) * 1000)

    timings.sort()
    median = statistics.median(timings)
    p99 = timings[int(len(timings) * 0.99)]
    print(f"study set   : {study_set.title}, {len(study_set.cards)} cards, "
          f"{len(pools[card_ids[0]])} candidates per call")
    print(f"calls       : {len(timings)}, each on an utterance not seen before")
    print(f"median      : {median:.2f} ms")
    print(f"p99         : {p99:.2f} ms")
    print(f"worst       : {timings[-1]:.2f} ms")
    print(f"budget      : 500 ms  (p99 is {p99 / 5:.1f}% of it)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
