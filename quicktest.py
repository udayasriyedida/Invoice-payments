#!/usr/bin/env python3
"""
Interactive test with DETAILED step-by-step output showing all workflow points A-R
"""

import os
from newcode import *
from langgraph.types import Command

def get_project_inputs():
    """Get project details from user including client email"""
    print("🎯 COMPLETE INVOICE-TO-CASH WORKFLOW (A-R)")
    print("=" * 60)
    print("Please provide your project details:\n")
    
    project_name = input("Project Name: ").strip()
    if not project_name:
        project_name = "Default Project"
    
    client_name = input("Client Name: ").strip()
    if not client_name:
        client_name = "Default Client"
    
    client_email = input("Client Email: ").strip()
    if not client_email or "@" not in client_email:
        client_email = "client@example.com"
    
    currency = input("Currency (USD/EUR/GBP/INR): ").strip().upper()
    if currency not in ['USD', 'EUR', 'GBP', 'INR', 'CAD', 'AUD']:
        currency = "USD"
    
    while True:
        try:
            total_amount = float(input(f"Total Amount ({currency}): ").strip())
            if total_amount > 0:
                break
            else:
                print("❌ Amount must be positive")
        except ValueError:
            print("❌ Please enter a valid number")
    
    return {
        "project_name": project_name,
        "client_name": client_name,
        "client_email": client_email,
        "currency": currency,
        "total_amount": total_amount
    }

def print_step_separator(step, description):
    """Print a visual separator for each workflow step"""
    print(f"\n{'='*80}")
    print(f"📍 POINT {step}: {description}")
    print(f"{'='*80}")

def print_audit_entries(result, prev_count):
    """Print new audit log entries since last check"""
    audit_log = result.get("audit_log", [])
    new_entries = audit_log[prev_count:]
    
    for entry in new_entries:
        print(f"🔍 AUDIT: {entry}")
    
    return len(audit_log)

def print_ai_messages(result, prev_count):
    """Print new AI messages since last check"""
    messages = result.get("messages", [])
    new_messages = messages[prev_count:]
    
    for msg in new_messages:
        print(f"🤖 AI MSG: {msg.content}")
    
    return len(messages)

def print_workflow_state(result, step_name):
    """Print current workflow state information"""
    print(f"\n📊 CURRENT STATE after {step_name}:")
    print(f"  • Project ID: {result.get('project_id', 'N/A')}")
    print(f"  • Current Milestone: {result.get('current_milestone', {}).get('name', 'N/A')}")
    print(f"  • Invoice ID: {result.get('invoice_id', 'N/A')}")
    print(f"  • Invoice Amount: {result.get('currency', 'USD')} {result.get('invoice_amount', 0):,.2f}")
    print(f"  • Payment Received: {result.get('payment_received', False)}")
    print(f"  • Reminders Sent: {result.get('reminders_sent', 0)}")
    print(f"  • Escalated to Finance: {result.get('escalated_to_finance', False)}")
    print(f"  • Legal Flag: {result.get('legal_flag_raised', False)}")

def test_detailed_workflow():
    if not os.getenv("OPENROUTER_API_KEY"):
        print("❌ Set OPENROUTER_API_KEY environment variable")
        return
    
    # Get user inputs
    user_inputs = get_project_inputs()
    user_inputs["thread_id"] = "detailed-interactive-test"
    
    config = {"configurable": {"thread_id": "detailed-interactive-test"}}
    
    print(f"\n🚀 Starting COMPLETE A-R workflow...")
    print(f"Project: {user_inputs['project_name']}")
    print(f"Client: {user_inputs['client_name']} ({user_inputs['client_email']})")
    print(f"Budget: {user_inputs['currency']} {user_inputs['total_amount']:,.2f}")
    print("=" * 80)
    
    print("\n🗺️  WORKFLOW MAP:")
    print("A→B→C→[D→E→F→G or G]→H→[I→J→K→L or M→N→[P→Q→R or O→M]]")
    print("HIL Points: C (Milestone), H (Payment), N (Escalation)")
    
    # Track audit and message counts
    prev_audit_count = 0
    prev_msg_count = 0
    
    # Start workflow - this will execute A and B automatically
    print_step_separator("A", "Project Initiated")
    print("🎬 Executing: Project initiation with user inputs...")
    
    print_step_separator("B", "AI Billing Plan & Milestones Generation")
    print("🤖 Executing: AI analyzing project and generating milestones...")
    
    result = workflow.invoke(user_inputs, config=config)
    
    # Show A and B results
    prev_audit_count = print_audit_entries(result, prev_audit_count)
    prev_msg_count = print_ai_messages(result, prev_msg_count)
    
    # Show generated milestones
    if result.get('milestones'):
        print(f"\n🎯 AI GENERATED MILESTONES:")
        for i, milestone in enumerate(result['milestones'], 1):
            print(f"  {i}. {milestone['name']} - {user_inputs['currency']} {milestone['amount']:,.2f}")
            print(f"     Deliverables: {', '.join(milestone['deliverables'])}")
    
    print_workflow_state(result, "A-B")
    
    interrupt_count = 0
    step_history = []
    
    while "__interrupt__" in result:
        interrupt_count += 1
        interrupt_data = result["__interrupt__"][0].value
        current_step = interrupt_data.get('step', 'Unknown')
        step_name = interrupt_data.get('step_name', 'Decision Point')
        
        print_step_separator(current_step, f"{step_name} (HIL)")
        
        # Show step-specific information
        if current_step == 'C':  # Milestone check
            print("🎯 MILESTONE COMPLETION CHECK:")
            print(f"  • Milestone: {interrupt_data.get('milestone_name')}")
            print(f"  • Description: {interrupt_data.get('milestone_description', 'N/A')}")
            print(f"  • Amount: {interrupt_data.get('currency', user_inputs['currency'])} {interrupt_data.get('amount', 0):,.2f}")
            print(f"  • Progress: {interrupt_data.get('milestone_progress')}")
            print(f"  • Deliverables: {', '.join(interrupt_data.get('deliverables', []))}")
            print(f"  • Estimated Duration: {interrupt_data.get('estimated_duration', 'N/A')}")
            
        elif current_step == 'H':  # Payment check
            print("💰 PAYMENT STATUS VERIFICATION:")
            print(f"  • Invoice: {interrupt_data.get('invoice_id')}")
            print(f"  • Amount: {interrupt_data.get('currency', user_inputs['currency'])} {interrupt_data.get('invoice_amount', 0):,.2f}")
            print(f"  • Client Email: {interrupt_data.get('context', {}).get('client_email', 'N/A')}")
            print(f"  • Days Overdue: {interrupt_data.get('overdue_days', 0)}")
            print(f"  • Reminders Sent: {interrupt_data.get('reminders_sent', 0)}")
            
        elif current_step == 'N':  # Overdue escalation
            print("⚠️  OVERDUE PAYMENT ESCALATION:")
            print(f"  • Invoice: {interrupt_data.get('invoice_id')}")
            print(f"  • Client: {interrupt_data.get('client_name')} ({interrupt_data.get('client_email')})")
            print(f"  • Days Overdue: {interrupt_data.get('overdue_days', 0)}")
            print(f"  • Reminders Sent: {interrupt_data.get('reminders_sent', 0)}")
            print(f"  • Invoice Amount: {interrupt_data.get('currency', user_inputs['currency'])} {interrupt_data.get('invoice_amount', 0):,.2f}")
        
        # Show instructions and question
        print(f"\n📋 INSTRUCTIONS: {interrupt_data.get('instructions', 'Make your decision')}")
        print(f"❓ QUESTION: {interrupt_data.get('question')}")
        print(f"🎛️  OPTIONS: {' / '.join(interrupt_data.get('options', ['yes', 'no']))}")
        
        # Get human input
        while True:
            print(f"\n{'─'*50}")
            human_input = input(f"👤 Your decision for Point {current_step}: ").strip()
            if human_input:
                break
            print("❌ Please enter a decision")
        
        print(f"✅ DECISION: {human_input}")
        step_history.append(f"{current_step}: {human_input}")
        
        # Predict next steps based on decision
        if current_step == 'C':
            if human_input.lower() in ['yes', 'y']:
                print("🔮 NEXT STEPS: D→E→F→G→H (Invoice generation sequence)")
            else:
                print("🔮 NEXT STEPS: G→H (Direct to monitoring)")
        elif current_step == 'H':
            if human_input.lower() in ['yes', 'y']:
                print("🔮 NEXT STEPS: I→J→K→L (Payment reconciliation)")
            else:
                print("🔮 NEXT STEPS: M→N (Payment reminders)")
        elif current_step == 'N':
            if human_input.lower() in ['yes', 'y']:
                print("🔮 NEXT STEPS: P→Q→R (Finance escalation)")
            else:
                print("🔮 NEXT STEPS: O→M (Wait and retry)")
        
        # Resume workflow and show all intermediate steps
        try:
            result = workflow.invoke(Command(resume=human_input), config=config)
            
            # Print all new audit entries (showing intermediate steps)
            print(f"\n🔄 EXECUTING WORKFLOW STEPS...")
            prev_audit_count = print_audit_entries(result, prev_audit_count)
            prev_msg_count = print_ai_messages(result, prev_msg_count)
            
            print_workflow_state(result, f"after Point {current_step}")
            
        except Exception as e:
            print(f"❌ ERROR during workflow execution: {e}")
            break
    
    # Final completion
    print(f"\n{'='*80}")
    print("🎉 WORKFLOW EXECUTION COMPLETED!")
    print(f"{'='*80}")
    print(f"Total Human Decisions Made: {interrupt_count}")
    print(f"Decision History: {' → '.join(step_history)}")
    
    # Show final state
    print(f"\n📊 FINAL WORKFLOW STATE:")
    print(f"  • Project Status: {'✅ Completed' if result.get('milestone_paid') else '⏳ In Progress'}")
    print(f"  • Total Milestones: {len(result.get('milestones', []))}")
    print(f"  • Current Milestone Index: {result.get('current_milestone_index', 0) + 1}")
    print(f"  • Payment Status: {'✅ Received' if result.get('payment_received') else '❌ Pending'}")
    print(f"  • Total Reminders Sent: {result.get('reminders_sent', 0)}")
    print(f"  • Finance Escalation: {'✅ Yes' if result.get('escalated_to_finance') else '❌ No'}")
    print(f"  • Legal Action: {'✅ Initiated' if result.get('legal_flag_raised') else '❌ Not Required'}")
    
    # Show milestone progress
    if result.get('milestones'):
        print(f"\n🏁 MILESTONE PROGRESS:")
        current_index = result.get('current_milestone_index', 0)
        for i, milestone in enumerate(result['milestones']):
            status = "✅ PAID" if i < current_index or (i == current_index and result.get('milestone_paid')) else "⏳ PENDING"
            print(f"  {i+1}. {milestone['name']} - {user_inputs['currency']} {milestone['amount']:,.2f} [{status}]")
    
    # Complete audit trail
    print(f"\n📋 COMPLETE AUDIT TRAIL (All {len(result.get('audit_log', []))} entries):")
    for i, log_entry in enumerate(result.get("audit_log", []), 1):
        step_letter = log_entry.split(':')[0] if ':' in log_entry else f"{i:2d}"
        print(f"  {step_letter:2}. {log_entry}")
    
    # Show all AI messages
    print(f"\n🤖 ALL AI MESSAGES ({len(result.get('messages', []))} total):")
    for i, msg in enumerate(result.get("messages", []), 1):
        print(f"  {i:2d}. {msg.content}")

if __name__ == "__main__":
    test_detailed_workflow()
