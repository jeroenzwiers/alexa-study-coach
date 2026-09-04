# Study Coach Golden Demo Storyboard

| Time      | Screen and action                            | Spoken line                                                                                  | Proof state                                          |
| --------- | -------------------------------------------- | -------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| 0:00-0:15 | Opening headline, click **Run live session** | "A normal study app knows you were wrong. Study Coach knows what you confused it with."      | QUESTION                                             |
| 0:15-0:28 | First returned question and answer card      | Student says "Chloroplasts." Coach explains the chloroplasts were reached for.               | ANSWER_RECEIVED, ATTRIBUTED_TO                       |
| 0:28-0:45 | Mirrored target appears                      | Student says "Mitochondria." Coach says "Let's separate those two."                          | POSSIBLE_CONFUSION, CONFUSION_DETECTED               |
| 0:45-1:00 | Contrast question with two concepts          | "Which organelle releases energy from glucose? Is it the mitochondria, or the chloroplasts?" | CONTRAST_PROBE                                       |
| 1:00-1:15 | First side correct, then second side correct | Coach says "Exactly," then "That one's done."                                                | SIDE_A_MASTERED, SIDE_B_MASTERED, CONFUSION_RESOLVED |
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
32 ms worst round-trip in latest passing local MCP smoke run
```

The timing is local MCP smoke-test timing only, not production or Alexa+ network latency.

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
