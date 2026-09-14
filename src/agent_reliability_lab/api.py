"""Local-only API for exploring deterministic experiments."""

from importlib.resources import files

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .domain import FAULTS, Fault
from .runner import evaluate, experiment, load_suite

app = FastAPI(
    title="AI Agent Reliability Lab",
    version="0.1.0",
    description="Synthetic, offline evaluation sandbox. No payment or model APIs are called.",
)
web = files("agent_reliability_lab").joinpath("web")
app.mount("/static", StaticFiles(directory=str(web)), name="static")


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fault: Fault = Fault.NONE
    trials: int = Field(default=1, ge=1, le=10)


@app.get("/")
def home():
    return FileResponse(str(web.joinpath("index.html")))


@app.get("/health")
def health():
    return {"status": "ok", "mode": "offline-reference"}


@app.get("/api/catalogue")
def catalogue():
    version, digest, scenarios = load_suite()
    return {
        "version": version,
        "sha256": digest,
        "scenarios": scenarios,
        "faults": [{"id": key, "description": value} for key, value in FAULTS.items()],
    }


@app.get("/api/experiment")
def get_experiment():
    return experiment()


@app.post("/api/runs")
def run(request: RunRequest):
    return evaluate(request.fault, request.trials)
