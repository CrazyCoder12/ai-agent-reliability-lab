# Three-minute interview demo

## Setup

```bash
agent-lab demo
agent-lab serve
```

Open http://127.0.0.1:8787. Keep the exported report available as a no-server fallback.

## 0:00–0:30 — State the problem

“A support agent can produce a plausible success message while the real operation fails. I built a Python lab that verifies tool events and persisted outcomes against explicit business expectations.”

Explain immediately that the current agent is deterministic. The demonstration evaluates the harness, not a language model.

## 0:30–1:15 — False completion

Select **False completion**, then **Eligible refund**. Show the failed refund count, amount, and supported-claim checks. Open **State diff**: no refund exists despite the completion claim. Open **Tool trace**: no refund call occurred.

Explain why a test that checked only the text “refund complete” would be misleading.

## 1:15–2:00 — Lost response, duplicate effect

Select **Duplicate refund**, then **Lost response after commit**. Show the first tool attempt ending in a timeout, then the second attempt. The state diff contains two refunds.

Switch to **Reference agent**, select the same scenario, and show that the retry reuses the first refund. One committed effect is the invariant.

## 2:00–2:30 — Authorization and evidence

Select **Authorization bypass** and **Customer isolation**. Show the foreign-data and side-effect checks. Explain that the trusted principal is outside the agent's tool arguments, and the tool boundary owns enforcement.

## 2:30–3:00 — Engineering judgment

Explain three decisions:

- Expectations are separate from agent inputs and the application's policy function.
- Every case gets isolated database state; repeated requests share state only when the scenario requires it.
- Completion claims are checked at each turn, so later success cannot hide an earlier unsupported claim.

Finish with a boundary: “This version proves repeatable defect detection in a small synthetic system. My next increment would attach a live model and evaluate repeated trials against a held-out benchmark.”

## Questions to prepare for

**Why not just use an LLM judge?**
Database effects have precise ground truth. A semantic judge can complement it for message quality, but should not decide whether a refund row exists.

**Why not assert one exact tool sequence?**
Multiple sequences may produce a valid result. The lab constrains forbidden effects and execution budgets while inspecting evidence rather than requiring one universal path.

**Is the idempotency design production-ready?**
No. The serial sandbox demonstrates retry behavior. Real concurrent processing needs database constraints, atomic operations, and concurrency tests.

**What does the injection experiment demonstrate?**
It demonstrates that the oracle detects a known instruction-boundary regression. It does not demonstrate resistance to arbitrary attacks on a real language model.

## Resume wording after reviewing and understanding the implementation

“Built a Python evaluation lab for tool-using agents with 20 versioned scenarios, state-based assertions, five controlled defect variants, and CI quality gates; validated refund correctness, customer isolation, and retry idempotency.”

Describe this as a personal project. Do not present synthetic measurements as production impact.
