# Generalization Report

## Scope

The same existing `StudySet`, `grading.grade`, MCP session, contrast queue,
resolution, and history interfaces were exercised across three independently
authored bounded domains. No grader, attribution, scheduling, resolution,
persistence, privacy, MCP, or demo behavior was changed.

The two new sets contain five declared confusable pairs each. The original
biology set predates pair metadata; its established mitochondria/chloroplasts
pair was used as the single regression flow.

## Measured results

| Domain             |  Cards |       Confusable pairs |               Correct acceptance cases |              Cross-attribution cases |                     Ambiguous rejection cases | False attributions | Confusion flow | Resolution |
| ------------------ | -----: | ---------------------: | -------------------------------------: | -----------------------------------: | --------------------------------------------: | -----------------: | -------------- | ---------- |
| Biology            |     13 |          1 tested pair |      2 targeted, 42 verifier phrasings |       2 targeted, 504 verifier cases |                                             3 |                  0 | PASS           | PASS       |
| Computer science   |     12 |                      5 |      2 targeted, 36 verifier phrasings |       2 targeted, 396 verifier cases |                                             3 |                  0 | PASS           | PASS       |
| History and civics |     12 |                      5 |      2 targeted, 36 verifier phrasings |       2 targeted, 396 verifier cases |                                             3 |                  0 | PASS           | PASS       |
| **Total**          | **37** | **11 tested/declared** | **6 targeted, 114 verifier phrasings** | **6 targeted, 1,296 verifier cases** | **9 domain cases + 1 close-neighbor fixture** |              **0** | **PASS**       | **PASS**   |

The verifier reported zero own-phrasing failures and zero cross-attribution
failures for both new sets. The domain-independent harness reported zero false
attributions.

## Adversarial coverage

- Unknown answers were rejected as confident correct answers in all three sets.
- Partial answers were not accepted confidently.
- Negated answers were rejected.
- Filler-heavy answers remained accepted when the concept was clear.
- Phonetic distortion remained accepted for the tested concept.
- `auth` against `authentication` and `authorization` was rejected as ambiguous.
- A contained concept fixture (`data` inside `database`) was rejected by the verifier.
- Malformed difficulty metadata was rejected by the verifier.
- The first correct side never resolved a pair; the second distinct side did.

## Harness

Run the full cross-domain proof with:

```bash
.venv/bin/python harness/test_generalization.py
```

It opens a real MCP Streamable HTTP client for each domain, calls the existing
server tools, closes that client, opens a new client, and verifies persisted
context. It does not import or call the local grader for the live confusion
flow, and it does not implement local confusion or resolution semantics.

## Claim boundary

**The same deterministic misconception-attribution and resolution mechanism
works across three independently authored bounded learning domains without
domain-specific code.**

This does not establish general educational intelligence, arbitrary subject
understanding, unrestricted natural-language understanding, or general
misconception diagnosis.

DOMAIN_SPECIFIC_CODE_ADDED=false
