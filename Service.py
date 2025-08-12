"""
FastAPI server for complete Invoice-to-Cash workflow 
"""

import uuid
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from langgraph.types import Command
from main import *

app = FastAPI(
    title="Complete Invoice-to-Cash API",
    description="Full workflow from project initiation to legal collections",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True
)

# ──────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────────────────────────────────────
def get_config(thread_id: str) -> Dict[str, Any]:
    """Get LangGraph config for thread"""
    return {"configurable": {"thread_id": thread_id}}


def run_until_interrupt(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Run workflow until interrupt or completion"""
    config = get_config(payload["thread_id"])
    result = workflow.invoke(payload, config=config)
    
    return {
        "success": True,
        "thread_id": payload["thread_id"],
        "state": result,
        "interrupted": "__interrupt__" in result,
        "interrupt_data": result.get("__interrupt__", [{}])[0].get("value") if "__interrupt__" in result else None,
        "current_step": get_current_step(result),
        "audit_log": result.get("audit_log", [])[-5:]  # Last 5 entries
    }


def get_current_step(state: Dict[str, Any]) -> str:
    """Determine current workflow step based on state"""
    if "__interrupt__" in state:
        return "WAITING_FOR_HUMAN_INPUT"
    elif state.get("legal_flag_raised"):
        return "LEGAL_COLLECTIONS"
    elif state.get("recovery_initiated"):
        return "RECOVERY_WORKFLOW"
    elif state.get("escalated_to_finance"):
        return "FINANCE_ESCALATION"
    elif state.get("milestone_paid"):
        return "PAYMENT_SETTLED"
    elif state.get("payment_reconciled"):
        return "PAYMENT_RECONCILED"
    elif state.get("payment_received"):
        return "PAYMENT_RECEIVED"
    elif state.get("invoice_sent"):
        return "INVOICE_SENT"
    elif state.get("invoice_id"):
        return "INVOICE_GENERATED"
    elif state.get("milestone_complete"):
        return "MILESTONE_COMPLETE"
    elif state.get("milestones"):
        return "BILLING_PLAN_DEFINED"
    elif state.get("project_id"):
        return "PROJECT_STARTED"
    else:
        return "INITIALIZING"


# ──────────────────────────────────────────────────────────────────────────────
# API Routes
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/")
def health_check():
    """API health check"""
    return {
        "status": "healthy",
        "service": "Complete Invoice-to-Cash API",
        "workflow_steps": "A through R",
        "features": ["Human-in-the-Loop", "Payment Tracking", "Collections"]
    }


@app.post("/workflow/start")
def start_workflow(initial: Dict[str, Any]):
    """Start a new complete invoice workflow"""
    if "thread_id" not in initial:
        initial["thread_id"] = f"workflow-{uuid.uuid4()}"
    
    try:
        return run_until_interrupt(initial)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to start workflow: {exc}")


@app.post("/workflow/resume/{thread_id}")
def resume_workflow(thread_id: str, decision: Dict[str, str]):
    """Resume workflow with human decision"""
    try:
        config = get_config(thread_id)
        user_input = decision.get("resume", decision.get("decision", ""))
        
        result = workflow.invoke(Command(resume=user_input), config=config)
        
        return {
            "success": True,
            "thread_id": thread_id,
            "state": result,
            "interrupted": "__interrupt__" in result,
            "interrupt_data": result.get("__interrupt__", [{}])[0].get("value") if "__interrupt__" in result else None,
            "current_step": get_current_step(result),
            "human_decision": user_input,
            "audit_log": result.get("audit_log", [])[-5:]
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to resume workflow: {exc}")


@app.get("/workflow/status/{thread_id}")
def get_workflow_status(thread_id: str):
    """Get current workflow status and state"""
    try:
        config = get_config(thread_id)
        state_snapshot = workflow.get_state(config)
        
        if not state_snapshot or not state_snapshot.values:
            raise HTTPException(status_code=404, detail=f"No workflow found for thread {thread_id}")
        
        state = state_snapshot.values
        
        return {
            "success": True,
            "thread_id": thread_id,
            "current_step": get_current_step(state),
            "interrupted": "__interrupt__" in state,
            "interrupt_data": state.get("__interrupt__", [{}])[0].get("value") if "__interrupt__" in state else None,
            "project_id": state.get("project_id"),
            "client_name": state.get("client_name"),
            "invoice_id": state.get("invoice_id"),
            "payment_received": state.get("payment_received", False),
            "payment_overdue_days": state.get("payment_overdue_days", 0),
            "reminders_sent": state.get("reminders_sent", 0),
            "escalated_to_finance": state.get("escalated_to_finance", False),
            "legal_flag_raised": state.get("legal_flag_raised", False),
            "audit_log": state.get("audit_log", [])[-10:]  # Last 10 entries
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {exc}")


@app.get("/workflow/history/{thread_id}")
def get_workflow_history(thread_id: str, limit: int = Query(20, ge=1, le=100)):
    """Get workflow execution history"""
    try:
        config = get_config(thread_id)
        history = []
        
        for state in workflow.get_state_history(config, limit=limit):
            history.append({
                "timestamp": state.created_at.isoformat() if state.created_at else None,
                "step": get_current_step(state.values) if state.values else "UNKNOWN",
                "values": state.values,
                "metadata": state.metadata
            })
        
        return {
            "success": True,
            "thread_id": thread_id,
            "history": history,
            "total_steps": len(history)
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {exc}")


@app.post("/workflow/force-step/{thread_id}")
def force_workflow_step(thread_id: str, step_data: Dict[str, Any]):
    """Force workflow to specific state (for testing/admin)"""
    try:
        config = get_config(thread_id)
        
        # Update specific state fields
        current_state = workflow.get_state(config)
        if not current_state or not current_state.values:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # This is a simplified force update - in production you'd want more validation
        updated_state = {**current_state.values, **step_data}
        
        result = workflow.invoke(updated_state, config=config)
        
        return {
            "success": True,
            "thread_id": thread_id,
            "forced_update": step_data,
            "new_state": result,
            "current_step": get_current_step(result)
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to force step: {exc}")


@app.delete("/workflow/{thread_id}")
def delete_workflow(thread_id: str):
    """Delete/reset a workflow thread"""
    try:
        # Note: InMemorySaver doesn't have explicit delete
        # In production with persistent storage, you'd delete the thread here
        
        return {
            "success": True,
            "message": f"Workflow {thread_id} marked for deletion",
            "thread_id": thread_id
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to delete workflow: {exc}")


# ──────────────────────────────────────────────────────────────────────────────
# Development & Testing Routes
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/workflow/steps")
def get_workflow_steps():
    """Get all workflow steps and their descriptions"""
    return {
        "workflow_steps": {
            "A": "Project Initiated",
            "B": "Define Billing Plan & Milestones", 
            "C": "Milestone Marked Complete? (HIL)",
            "D": "Trigger Auto-Invoice Generation",
            "E": "Log Invoice in Audit Trail",
            "F": "Dispatch Invoice to Customer", 
            "G": "Continue Monitoring Project Progress",
            "H": "Payment Received? (HIL)",
            "I": "Reconcile Payment in Ledger",
            "J": "Mark Milestone as Paid",
            "K": "Notify Internal Stakeholders",
            "L": "End: Payment Settled",
            "M": "Send Payment Reminder",
            "N": "Payment Overdue > 30 Days? (HIL)",
            "O": "Wait & Retry Reminder Loop",
            "P": "Escalate to Finance Team",
            "Q": "Initiate Recovery Workflow", 
            "R": "Legal/Collection Flag if > 60 Days"
        },
        "human_in_loop_points": ["C", "H", "N"],
        "decision_points": {
            "C": "Milestone completion approval",
            "H": "Payment received confirmation", 
            "N": "Escalation to finance decision"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "2024"))
    print(f"🌟 Starting Complete Invoice-to-Cash API on port {port}")
    
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )