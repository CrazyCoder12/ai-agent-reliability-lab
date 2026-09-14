import json
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from agent_reliability_lab.api import app
from agent_reliability_lab.reporting import html_report
from agent_reliability_lab.runner import experiment

client = TestClient(app)


def test_api_catalogue_and_health():
    assert client.get("/health").json() == {"status": "ok", "mode": "offline-reference"}
    catalogue = client.get("/api/catalogue").json()
    assert len(catalogue["scenarios"]) == 20
    assert len(catalogue["faults"]) == 6


def test_api_returns_evidence_for_a_failed_run():
    response = client.post("/api/runs", json={"fault": "false_success"})
    assert response.status_code == 200
    report = response.json()
    assert report["failed"] > 0
    assert report["cases"][0]["after"] == []
    assert any(
        c["name"] == "claim_supported" and not c["passed"] for c in report["cases"][0]["checks"]
    )


@pytest.mark.parametrize(
    "payload", [{"fault": "unknown"}, {"trials": 0}, {"trials": 11}, {"api_key": "never-accepted"}]
)
def test_api_rejects_invalid_run_configuration(payload):
    assert client.post("/api/runs", json=payload).status_code == 422


def test_dashboard_assets_and_complete_experiment():
    assert "Trust the outcome." in client.get("/").text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/style.css").status_code == 200
    assert client.get("/api/experiment").json()["faults_detected"] == 5


def test_exported_html_has_no_remote_assets_and_escapes_embedded_payload():
    payload = experiment()
    payload["runs"][0]["cases"][0]["result"]["message"] = (
        '</script><script>alert("injected")</script>'
    )
    html = html_report(payload)
    assert '<script>alert("injected")</script>' not in html
    assert "\\u003c/script>" in html
    assert "<script src=" not in html
    assert '<link rel="stylesheet"' not in html
    assert 'id="report-data"' in html


@pytest.mark.parametrize("fault,expected", [("none", 0), ("false_success", 1)])
def test_cli_exit_code_and_portable_report(tmp_path, fault, expected):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "agent_reliability_lab",
            "evaluate",
            "--fault",
            fault,
            "--output",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == expected, result.stderr
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["runs"][0]["fault"] == fault
    assert (tmp_path / "report.html").exists()


def test_demo_is_green_only_when_baseline_passes_and_all_faults_are_detected(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "agent_reliability_lab", "demo", "--output", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert "5/5" in result.stdout


def test_cli_unknown_scenario_is_configuration_failure(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "agent_reliability_lab",
            "evaluate",
            "--scenario",
            "missing",
            "--output",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 2
    assert not (tmp_path / "report.json").exists()
