import os, uuid, json
from datetime import datetime, timedelta
from operator import add
from typing import Annotated, Literal, TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command, interrupt
from pydantic import BaseModel, Field
from typing import List

load_dotenv()

# ──────────────────────────────────────────────────────────────────────────────
# 1. LLM INITIALIZATION (OpenRouter)
# ──────────────────────────────────────────────────────────────────────────────
class ChatOpenRouter(ChatOpenAI):
    """OpenRouter wrapper for LangChain's ChatOpenAI interface."""
    def __init__(self, model_name: str = "anthropic/claude-3-haiku", **kwargs):
        super().__init__(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            model=model_name,
            **kwargs,
        )

llm = ChatOpenRouter(temperature=0.3)

# ──────────────────────────────────────────────────────────────────────────────
# 2. PYDANTIC MODELS (Same as before)
# ──────────────────────────────────────────────────────────────────────────────
class Milestone(BaseModel):
    id: str = Field(description="Unique milestone identifier (e.g., MS-001)")
    name: str = Field(description="Descriptive milestone name")
    description: str = Field(description="Detailed description of what this milestone covers")
    amount: float = Field(description="Payment amount for this milestone")
    percentage: float = Field(description="Percentage of total project value (0-100)")
    deliverables: List[str] = Field(description="List of specific deliverables for this milestone")
    estimated_duration: str = Field(description="Estimated time to complete (e.g., '2-3 weeks')")
    dependencies: List[str] = Field(description="Prerequisites or dependencies", default=[])

class BillingPlan(BaseModel):
    currency: str = Field(description="Currency code (e.g., USD, EUR)")
    total_amount: float = Field(description="Total project amount")
    payment_terms: str = Field(description="Payment terms (e.g., 'Net 30 days')")
    milestone_count: int = Field(description="Number of milestones")
    payment_structure: str = Field(description="Description of payment structure")

class AIGeneratedPlan(BaseModel):
    billing_plan: BillingPlan
    milestones: List[Milestone]
    ai_reasoning: str = Field(description="AI's reasoning for this milestone structure")

# ──────────────────────────────────────────────────────────────────────────────
# 3. WORKFLOW STATE
# ──────────────────────────────────────────────────────────────────────────────
class InvoiceState(TypedDict, total=False):
    thread_id: str
    project_id: str
    project_name: str
    client_name: str
    client_email: str
    currency: str
    total_amount: float

    # AI-generated billing / milestone data
    billing_plan: dict
    milestones: list[dict]
    current_milestone: dict
    current_milestone_index: int
    milestone_complete: bool
    ai_reasoning: str

    # Invoice data
    invoice_id: str
    invoice_amount: float
    invoice_sent: bool
    invoice_date: str
    billing_invoice: dict

    # Payment tracking
    payment_received: bool
    payment_date: str
    payment_reconciled: bool
    milestone_paid: bool
    
    # Reminder system
    reminders_sent: int
    last_reminder_date: str
    payment_overdue_days: int
    overdue_30_days: bool
    
    # Escalation tracking
    escalated_to_finance: bool
    recovery_initiated: bool
    legal_flag_raised: bool
    overdue_60_days: bool
    
    # Logs & messaging
    audit_log: Annotated[list[str], add]
    messages: Annotated[list, add_messages]

    # HIL artifacts
    human_decision: str
    hil_step: str

# ──────────────────────────────────────────────────────────────────────────────
# 4. NODE FUNCTIONS (Same implementations, no changes needed)
# ──────────────────────────────────────────────────────────────────────────────

def start_project(state: InvoiceState) -> InvoiceState:                           # A
    pid = f"PROJ-{uuid.uuid4().hex[:8].upper()}"
    
    project_name = state.get("project_name", "Unnamed Project")
    client_name = state.get("client_name", "Unknown Client")
    client_email = state.get("client_email", "no-email@example.com")
    currency = state.get("currency", "USD").upper()
    total_amount = state.get("total_amount", 0)
    
    return {
        "project_id": pid,
        "project_name": project_name,
        "client_name": client_name,
        "client_email": client_email,
        "currency": currency,
        "total_amount": total_amount,
        "current_milestone_index": 0,
        "payment_received": False,
        "payment_reconciled": False,
        "milestone_paid": False,
        "reminders_sent": 0,
        "payment_overdue_days": 0,
        "overdue_30_days": False,
        "overdue_60_days": False,
        "escalated_to_finance": False,
        "recovery_initiated": False,
        "legal_flag_raised": False,
        "audit_log": [f"A: Project {pid} initiated - {project_name} for {client_name} ({client_email}) - {currency} {total_amount:,.2f}"],
        "messages": [AIMessage(content=f"🔰 Project {pid} started for {client_name}")]
    }


def define_billing_plan(state: InvoiceState) -> InvoiceState:                     # B
    project_name = state["project_name"]
    client_name = state["client_name"]
    client_email = state["client_email"]
    currency = state["currency"]
    total_amount = state["total_amount"]
    
    # AI Milestone Planning
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert project manager and billing specialist. 
        Create a detailed billing plan with milestones for the given project.
        
        Guidelines:
        - Create 3-5 logical milestones based on the project type
        - Distribute amounts reasonably (typical: 20-30% kickoff, 40-50% development, 20-30% completion)
        - Include specific deliverables for each milestone
        - Consider project complexity and client needs
        - Make milestone names descriptive and professional
        
        Return ONLY valid JSON matching the required schema."""),
        
        ("human", """Create a billing plan for:
        
        Project: {project_name}
        Client: {client_name}  
        Total Amount: {currency} {total_amount:,.2f}
        
        Analyze the project name to determine appropriate milestone structure.""")
    ])
    
    parser = JsonOutputParser(pydantic_object=AIGeneratedPlan)
    chain = prompt | llm | parser
    
    try:
        ai_plan = chain.invoke({
            "project_name": project_name,
            "client_name": client_name,
            "currency": currency,
            "total_amount": total_amount
        })
        
        billing_plan = ai_plan["billing_plan"]
        milestones = ai_plan["milestones"]
        ai_reasoning = ai_plan.get("ai_reasoning", "AI-generated milestone plan")
        
        # Ensure amounts add up correctly
        total_milestone_amount = sum(m["amount"] for m in milestones)
        if abs(total_milestone_amount - total_amount) > 0.01:
            difference = total_amount - total_milestone_amount
            milestones[-1]["amount"] += difference
        
        current_milestone = milestones[0] if milestones else {}
        
    except Exception as e:
        # Fallback plan
        fallback_milestones = [
            {
                "id": "MS-001",
                "name": "Project Kickoff & Planning",
                "description": "Initial project setup, requirements gathering, and planning phase",
                "amount": total_amount * 0.3,
                "percentage": 30.0,
                "deliverables": ["Project plan", "Requirements document", "Timeline"],
                "estimated_duration": "1-2 weeks",
                "dependencies": []
            },
            {
                "id": "MS-002", 
                "name": "Development & Implementation",
                "description": "Core development and implementation work",
                "amount": total_amount * 0.5,
                "percentage": 50.0,
                "deliverables": ["Core functionality", "Testing", "Documentation"],
                "estimated_duration": "4-6 weeks",
                "dependencies": ["MS-001"]
            },
            {
                "id": "MS-003",
                "name": "Completion & Delivery", 
                "description": "Final delivery, training, and project closure",
                "amount": total_amount * 0.2,
                "percentage": 20.0,
                "deliverables": ["Final delivery", "Training", "Support documentation"],
                "estimated_duration": "1-2 weeks",
                "dependencies": ["MS-002"]
            }
        ]
        
        billing_plan = {
            "currency": currency,
            "total_amount": total_amount,
            "payment_terms": "Net 30 days",
            "milestone_count": len(fallback_milestones),
            "payment_structure": "Milestone-based payments"
        }
        
        milestones = fallback_milestones
        ai_reasoning = f"Fallback plan used due to AI error: {str(e)}"
        current_milestone = fallback_milestones[0]

    # 🆕 GENERATE INVOICE AT POINT B (Always happens)
    milestone_name = current_milestone["name"]
    milestone_amount = current_milestone["amount"]
    due_terms = billing_plan.get("payment_terms", "Net 30 days")

    # AI Invoice Generation
    invoice_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert invoicing assistant. Generate a professional invoice in JSON containing: "
                   "invoice_number, date, due_date, bill_to (name,email), project_name, "
                   "milestone_name, line_items (list of {description, amount}), subtotal, total, currency."),
        ("human", """Generate invoice for:
Project: {project_name}
Client: {client_name} <{client_email}>
Milestone: {milestone_name}
Amount: {currency} {milestone_amount:,.2f}
Total Project Amount: {currency} {total_amount:,.2f}
Payment Terms: {due_terms}""")
    ])
    
    invoice_parser = JsonOutputParser(pydantic_object=dict)
    invoice_chain = invoice_prompt | llm | invoice_parser

    try:
        invoice_data = invoice_chain.invoke({
            "project_name": project_name,
            "client_name": client_name,
            "client_email": client_email,
            "milestone_name": milestone_name,
            "milestone_amount": milestone_amount,
            "currency": currency,
            "total_amount": total_amount,
            "due_terms": due_terms
        })
    except Exception:
        invoice_data = {
            "invoice_number": f"INV-{uuid.uuid4().hex[:8].upper()}",
            "date": datetime.now().isoformat()[:10],
            "due_date": (datetime.now() + timedelta(days=30)).isoformat()[:10],
            "bill_to": {"name": client_name, "email": client_email},
            "project_name": project_name,
            "milestone_name": milestone_name,
            "line_items": [{"description": milestone_name, "amount": milestone_amount}],
            "subtotal": milestone_amount,
            "total": milestone_amount,
            "currency": currency
        }

    return {
        # Billing plan data
        "billing_plan": billing_plan,
        "milestones": milestones,
        "current_milestone": current_milestone,
        "current_milestone_index": 0,
        "ai_reasoning": ai_reasoning,
        "milestone_complete": False,
        
        # 🆕 Invoice data (generated at Point B)
        "invoice_id": invoice_data["invoice_number"],
        "invoice_amount": invoice_data["total"],
        "invoice_date": invoice_data["date"],
        "billing_invoice": invoice_data,
        "invoice_sent": False,  # Will be set to True at Point F
        
        # Audit logs
        "audit_log": [
            f"B: AI generated billing plan with {len(milestones)} milestones - Total: {currency} {total_amount:,.2f}",
            f"B: AI-generated invoice {invoice_data['invoice_number']} for {milestone_name} - {currency} {milestone_amount:,.2f}"
        ],
        "messages": [
            AIMessage(content=f"🤖 AI created {len(milestones)} milestones"),
            AIMessage(content=f"🧾 Invoice {invoice_data['invoice_number']} generated at billing stage")
        ]
    }



def check_milestone_completion(state: InvoiceState) -> InvoiceState:              # C (HIL)
    ms = state["current_milestone"]
    current_index = state.get("current_milestone_index", 0)
    total_milestones = len(state.get("milestones", []))
    
    hil_payload = {
        "step": "C",
        "step_name": "Milestone Completion Check", 
        "milestone_id": ms["id"],
        "milestone_name": ms["name"],
        "milestone_description": ms.get("description", "No description"),
        "amount": ms["amount"],
        "percentage": ms.get("percentage", 0),
        "deliverables": ms["deliverables"],
        "estimated_duration": ms.get("estimated_duration", "Unknown"),
        "dependencies": ms.get("dependencies", []),
        "milestone_progress": f"{current_index + 1} of {total_milestones}",
        "instructions": "Please review the milestone details and confirm if all deliverables are complete.",
        "question": f"Is milestone '{ms['name']}' complete and ready for invoicing?",
        "options": ["yes", "no"],
        "context": {
            "project_id": state.get("project_id"),
            "project_name": state.get("project_name"),
            "client_name": state.get("client_name"),
            "client_email": state.get("client_email"),
            "currency": state.get("currency"),
            "ai_reasoning": state.get("ai_reasoning", "AI milestone planning applied")
        }
    }
    
    human_response = interrupt(hil_payload)
    is_complete = str(human_response).lower() in {"yes", "y", "true", "complete", "approved"}
    
    return {
        "milestone_complete": is_complete,
        "human_decision": str(human_response),
        "hil_step": "C_completed",
        "audit_log": [f"C: Milestone {ms['id']} ({ms['name']}) completion check - Human decided: {human_response}"]
    }


def trigger_invoice(state: InvoiceState) -> InvoiceState:                         # D
    project_name = state["project_name"]
    client_name = state["client_name"]
    client_email = state["client_email"]
    currency = state["currency"]
    milestone = state["current_milestone"]
    milestone_name = milestone["name"]
    milestone_amount = milestone["amount"]
    total_amount = state["total_amount"]
    due_terms = state.get("billing_plan", {}).get("payment_terms", "Net 30 days")

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert invoicing assistant. Generate a professional invoice in JSON containing: "
                   "invoice_number, date, due_date, bill_to (name,email), project_name, "
                   "milestone_name, line_items (list of {description, amount}), subtotal, total, currency."),
        ("human", """Generate invoice for:
Project: {project_name}
Client: {client_name} <{client_email}>
Milestone: {milestone_name}
Amount: {currency} {milestone_amount:,.2f}
Total Project Amount: {currency} {total_amount:,.2f}
Payment Terms: {due_terms}""")
    ])
    
    parser = JsonOutputParser(pydantic_object=dict)
    chain = prompt | llm | parser

    try:
        invoice_data = chain.invoke({
            "project_name": project_name,
            "client_name": client_name,
            "client_email": client_email,
            "milestone_name": milestone_name,
            "milestone_amount": milestone_amount,
            "currency": currency,
            "total_amount": total_amount,
            "due_terms": due_terms
        })
    except Exception:
        invoice_data = {
            "invoice_number": f"INV-{uuid.uuid4().hex[:8].upper()}",
            "date": datetime.now().isoformat()[:10],
            "due_date": (datetime.now() + timedelta(days=30)).isoformat()[:10],
            "bill_to": {"name": client_name, "email": client_email},
            "project_name": project_name,
            "milestone_name": milestone_name,
            "line_items": [{"description": milestone_name, "amount": milestone_amount}],
            "subtotal": milestone_amount,
            "total": milestone_amount,
            "currency": currency
        }

    return {
        "invoice_id": invoice_data["invoice_number"],
        "invoice_amount": invoice_data["total"],
        "invoice_date": invoice_data["date"],
        "billing_invoice": invoice_data,
        "audit_log": [f"D: AI-generated invoice {invoice_data['invoice_number']} for {milestone_name}"],
        "messages": [AIMessage(content=f"🤖 Generated invoice {invoice_data['invoice_number']}")]
    }


def log_audit(state: InvoiceState) -> InvoiceState:                               # E
    invoice_id = state.get("invoice_id", "N/A")
    invoice_amount = state.get("invoice_amount", 0)
    currency = state.get("currency", "USD")
    milestone_name = state["current_milestone"]["name"]
    client_email = state.get("client_email", "no-email")
    
    timestamp = datetime.now().isoformat()
    
    return {
        "audit_log": [f"E: AUDIT LOG - Invoice {invoice_id} for '{milestone_name}' logged at {timestamp} - Amount: {currency} {invoice_amount:,.2f} - Client: {client_email}"],
        "messages": [AIMessage(content=f"📋 Invoice {invoice_id} logged in audit trail")]
    }


def dispatch_invoice(state: InvoiceState) -> InvoiceState:                        # F
    client = state["client_name"]
    client_email = state["client_email"]
    invoice_id = state["invoice_id"]
    milestone_name = state["current_milestone"]["name"]
    
    return {
        "invoice_sent": True,
        "audit_log": [f"F: Invoice {invoice_id} for '{milestone_name}' dispatched to {client} ({client_email})"],
        "messages": [AIMessage(content=f"📧 Invoice {invoice_id} sent to {client} at {client_email}")]
    }


def monitor_progress(state: InvoiceState) -> InvoiceState:                        # G
    pid = state["project_id"]
    
    # Preserve critical data
    invoice_id = state.get("invoice_id", "N/A")
    invoice_amount = state.get("invoice_amount", 0)
    invoice_date = state.get("invoice_date")
    invoice_sent = state.get("invoice_sent", False)
    current_milestone = state.get("current_milestone", {})
    currency = state.get("currency", "USD")
    billing_invoice = state.get("billing_invoice", {})
    
    # Calculate overdue status
    overdue_days = 0
    overdue_30 = False
    overdue_60 = False
    
    if invoice_sent and invoice_date:
        try:
            invoice_date_obj = datetime.fromisoformat(invoice_date)
            days_passed = (datetime.now() - invoice_date_obj).days
            payment_terms = 30
            overdue_days = max(0, days_passed - payment_terms)
            overdue_30 = overdue_days > 30
            overdue_60 = overdue_days > 60
        except Exception as e:
            print(f"Date calculation error: {e}")
    
    return {
        # Monitoring data
        "payment_overdue_days": overdue_days,
        "overdue_30_days": overdue_30,
        "overdue_60_days": overdue_60,
        
        # PRESERVED: Critical data
        "invoice_id": invoice_id,
        "invoice_amount": invoice_amount,
        "invoice_date": invoice_date,
        "invoice_sent": invoice_sent,
        "current_milestone": current_milestone,
        "current_milestone_index": state.get("current_milestone_index", 0),
        "currency": currency,
        "client_email": state.get("client_email"),
        "billing_invoice": billing_invoice,
        
        "audit_log": [f"G: Monitoring {pid} - Invoice {invoice_id} ({currency} {invoice_amount:,.2f}) - Overdue: {overdue_days} days"],
        "messages": [AIMessage(content=f"🔍 Monitoring {pid} - Invoice {invoice_id} overdue: {overdue_days} days")]
    }


def check_payment_received(state: InvoiceState) -> InvoiceState:                  # H (HIL)
    invoice_id = state.get("invoice_id", "N/A")
    amount = state.get("invoice_amount", 0)
    currency = state.get("currency", "USD")
    overdue_days = state.get("payment_overdue_days", 0)
    milestone_name = state["current_milestone"]["name"]
    current_index = state.get("current_milestone_index", 0)
    total_milestones = len(state.get("milestones", []))
    client_email = state.get("client_email", "no-email")
    
    hil_payload = {
        "step": "H",
        "step_name": "Payment Status Verification",
        "invoice_id": invoice_id,
        "invoice_amount": amount,
        "currency": currency,
        "milestone_name": milestone_name,
        "milestone_progress": f"{current_index + 1} of {total_milestones}",
        "overdue_days": overdue_days,
        "reminders_sent": state.get("reminders_sent", 0),
        "instructions": "Please check your payment systems, bank accounts, and client communications to verify payment status.",
        "question": f"Has payment been received for invoice {invoice_id} ({currency} {amount:,.2f})?",
        "options": ["yes", "no"],
        "context": {
            "project_id": state.get("project_id"),
            "project_name": state.get("project_name"),
            "client_name": state.get("client_name"),
            "client_email": client_email,
            "invoice_date": state.get("invoice_date"),
            "payment_terms": "Net 30 days"
        }
    }
    
    human_response = interrupt(hil_payload)
    payment_received = str(human_response).lower() in {"yes", "y", "true", "received", "paid"}
    
    return {
        "payment_received": payment_received,
        "human_decision": str(human_response),
        "hil_step": "H_completed",
        "payment_date": datetime.now().isoformat()[:10] if payment_received else None,
        "audit_log": [f"H: Payment verification for {invoice_id} - Human confirmed: {human_response}"]
    }


def reconcile_payment(state: InvoiceState) -> InvoiceState:                       # I
    invoice_id = state["invoice_id"]
    amount = state["invoice_amount"]
    currency = state["currency"]
    milestone_name = state["current_milestone"]["name"]
    client_name = state["client_name"]
    payment_date = state.get("payment_date", datetime.now().isoformat()[:10])
    
    return {
        "payment_reconciled": True,
        "audit_log": [f"I: PAYMENT RECONCILED in ledger - {currency} {amount:,.2f} from {client_name} for milestone '{milestone_name}' (Invoice: {invoice_id}) on {payment_date}"],
        "messages": [AIMessage(content=f"💰 Payment {currency} {amount:,.2f} reconciled in ledger")]
    }


def mark_milestone_paid(state: InvoiceState) -> InvoiceState:  # J
    current_index = state.get("current_milestone_index", 0)
    total = len(state.get("milestones", []))
    
    result = {
        "milestone_paid": True,
        "old_milestone_index": current_index,  # 🔥 Store old index for routing
        "audit_log": [f"J: Milestone '{state['current_milestone']['name']}' marked PAID ({current_index + 1}/{total})"],
        "messages": [AIMessage(content=f"✅ Milestone '{state['current_milestone']['name']}' paid")]
    }
    
    # Only advance if there are more milestones
    if current_index + 1 < total:
        next_index = current_index + 1
        next_milestone = state["milestones"][next_index]
        result.update({
            "current_milestone_index": next_index,
            "current_milestone": next_milestone,
            "milestone_complete": False,
            "payment_received": False,
            "payment_reconciled": False,
            "invoice_sent": False,   
            "invoice_amount": 0,
            "invoice_date": None,
            "billing_invoice": {},
            "reminders_sent": 0,
        })
    
    return result


def notify_stakeholders(state: InvoiceState) -> InvoiceState:                     # K
    milestone_name = state["current_milestone"]["name"]
    current_index = state.get("current_milestone_index", 0)
    total_milestones = len(state.get("milestones", []))
    
    return {
        "audit_log": [f"K: Stakeholders notified - Milestone '{milestone_name}' completed ({current_index + 1}/{total_milestones})"],
        "messages": [AIMessage(content=f"📢 Stakeholders notified of milestone completion")]
    }


def payment_settled(state: InvoiceState) -> InvoiceState:                         # L
    invoice_id = state.get("invoice_id", "N/A")
    current_index = state.get("current_milestone_index", 0)
    total_milestones = len(state.get("milestones", []))
    
    is_final_milestone = current_index + 1 >= total_milestones
    
    if is_final_milestone:
        return {
            "audit_log": [f"L: FINAL milestone payment settled - Project completed! (Invoice: {invoice_id})"],
            "messages": [AIMessage(content=f"🎉 Project completed! Final payment settled for {invoice_id}")]
        }
    else:
        return {
            "audit_log": [f"L: Milestone payment settled - Proceeding to next milestone (Invoice: {invoice_id})"],
            "messages": [AIMessage(content=f"💼 Milestone payment settled - {total_milestones - current_index - 1} milestones remaining")]
        }


def send_payment_reminder(state: InvoiceState) -> InvoiceState:                   # M
    invoice_id = state.get("invoice_id", "N/A")
    reminder_count = state.get("reminders_sent", 0) + 1
    client = state.get("client_name", "Client")
    client_email = state.get("client_email", "no-email")
    milestone_name = state["current_milestone"]["name"]
    
    return {
        "reminders_sent": reminder_count,
        "last_reminder_date": datetime.now().isoformat()[:10],
        "audit_log": [f"M: Payment reminder #{reminder_count} sent to {client} ({client_email}) for '{milestone_name}' (Invoice: {invoice_id})"],
        "messages": [AIMessage(content=f"📬 Reminder #{reminder_count} sent to {client_email}")]
    }


def check_overdue_30days(state: InvoiceState) -> InvoiceState:                    # N (HIL)
    overdue_days = state.get("payment_overdue_days", 0)
    invoice_id = state.get("invoice_id", "N/A")
    client = state.get("client_name", "Client")
    client_email = state.get("client_email", "no-email")
    milestone_name = state["current_milestone"]["name"]
    amount = state.get("invoice_amount", 0)
    currency = state.get("currency", "USD")
    
    hil_payload = {
        "step": "N",
        "step_name": "Overdue Payment Escalation Decision",
        "invoice_id": invoice_id,
        "client_name": client,
        "client_email": client_email,
        "milestone_name": milestone_name,
        "invoice_amount": amount,
        "currency": currency,
        "overdue_days": overdue_days,
        "reminders_sent": state.get("reminders_sent", 0),
        "instructions": "Consider the client relationship, project status, and payment history before deciding to escalate.",
        "question": f"Invoice {invoice_id} for '{milestone_name}' is {overdue_days} days overdue. Escalate to finance team?",
        "options": ["yes", "no"],
        "context": {
            "project_id": state.get("project_id"),
            "project_name": state.get("project_name"),
            "total_project_value": state.get("total_amount", 0),
            "last_reminder": state.get("last_reminder_date")
        }
    }
    
    human_response = interrupt(hil_payload)
    
    return {
        "human_decision": str(human_response),
        "hil_step": "N_completed",
        "audit_log": [f"N: Escalation decision for overdue '{milestone_name}' - Human decided: {human_response}"]
    }


def wait_retry_reminder(state: InvoiceState) -> InvoiceState:                     # O
    return {
        "audit_log": ["O: Waiting for retry period before next reminder"],
        "messages": [AIMessage(content="⏳ Waiting for retry period")]
    }


def escalate_to_finance(state: InvoiceState) -> InvoiceState:                     # P
    invoice_id = state["invoice_id"]
    milestone_name = state["current_milestone"]["name"]
    
    return {
        "escalated_to_finance": True,
        "audit_log": [f"P: Invoice {invoice_id} for '{milestone_name}' escalated to finance team"],
        "messages": [AIMessage(content=f"⚠️ Escalated to finance - {invoice_id}")]
    }


def initiate_recovery(state: InvoiceState) -> InvoiceState:                       # Q
    invoice_id = state["invoice_id"]
    milestone_name = state["current_milestone"]["name"]
    
    return {
        "recovery_initiated": True,
        "audit_log": [f"Q: Recovery workflow initiated for '{milestone_name}' (Invoice: {invoice_id})"],
        "messages": [AIMessage(content=f"🔄 Recovery initiated for {invoice_id}")]
    }


def legal_collection_flag(state: InvoiceState) -> InvoiceState:                   # R
    invoice_id = state["invoice_id"]
    overdue_days = state.get("payment_overdue_days", 0)
    milestone_name = state["current_milestone"]["name"]
    
    return {
        "legal_flag_raised": True,
        "audit_log": [f"R: Legal flag raised for '{milestone_name}' - {overdue_days} days overdue (Invoice: {invoice_id})"],
        "messages": [AIMessage(content=f"⚖️ Legal action initiated for {invoice_id}")]
    }


def end_workflow(state: InvoiceState) -> InvoiceState:
    return {
        "audit_log": ["Workflow ended - No legal action required"],
        "messages": [AIMessage(content="🏁 Workflow completed")]
    }


# ──────────────────────────────────────────────────────────────────────────────
# 5. CORRECTED ROUTING FUNCTIONS
# ──────────────────────────────────────────────────────────────────────────────

def route_after_milestone_check(state: InvoiceState) -> Literal["trigger", "monitor"]:
    """CORRECTED: C → D (if yes) or C → G (if no)"""
    return "trigger" if state.get("milestone_complete") else "monitor"


def route_after_monitor(state: InvoiceState) -> Literal["check_payment"]:
    """G → H (always)"""
    return "check_payment"


def route_after_payment_check(state: InvoiceState) -> Literal["reconcile", "send_reminder"]:
    """CORRECTED: H → I (if yes) or H → M (if no)"""
    return "reconcile" if state.get("payment_received") else "send_reminder"


def route_after_reminder(state: InvoiceState) -> Literal["check_overdue"]:
    """M → N (always)"""
    return "check_overdue"


def route_after_overdue_check(state: InvoiceState) -> Literal["escalate_finance", "wait_retry"]:
    """CORRECTED: N → P (if yes) or N → O (if no)"""
    human_decision = state.get("human_decision", "").lower()
    escalate = human_decision in {"yes", "y", "true", "escalate"}
    return "escalate_finance" if escalate else "wait_retry"


def route_after_wait_retry(state: InvoiceState) -> Literal["send_reminder"]:
    """CORRECTED: O → M (always) - creates the M→N→O→M loop"""
    return "send_reminder"


def route_after_escalate(state: InvoiceState) -> Literal["recovery"]:
    """P → Q (always)"""
    return "recovery"


def route_after_recovery(state: InvoiceState) -> Literal["legal_flag", "end_workflow"]:
    """Q → R (if >60 days) or Q → END"""
    overdue_60 = state.get("overdue_60_days", False)
    return "legal_flag" if overdue_60 else "end_workflow"


def route_after_legal_flag(state: InvoiceState) -> Literal["check_payment"]:
    """CORRECTED: R → H (back to payment check after legal flag)"""
    return "check_payment"


def route_after_payment_settled(state: InvoiceState) -> Literal["check_milestone", "__end__"]:
    """CORRECTED: L → C (if more milestones) or L → END (if final milestone)"""
    current_index = state.get("current_milestone_index", 0)
    total_milestones = len(state.get("milestones", []))
    
    has_more_milestones = current_index + 1 < total_milestones
    return "check_milestone" if has_more_milestones else "__end__"


# ──────────────────────────────────────────────────────────────────────────────
# 6. CORRECTED WORKFLOW GRAPH
# ──────────────────────────────────────────────────────────────────────────────
def build_complete_workflow():
    """Build workflow where INVOICE IS GENERATED AT POINT B"""
    sg = StateGraph(InvoiceState)

    # Add all nodes
    sg.add_node("start",           start_project)                 # A
    sg.add_node("define_plan",     define_billing_plan)          # B 
    sg.add_node("check_milestone", check_milestone_completion)    # C (HIL)
    sg.add_node("trigger",         trigger_invoice)              # D 
    sg.add_node("log",             log_audit)                    # E
    sg.add_node("dispatch",        dispatch_invoice)             # F
    sg.add_node("monitor",         monitor_progress)             # G
    sg.add_node("check_payment",   check_payment_received)       # H (HIL)
    sg.add_node("reconcile",       reconcile_payment)            # I
    sg.add_node("mark_paid",       mark_milestone_paid)          # J
    sg.add_node("notify",          notify_stakeholders)          # K
    sg.add_node("settled",         payment_settled)              # L
    sg.add_node("send_reminder",   send_payment_reminder)        # M
    sg.add_node("check_overdue",   check_overdue_30days)         # N (HIL)
    sg.add_node("wait_retry",      wait_retry_reminder)          # O
    sg.add_node("escalate_finance", escalate_to_finance)         # P
    sg.add_node("recovery",        initiate_recovery)            # Q
    sg.add_node("legal_flag",      legal_collection_flag)        # R
    sg.add_node("end_workflow",    end_workflow)

    # EDGES - Invoice generated at B, routing based on C decision
    sg.add_edge(START, "start")                            # → A
    sg.add_edge("start", "define_plan")                    # A → B (Invoice generated here)
    sg.add_edge("define_plan", "check_milestone")          # B → C (Go to milestone check)
    
    # C decision routing
    sg.add_conditional_edges("check_milestone", route_after_milestone_check,
                             {"trigger": "trigger", "monitor": "monitor"})
    
    # E → F → G sequence
    sg.add_edge("trigger", "log")                          # D → E
    sg.add_edge("log", "dispatch")                         # E → F  
    sg.add_edge("dispatch", "monitor")                     # F → G
    
    # G → H (monitoring to payment check)
    sg.add_conditional_edges("monitor", route_after_monitor,
                             {"check_payment": "check_payment"})
    
    # Rest of the routing remains the same...
    sg.add_conditional_edges("check_payment", route_after_payment_check,
                             {"reconcile": "reconcile", "send_reminder": "send_reminder"})
    
    sg.add_edge("reconcile", "mark_paid")                  # I → J
    sg.add_conditional_edges(
    "mark_paid",
    lambda state: "notify" if state.get("old_milestone_index", 0) >= len(state.get("milestones", [])) - 1 else "check_milestone",
    {"check_milestone": "check_milestone", "notify": "notify"}
)
    sg.add_edge("notify", "settled")                       # K → L
    
    sg.add_conditional_edges("settled", route_after_payment_settled,
                             {"check_milestone": "check_milestone", "__end__": END})
    
    sg.add_conditional_edges("send_reminder", route_after_reminder,
                             {"check_overdue": "check_overdue"})
    
    sg.add_conditional_edges("check_overdue", route_after_overdue_check,
                             {"escalate_finance": "escalate_finance", "wait_retry": "wait_retry"})
    
    sg.add_conditional_edges("wait_retry", route_after_wait_retry,
                             {"send_reminder": "send_reminder"})
    
    sg.add_conditional_edges("escalate_finance", route_after_escalate,
                             {"recovery": "recovery"})
    
    sg.add_conditional_edges("recovery", route_after_recovery,
                             {"legal_flag": "legal_flag", "end_workflow": "end_workflow"})
    
    sg.add_conditional_edges("legal_flag", route_after_legal_flag,
                             {"check_payment": "check_payment"})
    
    sg.add_edge("end_workflow", END)

    return sg.compile(checkpointer=InMemorySaver())

workflow = build_complete_workflow()

if __name__ == "__main__":
    test_inputs = {
        "thread_id": "corrected-workflow-test",
        "project_name": "E-commerce Platform Development",
        "client_name": "TechCorp Solutions",
        "client_email": "finance@techcorp.com",
        "currency": "USD",
        "total_amount": 50000.00
    }
    
    config = {"configurable": {"thread_id": "corrected-workflow-test"}}
    
    print("🚀 Testing CORRECTED workflow routing...")
    print("✅ A → B → C")
    print("✅ C → D→E→F→G→H (if yes) or C → G→H (if no)")
    print("✅ H → I→J→K→L (if yes) or H → M→N (if no)")
    print("✅ N → P→Q→R (if yes) or N → O→M→N (if no)")
    print("✅ R → H (legal flag check)")
    print("✅ L → C (next milestone) or L → END (final)")
    
    try:
        result = workflow.invoke(test_inputs, config=config)
        
        if "__interrupt__" in result:
            pass
            # print(f"\n🤚 Human input required: {result['__interrupt__'][0].value.get('question')}")
        else:
            print("\n✅ Workflow completed!")
        
        print("\nRecent audit log:")
        for log in result.get('audit_log', [])[-3:]:
            print(f"  • {log}")
    
    except Exception as e:
        print(f"❌ Error: {e}")


