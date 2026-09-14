"""Portable reports with all assets embedded and JSON escaped for HTML context."""

import json
from importlib.resources import files
from pathlib import Path


def html_report(data: dict) -> str:
    web = files("agent_reliability_lab").joinpath("web")
    template = web.joinpath("index.html").read_text()
    css = web.joinpath("style.css").read_text()
    js = web.joinpath("app.js").read_text()
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace("&", "\\u0026")
    return template.replace(
        '<link rel="stylesheet" href="/static/style.css">', f"<style>{css}</style>"
    ).replace(
        '<script src="/static/app.js" defer></script>',
        f'<script id="report-data" type="application/json">{payload}</script><script>{js}</script>',
    )


def save_report(data: dict, output: Path) -> tuple[Path, Path]:
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "report.json"
    html_path = output / "report.html"
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    html_path.write_text(html_report(data))
    return json_path, html_path
