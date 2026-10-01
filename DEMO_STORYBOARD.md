# Study Coach Golden Demo Storyboard

| Time      | Screen and action                            | Spoken line                                                                                  | Proof state                                          |
| --------- | -------------------------------------------- | -------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| 0:00-0:15 | Opening headline, click **Run live session** | "A normal study app knows you were wrong. Study Coach knows what you confused it with."      | QUESTION                                             |
| 0:15-0:28 | First returned question and answer card      | Student says "Chloroplasts." Coach explains the chloroplasts were reached for.               | ANSWER_RECEIVED, ATTRIBUTED_TO                       |
| 0:28-0:45 | Mirrored target appears                      | Student says "Mitochondria." Coach says "Let's separate the chloroplasts and the mitochondria."                          | POSSIBLE_CONFUSION, CONFUSION_DETECTED               |
| 0:45-1:00 | Contrast question with two concepts          | "Which organelle captures light energy in a plant cell? Is it the chloroplasts, or the mitochondria?" | CONTRAST_PROBE                                       |
| 1:00-1:15 | First side correct, then second side correct | Coach says "Exactly - that's the difference," then "That one's done."                        | SIDE_B_MASTERED, then SIDE_A_MASTERED, CONFUSION_RESOLVED |
| 1:15-1:35 | Persisted progress and restart cards         | "The diagnosis is not thrown away when the session ends."                                    | PERSISTED_STATE                                      |
| 1:35-1:55 | Static architecture frame                    | "The shell is only a client. The Study Coach server owns every decision."                    | TECHNICAL PROOF                                      |
| 1:55-2:15 | MCP connection row                           | "No LLM is on the live grading path."                                                        | NO LLM ON LIVE GRADING PATH                          |
| 2:15-2:35 | Keep the resolved state visible              | "The feedback names the distinction to practise."                                            | PRODUCT IMPACT                                       |
| 2:35-2:40 | Return to resolved card                      | "A wrong answer is not just a score. It is evidence about the learner's mental model."       | CLOSE                                                |

## Architecture frame

```text
Alexa+-style demo shell
        |
        v
MCP 2025-11-25
Streamable HTTP
        |
        v
Study Coach server
        +-> deterministic grading
        +-> misconception state
        +-> persistence

NO LLM ON LIVE GRADING PATH
grading: 11 ms median, 50 ms p99 over 10,400 calls
```

Those two figures are the grading call itself, measured by `harness/bench_grading.py`
on an otherwise idle machine. The round-trip worst case is deliberately not on the
frame: it swings with whatever else the laptop is doing - 169 ms with nothing else
running, 912 ms with the demo shell alongside - and a number that moves by a factor
of five does not belong in a claim. Close everything you do not need before
recording, for the same reason.

The timing is local measurement only, not production or Alexa+ network latency.

## Clean capture frames

1. Opening headline before clicking the button.
2. First `ATTRIBUTED_TO` card showing chloroplasts.
3. `CONFUSION_DETECTED · CONTRAST_PROBE` card showing the pair.
4. `CONFUSION_RESOLVED` card after both distinct sides succeed.
5. `PERSISTED_STATE` restart card.
6. MCP connection row for protocol and transport proof.

## Fallbacks

- If the browser shell cannot reach port 8421, show the repository's saved MCP smoke output and stop the recording; do not simulate a successful response.
- If a card scrolls below the viewport, pause after each clean state and capture it separately rather than zooming out until text is unreadable.
- If the randomized legacy smoke harness misses the pair, do not use it for recording; use the deterministic golden run instead.
