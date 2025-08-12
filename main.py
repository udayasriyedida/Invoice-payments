# api.py - Updated with billing plan and milestones in response

import os
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Any, Dict, List

from langgraph.types import Command
from newcode import workflow  # your compiled graph

app = FastAPI(
    title="Invoice-to-Cash Workflow API",
    description="FastAPI endpoints for interactive A-R workflow with detailed step messages",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_config(thread_id: str) -> Dict[str, Any]:
    return {"configurable": {"thread_id": thread_id}}

def build_response(result: dict, thread_id: str) -> dict:
    """Build standardized response with billing plan and milestones"""
    response = {
        "thread_id": thread_id,
        "completed": "__interrupt__" not in result,
        "interrupt": None,
        "audit_log": result.get("audit_log", []),
        "messages": [m.content for m in result.get("messages", [])],
        "state": {
            "project_id": result.get("project_id"),
            "current_milestone": result.get("current_milestone", {}).get("name"),
            "current_milestone_index": result.get("current_milestone_index", 0),
            "invoice_id": result.get("invoice_id"),
            "payment_received": result.get("payment_received"),
            "reminders_sent": result.get("reminders_sent"),
            "escalated_to_finance": result.get("escalated_to_finance"),
            "legal_flag_raised": result.get("legal_flag_raised")
        },
        # 🆕 Include billing plan and milestones
        "billing_plan": result.get("billing_plan"),
        "milestones": result.get("milestones", []),
        "ai_reasoning": result.get("ai_reasoning")
    }
    
    if "__interrupt__" in result:
        interrupt = result["__interrupt__"][0].value
        response["interrupt"] = {
            "step": interrupt.get("step"),
            "step_name": interrupt.get("step_name"),
            "question": interrupt.get("question"),
            "instructions": interrupt.get("instructions"),
            "options": interrupt.get("options"),
            "context": interrupt.get("context", {})
        }
    
    return response

@app.post("/workflow/start")
def start_workflow(payload: Dict[str, Any]):
    """Start the workflow with billing plan and milestones in response"""
    # Ensure total_amount is numeric
    try:
        payload["total_amount"] = float(payload["total_amount"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(status_code=400, detail="`total_amount` must be a number")
    
    # Thread ID
    thread_id = payload.get("thread_id", f"thread-{uuid.uuid4().hex}")
    payload["thread_id"] = thread_id
    
    config = get_config(thread_id)
    try:
        result = workflow.invoke(payload, config=config)
        return build_response(result, thread_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/workflow/resume/{thread_id}")
def resume_workflow(thread_id: str, decision: Dict[str, str]):
    """Resume workflow with billing plan and milestones in response"""
    user_decision = decision.get("decision") or decision.get("resume")
    if not user_decision:
        raise HTTPException(status_code=400, detail="Missing 'decision' in body")
    
    config = get_config(thread_id)
    try:
        result = workflow.invoke(Command(resume=user_decision), config=config)
        return build_response(result, thread_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/workflow/status/{thread_id}")
def workflow_status(thread_id: str):
    """Get workflow status with billing plan and milestones"""
    config = get_config(thread_id)
    state_snapshot = workflow.get_state(config)
    if not state_snapshot or not state_snapshot.values:
        raise HTTPException(status_code=404, detail=f"No workflow found for thread {thread_id}")
    
    state = state_snapshot.values
    return build_response(state, thread_id)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)
