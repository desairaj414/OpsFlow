"""A2A endpoint for the Diagnosis agent — the one Supervisor<->specialist handoff that travels
over A2A instead of an in-process call (see agent_card.py docstring). Local only, calls nothing
outbound.

    python a2a/endpoint.py   # boots on :9010
"""
from fastapi import FastAPI
from pydantic import BaseModel

from a2a.agent_card import DIAGNOSIS_AGENT_CARD
from agents.diagnosis import run_diagnosis

app = FastAPI(title="A2A Diagnosis Agent [local only, calls nothing outbound]")


class InvokeRequest(BaseModel):
    incident_id: str
    evidence: list[dict]


@app.get("/.well-known/agent-card.json")
def get_agent_card():
    return DIAGNOSIS_AGENT_CARD


@app.post("/invoke")
async def invoke(req: InvokeRequest):
    result = await run_diagnosis(req.incident_id, req.evidence)
    return result.model_dump()


@app.get("/health")
def health():
    return {"status": "ok", "agent": "diagnosis-a2a"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9010)
