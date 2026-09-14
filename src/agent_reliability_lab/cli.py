"""Command-line entry points for evaluations, fault experiments, and the dashboard."""

import argparse
from pathlib import Path

from .domain import Fault
from .reporting import save_report
from .runner import evaluate, experiment, load_suite


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Outcome-based quality checks for tool-using agents"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser(
        "demo", help="Evaluate baseline + five seeded defects; export portable reports"
    )
    demo.add_argument("--output", type=Path, default=Path("artifacts/demo"))
    run = sub.add_parser("evaluate", help="Run a suite; exit 1 if any scenario fails")
    run.add_argument("--fault", choices=[str(f) for f in Fault], default="none")
    run.add_argument("--trials", type=int, default=1)
    run.add_argument("--scenario", action="append", help="Run only these scenario IDs (repeatable)")
    run.add_argument("--output", type=Path, default=Path("artifacts/latest"))
    sub.add_parser("scenarios", help="List the versioned scenario catalogue")
    serve = sub.add_parser("serve", help="Open the local dashboard API on 127.0.0.1")
    serve.add_argument("--port", type=int, default=8787)
    args = parser.parse_args(argv)
    if args.command == "serve":
        import uvicorn

        uvicorn.run("agent_reliability_lab.api:app", host="127.0.0.1", port=args.port)
        return 0
    if args.command == "scenarios":
        version, _, scenarios = load_suite()
        print(f"{version} · {len(scenarios)} scenarios")
        for scenario in scenarios:
            print(f"{scenario.id:26} {scenario.category:22} {scenario.name}")
        return 0
    try:
        if args.command == "demo":
            data = experiment()
            baseline = data["runs"][0]
            print(f"Reference: {baseline['passed']}/{baseline['total']} scenarios passed")
            print(f"Seeded defects detected: {data['faults_detected']}/{data['faults_total']}")
            code = (
                0
                if data["baseline_passed"] and data["faults_detected"] == data["faults_total"]
                else 1
            )
        else:
            report = evaluate(Fault(args.fault), args.trials, args.scenario)
            data = {
                "runs": [report.model_dump(mode="json")],
                "mode": report.mode,
                "suite_version": report.suite_version,
                "created_at": report.created_at,
            }
            print(f"{report.fault}: {report.passed}/{report.total} scenarios passed")
            for case in report.cases:
                if not case.passed:
                    print(
                        f"  FAIL {case.scenario_id}: "
                        + ", ".join(c.name for c in case.checks if not c.passed)
                    )
            code = int(report.failed > 0)
        json_path, html_path = save_report(data, args.output)
        print(f"JSON: {json_path.resolve()}\nHTML: {html_path.resolve()}")
        return code
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
