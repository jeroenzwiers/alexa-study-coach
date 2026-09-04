# Study Coach Golden Demo Script

**Target runtime:** 2:40, simulated Alexa+ experience backed by a real MCP server.

## 0:00-0:15: The promise

**Narrator:** "A normal study app knows you were wrong. Study Coach knows what you confused it with."

Show the opening screen and click **Run live session**. Do not show JSON.

## 0:15-0:45: Two mirrored mistakes

**Study Coach:** "Which organelle releases energy from glucose?"

**Student:** "Chloroplasts."

**Study Coach:** "Not quite. That's the chloroplasts. Chloroplasts capture energy from light; mitochondria release it from food."

Point to the visible **ATTRIBUTED_TO** label. The important moment is that the response is attributed to chloroplasts, not shown as an anonymous wrong mark.

**Study Coach:** "Which organelle captures light energy in a plant cell?"

**Student:** "Mitochondria."

**Study Coach:** "Not quite. That's the mitochondria. Let's separate those two."

Point to **CONFUSION_DETECTED** and **CONTRAST_PROBE**.

## 0:45-1:15: Resolve the distinction

**Study Coach:** "Which organelle releases energy from glucose? Is it the mitochondria, or the chloroplasts?"

**Student:** "Mitochondria."

**Study Coach:** "Exactly."

Point to **SIDE_A_MASTERED**. It must not yet say resolved.

**Study Coach:** "Which organelle captures light energy in a plant cell?"

**Student:** "Chloroplasts."

**Study Coach:** "Yes, and that's the pair sorted. You've just had them both right. That one's done."

Point to **SIDE_B_MASTERED** and **CONFUSION_RESOLVED**.

## 1:15-1:35: Remembered context

**Narrator:** "The diagnosis is not thrown away when the session ends."

Show **Persisted progress** and read the sentence containing "Settled for good". Then show **Restart session** and read the "Welcome back" line.

## 1:35-1:55: Architecture

**Narrator:** "This is a simulated Alexa+ experience backed by the real MCP server. The shell is only a client."

Show the architecture frame from [DEMO_STORYBOARD.md](DEMO_STORYBOARD.md):

```text
Alexa+-style demo shell
        |
        v
MCP 2025-11-25 over Streamable HTTP
        |
        v
Study Coach server
        +-> deterministic grading
        +-> misconception state
        +-> persistence
```

## 1:55-2:15: Why deterministic

**Narrator:** "The live grading path uses no LLM. In this bounded learning domain, every candidate answer is known. The server compares the spoken response with the full set, attributes the competing concept, and returns structured evidence in milliseconds."

Show the MCP connection row with `2025-11-25`, `Streamable HTTP`, and `8 tools/list`. Do not imply the local timing is production or Alexa+ network latency.

## 2:15-2:35: Impact

**Narrator:** "For a learner, the feedback names the distinction to practise. Across learners, the same mechanism can reveal recurring anonymous topic confusions without exposing names."

Use the existing class-report capability only as a one-sentence repository-supported claim. Do not open a dashboard.

## 2:35-2:40: Close

**Narrator:** "A wrong answer is not just a score. It is evidence about the learner's mental model."
