# Contributing

Install the development dependencies and run `pytest`, `ruff check .`, `ruff format --check src tests`, and `agent-lab demo` before proposing a change.

New scenarios should include a clear requirement, an independently reviewed expected outcome, and a concrete reason the case matters. Do not derive expected outcomes by running the reference implementation and copying its answers.

Keep all fixture data synthetic. Do not add API keys, production traces, customer records, or real payment integrations to the sample dataset. A new fault should include a regression test proving the specific assertion that detects it.

Document limitations and distinguish offline harness checks from live-model evaluations. Avoid claiming production performance from synthetic scenarios.
