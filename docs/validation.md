# Validation record

Validated locally on macOS with Python 3.12 on September 13, 2026 (America/Detroit).

| Check | Result |
| --- | --- |
| pytest | 77 passed |
| Ruff lint | Passed |
| Ruff formatting | 15 files already formatted |
| Baseline experiment | 20/20 scenarios passed |
| Controlled defect detection | 5/5 variants detected |
| Source distribution and wheel build | Passed |
| Installed wheel smoke test | Baseline passed; bundled dashboard asset present |
| Dashboard browser check | 12 checks shown; false-completion failures and empty refund state verified |

The wheel was installed into a separate directory without reinstalling dependencies; the smoke test confirmed imports came from that directory. This checks packaging and resource inclusion, not a fresh dependency resolution on every operating system.

Two upstream deprecation warnings remain in the test client stack (Starlette/httpx and the AnyIO BlockingPortal alias). They did not cause failures.

GitHub Actions is configured for Python 3.11 and 3.12 but has not been run remotely. Python 3.11 has not been tested locally. Docker configuration is provided but was not executed because Docker was unavailable. No live model was evaluated.

Reproduce the checks using the commands in the README. Generated reports include their actual execution timestamp and dataset digest. These figures describe a deterministic synthetic harness, not a production agent benchmark.
