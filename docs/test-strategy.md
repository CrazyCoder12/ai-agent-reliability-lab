# Test strategy

## Quality risks

The most expensive failures in this lab are unauthorized effects, duplicate refunds, incorrect amounts, and unsupported completion claims. The strategy gives those risks independent database assertions and explicit negative scenarios.

| Layer | What it establishes |
| --- | --- |
| Business-rule tests | Date boundaries and policy enforcement at the tool boundary |
| Tool tests | Identity cannot be supplied by the agent; invalid arguments and repeat keys are handled |
| Evaluator tests | Wrong amounts, changed prior state, foreign refunds, and unsupported per-turn claims are rejected |
| Scenario tests | The reference implementation satisfies every hand-specified scenario |
| Defect tests | Each of the five injected faults produces a specific expected failing check |
| API tests | Validated run configuration, catalogue, artifacts, and error responses |
| CLI tests | Exit codes distinguish passing gates, failed gates, and invalid configuration |
| Report tests | Portable output includes evidence and escapes embedded script-like content |
| Browser inspection | Dashboard selection, filters, evidence views, and layout work in the local browser |

## Release gates

1. Every automated test passes.
2. The clean reference passes all 20 scenarios.
3. Each of five seeded fault variants produces at least one failing scenario.
4. The same versioned suite is used for baseline and fault variants.
5. A failing evaluation exits nonzero; an invalid or empty selection never produces a green report.
6. Package build, critical lint, and formatting checks pass.

`agent-lab demo` is a **test of fault detectability**. It succeeds when the baseline passes and every deliberately broken variant is detected. `agent-lab evaluate --fault …` is an ordinary release gate and fails when scenarios fail. Keeping these semantics separate prevents an intentionally red experiment from being confused with a broken CI job.

## Avoiding misleading metrics

- The pass rate is the fraction of scenario trials satisfying every check, not a weighted safety score.
- A 5/5 defect result applies only to these five handcrafted defects.
- Repeating a deterministic offline case does not increase statistical confidence about a real model.
- Latency in the report is local harness execution time. It is not inference latency.
- The dataset is small and synthetic. There is no held-out live-model benchmark in this release.
- A correct structured status does not prove that every sentence in the accompanying message is truthful.

## Manual checks

Run the demo and open the dashboard. Select False completion, inspect the failed claim and empty refund table, then select Duplicate refund and inspect the lost-response trace and two rows. Verify that the reference variant recovers with one row. Try the search and failure-only filter. Open the exported HTML with the server stopped to verify portability.

## Not covered yet

Concurrent requests, multiple processes, rate limiting, real authentication tokens, payment-provider semantics, retrieval quality, natural-language intent recognition, arbitrary prompt injection, live-model variability, semantic graders, and untrusted adapter containment require separate future work.
