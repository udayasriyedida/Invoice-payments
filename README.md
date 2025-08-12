# Invoice-to-Cash Workflow Automation

This project implements an **Invoice-to-Cash process automation** using **Python**, **LangGraph**, and **LangChain**.  
It converts a static business workflow  into an **automated backend system** that handles:

- Milestone-based billing plan generation
- Automatic invoice creation
- Payment tracking
- Escalation to finance/legal teams
- Full audit logging

---

## 📌 Problem Statement

In many project-based businesses, invoicing and payment follow-up are **manual and error-prone**.  
Invoices are delayed, reminders are inconsistent, and overdue cases lack a clear escalation path.  

This system solves that by **automating** the process end-to-end, ensuring:
- Invoices go out immediately at milestone completion
- Overdue cases trigger reminders and escalation
- Full compliance via audit logs

---

## 🔄 Workflow Overview

The workflow follows the original **Invoice & Payments System** PDF:

1. **Start Project (A)** → Store client & project details.
2. **Define Billing Plan (B)** → AI generates milestones & first invoice.
3. **Milestone Check (C)** → Human-in-the-loop decision on completion.
4. **Invoice Logging & Dispatch (E–F)** → Save in audit trail, send to client.
5. **Monitor Payments (G)** → Check overdue status.
6. **Payment Verification (H)** → Human check if payment received.
7. **If Paid (I–L)** → Reconcile, mark milestone as paid, notify stakeholders.
8. **If Not Paid (M–N–O)** → Send reminders, decide escalation.
9. **Escalation (P–Q–R)** → Finance or legal recovery if overdue >60 days.

---

## 🧠 AI Usage

- **Step B**: Uses LangChain with OpenRouter to generate a professional billing plan and invoice JSON.
---

## 📂 Tech Stack

- **Python 3.10+**
- **LangGraph** – State machine workflow engine
- **LangChain** – AI-powered invoice & milestone generation
- **Pydantic** – Data validation
- **dotenv** – Environment variable management
- **OpenRouter API** – LLM access

---

## 📜 Key Features

- **Dynamic Workflow Routing** – Follows business logic exactly as in the PDF.
- **Overdue Detection** – >30 days triggers reminder/escalation; >60 days triggers legal flag.
- **Audit Logging** – Tracks every step for compliance.
- **Email Reminders (extendable)** – Step M can integrate SMTP or SendGrid for real reminders.

---

## 🚀 Running the Project

1. **Clone the repository**
```bash
git clone https://github.com/your-username/invoice-to-cash-workflow.git
cd invoice-to-cash-workflow
