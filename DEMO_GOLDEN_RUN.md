# Deterministic Golden Run

## Start

From the repository root, use two terminals:

```bash
.venv/bin/python server/app.py
.venv/bin/python preview/demo_server.py
```

Open [http://127.0.0.1:8430](http://127.0.0.1:8430) and click **Run live session** once.

The demo creates a fresh student id and selects a fresh server-created session
whose first question is the mitochondria target. It scripts only the learner's
spoken answers, answers intervening cards normally, then produces the two target
mistakes in the required order. It never sends `manner`.

## Expected sequence

The shell receives these proof states from real MCP responses:

1. `QUESTION`: mitochondria-target question.
2. `ANSWER_RECEIVED · ATTRIBUTED_TO`: learner answer `chloroplasts`; returned `heard_as` is `The chloroplasts`.
3. `ANSWER_RECEIVED`: intervening known answers.
4. `CONFUSION_DETECTED · CONTRAST_PROBE`: learner answer `mitochondria` to the chloroplasts-target question; returned contrast contains both concepts and `heard_as` is `The mitochondria`.
5. `SIDE_B_MASTERED`: learner answers the chloroplasts side correctly; no `resolved_confusion` is present.
6. `SIDE_A_MASTERED` and `CONFUSION_RESOLVED`: learner answers the mitochondria side correctly; `resolved_confusion` is present.
7. `PERSISTED_STATE`: `student_progress` reports the pair as settled for good.
8. `PERSISTED_STATE`: a new `start_practice` call says, "Welcome back. You sorted out 1 confusion last time."

The exact question wording may include intervening cards. They are still real
server-selected questions and real MCP calls; the presentation shell simply
keeps those cards out of the story while driving them correctly.

## Automated proof

With the MCP server already running:

```bash
.venv/bin/python harness/test_demo_golden.py
```

The test asserts protocol version, transport, tools/list, both wrong-answer attributions, contrast scheduling, non-resolution after the first correct side, resolution after the second distinct side, persisted progress, restart context, no `manner`, and no duplicated domain symbols.

## Evidence boundary

The browser shell is a presentation client. It calls `initialize`, `tools/list`, `start_practice`, `submit_answer`, `student_progress`, and restart `start_practice` through Streamable HTTP. It does not import or implement grading, confusion tracking, scheduling, resolution, or persistence.

The demo is a simulated Alexa+ experience backed by a real MCP server. It does not claim real Alexa+ execution.

## Recovery

- Server unavailable: show the initial headline only and do not record a false successful run.
- Browser request fails: restart both local processes and click once again.
- State appears out of order: reload the page and run once; the fresh demo id prevents prior demo history from changing the result.
- Do not use `harness/smoke_client.py` as the recording driver because its legacy question order is randomized; use this golden run.
