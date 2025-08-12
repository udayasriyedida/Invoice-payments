// src/App.js - Updated to show billing plan and milestones

import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

// Set your FastAPI base URL
axios.defaults.baseURL = 'http://127.0.0.1:8000';

function App() {
  const [activeTab, setActiveTab] = useState('start');
  const [threadId, setThreadId] = useState('');
  const [statusThreadId, setStatusThreadId] = useState('');
  
  const [form, setForm] = useState({
    project_name: '',
    client_name: '',
    client_email: '',
    currency: 'USD',
    total_amount: '',
  });
  
  const [workflow, setWorkflow] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const startWorkflow = async () => {
    setLoading(true);
    setError('');
    try {
      const resp = await axios.post('http://127.0.0.1:8000/workflow/start', {
        ...form,
        total_amount: parseFloat(form.total_amount)
      });
      setThreadId(resp.data.thread_id);
      setWorkflow(resp.data);
      setActiveTab('resume');
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const resumeWorkflow = async (decision) => {
    setLoading(true);
    setError('');
    try {
      const resp = await axios.post(`http://127.0.0.1:8000/workflow/resume/${threadId}`, { decision });
      setWorkflow(resp.data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const checkWorkflowStatus = async () => {
    setLoading(true);
    setError('');
    try {
      const resp = await axios.get(`http://127.0.0.1:8000/workflow/status/${statusThreadId}`);
      setWorkflow(resp.data);
      setThreadId(statusThreadId);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const resetWorkflow = () => {
    setWorkflow(null);
    setThreadId('');
    setStatusThreadId('');
    setError('');
    setForm({
      project_name: '',
      client_name: '',
      client_email: '',
      currency: 'USD',
      total_amount: '',
    });
  };

  return (
    <div className="App">
      <header>
        <h1>🧾 Invoice-to-Cash Workflow</h1>
        <nav className="tabs">
          <button 
            className={activeTab === 'start' ? 'active' : ''}
            onClick={() => setActiveTab('start')}
          >
            Start New Workflow
          </button>
          <button 
            className={activeTab === 'resume' ? 'active' : ''}
            onClick={() => setActiveTab('resume')}
          >
            Resume Workflow
          </button>
          <button 
            className={activeTab === 'status' ? 'active' : ''}
            onClick={() => setActiveTab('status')}
          >
            Check Status
          </button>
        </nav>
      </header>

      {error && (
        <div className="error">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* START WORKFLOW TAB */}
      {activeTab === 'start' && (
        <section className="start-form">
          <h2>🚀 Start New Workflow</h2>
          <div className="form-grid">
            <label>
              Project Name *
              <input 
                placeholder="e.g., E-commerce Platform Development"
                value={form.project_name}
                onChange={e => setForm({ ...form, project_name: e.target.value })} 
              />
            </label>
            
            <label>
              Client Name *
              <input 
                placeholder="e.g., TechCorp Solutions"
                value={form.client_name}
                onChange={e => setForm({ ...form, client_name: e.target.value })} 
              />
            </label>
            
            <label>
              Client Email *
              <input 
                type="email"
                placeholder="e.g., finance@techcorp.com"
                value={form.client_email}
                onChange={e => setForm({ ...form, client_email: e.target.value })} 
              />
            </label>
            
            <label>
              Currency
              <select value={form.currency}
                      onChange={e => setForm({ ...form, currency: e.target.value })}>
                {['USD','EUR','GBP','INR','CAD','AUD'].map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </label>
            
            <label>
              Total Amount *
              <input 
                type="number" 
                step="0.01"
                placeholder="e.g., 50000"
                value={form.total_amount}
                onChange={e => setForm({ ...form, total_amount: e.target.value })} 
              />
            </label>
          </div>
          
          <button 
            onClick={startWorkflow} 
            disabled={loading || !form.project_name || !form.client_name || !form.client_email || !form.total_amount}
            className="primary-btn"
          >
            {loading ? '🔄 Starting...' : '🚀 Start Workflow'}
          </button>
        </section>
      )}

      {/* RESUME WORKFLOW TAB */}
      {activeTab === 'resume' && (
        <section className="resume-form">
          <h2>▶️ Resume Workflow</h2>
          
          {!workflow && (
            <div className="thread-input">
              <label>
                Thread ID
                <input 
                  placeholder="Enter existing thread ID or start a new workflow"
                  value={threadId}
                  onChange={e => setThreadId(e.target.value)} 
                />
              </label>
              <p className="hint">
                💡 Thread ID is provided when you start a workflow
              </p>
            </div>
          )}
          
          {threadId && !workflow && (
            <button 
              onClick={() => checkWorkflowStatus()} 
              disabled={loading}
              className="secondary-btn"
            >
              {loading ? '🔄 Loading...' : '🔍 Load Workflow'}
            </button>
          )}
        </section>
      )}

      {/* CHECK STATUS TAB */}
      {activeTab === 'status' && (
        <section className="status-form">
          <h2>🔍 Check Workflow Status</h2>
          
          <div className="thread-input">
            <label>
              Thread ID to Check
              <input 
                placeholder="Enter thread ID to check status"
                value={statusThreadId}
                onChange={e => setStatusThreadId(e.target.value)} 
              />
            </label>
          </div>
          
          <button 
            onClick={checkWorkflowStatus} 
            disabled={loading || !statusThreadId}
            className="secondary-btn"
          >
            {loading ? '🔄 Checking...' : '🔍 Check Status'}
          </button>
        </section>
      )}

      {/* WORKFLOW DISPLAY */}
      {workflow && (
        <section className="workflow">
          <div className="workflow-header">
            <h2>📋 Workflow Status</h2>
            <div className="workflow-meta">
              <span className="thread-id">Thread: <code>{workflow.thread_id}</code></span>
              <button onClick={resetWorkflow} className="reset-btn">🆕 New Workflow</button>
            </div>
          </div>

          {/* 🆕 BILLING PLAN & MILESTONES DISPLAY */}
          {workflow.billing_plan && (
            <div className="billing-section">
              <h3>💰 AI-Generated Billing Plan</h3>
              <div className="billing-plan">
                <div className="plan-summary">
                  <div className="plan-item">
                    <strong>Total Amount:</strong> 
                    <span>{workflow.billing_plan.currency} {workflow.billing_plan.total_amount?.toLocaleString()}</span>
                  </div>
                  <div className="plan-item">
                    <strong>Payment Terms:</strong> 
                    <span>{workflow.billing_plan.payment_terms}</span>
                  </div>
                  <div className="plan-item">
                    <strong>Payment Structure:</strong> 
                    <span>{workflow.billing_plan.payment_structure}</span>
                  </div>
                  <div className="plan-item">
                    <strong>Milestone Count:</strong> 
                    <span>{workflow.billing_plan.milestone_count}</span>
                  </div>
                </div>
                
                {workflow.ai_reasoning && (
                  <div className="ai-reasoning">
                    <h4>🤖 AI Reasoning:</h4>
                    <p>{workflow.ai_reasoning}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 🆕 MILESTONES DISPLAY */}
          {workflow.milestones && workflow.milestones.length > 0 && (
            <div className="milestones-section">
              <h3>🎯 Project Milestones ({workflow.milestones.length})</h3>
              <div className="milestones-grid">
                {workflow.milestones.map((milestone, index) => (
                  <div 
                    key={milestone.id} 
                    className={`milestone-card ${index === workflow.state?.current_milestone_index ? 'current' : ''}`}
                  >
                    <div className="milestone-header">
                      <h4>{milestone.name}</h4>
                      <div className="milestone-meta">
                        <span className="milestone-id">{milestone.id}</span>
                        <span className="milestone-amount">
                          {workflow.billing_plan?.currency} {milestone.amount?.toLocaleString()}
                        </span>
                        <span className="milestone-percentage">
                          {milestone.percentage}%
                        </span>
                      </div>
                    </div>
                    
                    <p className="milestone-description">{milestone.description}</p>
                    
                    <div className="milestone-details">
                      <div className="deliverables">
                        <strong>Deliverables:</strong>
                        <ul>
                          {milestone.deliverables?.map((deliverable, i) => (
                            <li key={i}>{deliverable}</li>
                          ))}
                        </ul>
                      </div>
                      
                      <div className="milestone-footer">
                        <span className="duration">
                          ⏱️ {milestone.estimated_duration}
                        </span>
                        {milestone.dependencies?.length > 0 && (
                          <span className="dependencies">
                            🔗 Depends on: {milestone.dependencies.join(', ')}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* HUMAN INPUT REQUIRED */}
          {workflow.interrupt && (
            <div className="interrupt">
              <div className="step-header">
                <h3>🤚 Step {workflow.interrupt.step}: {workflow.interrupt.step_name}</h3>
                <span className="status-badge pending">Pending Input</span>
              </div>
              
              <div className="step-content">
                <p className="instructions">
                  <strong>📋 Instructions:</strong> {workflow.interrupt.instructions}
                </p>
                
                <p className="question">
                  <strong>❓ Question:</strong> {workflow.interrupt.question}
                </p>

                {/* Context Information */}
                {workflow.interrupt.context && Object.keys(workflow.interrupt.context).length > 0 && (
                  <details className="context">
                    <summary>📄 Additional Context</summary>
                    <pre>{JSON.stringify(workflow.interrupt.context, null, 2)}</pre>
                  </details>
                )}
              </div>
              
              <div className="options">
                <strong>Choose an option:</strong>
                <div className="option-buttons">
                  {workflow.interrupt.options.map(opt => (
                    <button 
                      key={opt}
                      onClick={() => resumeWorkflow(opt)}
                      disabled={loading}
                      className={`option-btn ${opt.toLowerCase()}`}
                    >
                      {loading ? '🔄' : opt === 'yes' ? '✅' : opt === 'no' ? '❌' : '📝'} {opt.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* WORKFLOW COMPLETED */}
          {workflow.completed && !workflow.interrupt && (
            <div className="completed">
              <h3>🎉 Workflow Completed Successfully!</h3>
              <p>All steps have been processed.</p>
            </div>
          )}

          {/* CURRENT STATE SUMMARY */}
          {workflow.state && (
            <div className="state-summary">
              <h3>📊 Current State</h3>
              <div className="state-grid">
                <div className="state-item">
                  <strong>Project ID:</strong> 
                  <span>{workflow.state.project_id || 'N/A'}</span>
                </div>
                <div className="state-item">
                  <strong>Current Milestone:</strong> 
                  <span>{workflow.state.current_milestone || 'N/A'}</span>
                </div>
                <div className="state-item">
                  <strong>Invoice ID:</strong> 
                  <span>{workflow.state.invoice_id || 'Not Generated'}</span>
                </div>
                <div className="state-item">
                  <strong>Payment Received:</strong> 
                  <span className={workflow.state.payment_received ? 'success' : 'pending'}>
                    {workflow.state.payment_received ? '✅ Yes' : '⏳ No'}
                  </span>
                </div>
                <div className="state-item">
                  <strong>Reminders Sent:</strong> 
                  <span>{workflow.state.reminders_sent || 0}</span>
                </div>
                <div className="state-item">
                  <strong>Escalated to Finance:</strong> 
                  <span className={workflow.state.escalated_to_finance ? 'warning' : 'success'}>
                    {workflow.state.escalated_to_finance ? '⚠️ Yes' : '✅ No'}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* SYSTEM MESSAGES */}
          <div className="messages">
            <h3>🤖 System Messages ({workflow.messages?.length || 0})</h3>
            <div className="message-list">
              {workflow.messages?.length > 0 ? (
                workflow.messages.map((m, i) => (
                  <div key={i} className="message-item">
                    {m}
                  </div>
                ))
              ) : (
                <p className="no-data">No messages yet</p>
              )}
            </div>
          </div>

          {/* AUDIT LOG */}
          <div className="audit-log">
            <h3>📋 Complete Audit Trail ({workflow.audit_log?.length || 0})</h3>
            <div className="audit-list">
              {workflow.audit_log?.length > 0 ? (
                workflow.audit_log.map((entry, i) => (
                  <div key={i} className="audit-item">
                    <span className="audit-step">
                      {entry.split(':')[0]}:
                    </span>
                    <span className="audit-content">
                      {entry.substring(entry.indexOf(':') + 1).trim()}
                    </span>
                  </div>
                ))
              ) : (
                <p className="no-data">No audit entries yet</p>
              )}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

export default App;
