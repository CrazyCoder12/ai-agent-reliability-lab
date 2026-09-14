# Live-model integration roadmap

Live inference is intentionally absent from version 0.1. No API key is needed or read by the application.

## Proposed next increment

1. Implement the `Agent` protocol in a new adapter. The input is `AgentTask`, containing only the request, normalized intent, and order ID. Never pass `Scenario` or its expected outputs to the model.
2. Translate model tool calls to `Tools.call`. Keep the trusted identity fixed outside model-generated arguments.
3. Validate structured responses before returning `AgentResult`. Preserve tool traces without requesting or storing hidden chain-of-thought.
4. Add explicit timeouts, total request limits, tool-call limits, retry rules, and a configurable cost budget.
5. Maintain a deterministic fake provider for adapter tests. Run live evaluations separately, only when explicitly configured.
6. Version the model identifier, prompts, tool schemas, corpus if any, and benchmark dataset. Store raw measured results and sample sizes.
7. Compare paired baseline/candidate tasks with multiple trials. A deterministic temperature setting alone does not guarantee reproducibility.
8. Add a held-out scenario set and semantic graders with reviewed rubrics. Calibrate model-based grading against human judgments before using it as a release gate.

## What changes in the quality claim

An offline run shows whether the test harness detects specific controlled defects. A live run can provide evidence about a particular model, prompt, tool implementation, dataset, and execution environment. It still does not establish general agent safety.

If natural-language intent recognition is added, stop supplying the normalized intent to the model and evaluate that extraction as a separate component. Keep the first-release structured-input results distinguishable from free-form agent results.
