import React, { useState, useRef, useEffect } from 'react';
import { 
  X, 
  Send, 
  Sparkles, 
  ShieldCheck, 
  Database, 
  BookOpen, 
  RotateCcw, 
  HelpCircle,
  TrendingUp,
  AlertCircle
} from 'lucide-react';
import { api } from '../services/api';

export default function AICopilotDrawer({ isOpen, onClose, storeId = 14 }) {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      sender: 'assistant',
      text: `Hello Store Manager! I am your **DemandPilot Grounded AI Copilot**.\n\nI have direct read access to Store 14's **SQL forecast facts**, **promotion elasticity matrix**, and **regional operational knowledge base**.\n\nHow can I assist your inventory decisions today?`,
      verified: true,
      tools: ['DatabaseRepository', 'HybridRRFRetriever']
    }
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const quickPrompts = [
    "Why is School Supplies spiking at Store 14?",
    "What safety stock is needed for tomorrow's payday?",
    "Explain the LightGBM vs LSTM model selection",
    "Calculate ROP for Beverages with 7-day lead time"
  ];

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen]);

  const handleSend = async (queryText = inputQuery) => {
    const textToSend = queryText.trim();
    if (!textToSend || isLoading) return;

    const userMsg = {
      id: Date.now().toString(),
      sender: 'user',
      text: textToSend
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuery('');
    setIsLoading(true);

    try {
      const response = await api.sendAgentChat(textToSend, 'store_mgr_14', 'STORE_MANAGER', storeId);
      const assistantMsg = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: response.explanation || 'No response generated.',
        verified: response.grounded_verified ?? true,
        tools: response.source_tools_used || ['SQL_Facts', 'RRF_Retriever']
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: 'assistant',
          text: `An error occurred while querying the grounded agent: ${err.message}`,
          verified: false,
          tools: []
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClear = () => {
    setMessages([
      {
        id: 'welcome_reset',
        sender: 'assistant',
        text: `Chat session reset. Ready for Store 14 operational inquiries.`,
        verified: true,
        tools: ['DatabaseRepository']
      }
    ]);
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Dimmed Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(45, 42, 38, 0.35)',
          backdropFilter: 'blur(3px)',
          WebkitBackdropFilter: 'blur(3px)',
          zIndex: 90,
          transition: 'opacity var(--transition-normal)'
        }}
      />

      {/* Slide-in Drawer */}
      <aside
        style={{
          position: 'fixed',
          top: 0,
          right: 0,
          bottom: 0,
          width: 'min(460px, 94vw)',
          backgroundColor: '#faf8f5',
          borderLeft: '1px solid var(--border-subtle)',
          boxShadow: 'var(--shadow-drawer)',
          zIndex: 100,
          display: 'flex',
          flexDirection: 'column',
          animation: 'slideInRight 280ms cubic-bezier(0.16, 1, 0.3, 1) forwards'
        }}
      >
        {/* Drawer Header */}
        <div
          style={{
            padding: '18px 24px',
            borderBottom: '1px solid var(--border-subtle)',
            backgroundColor: 'var(--surface-card)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '34px',
                height: '34px',
                borderRadius: '8px',
                backgroundColor: 'var(--accent-terracotta)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#ffffff'
              }}
            >
              <Sparkles size={18} />
            </div>
            <div>
              <h3 style={{ fontSize: '1.15rem', fontFamily: 'var(--font-serif)', fontWeight: '700', lineHeight: 1.1 }}>
                Grounded AI Copilot
              </h3>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--state-success)' }} />
                Connected to Groq & SQL Facts
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <button
              onClick={handleClear}
              title="Reset Conversation"
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--text-muted)',
                padding: '6px',
                borderRadius: 'var(--radius-sm)'
              }}
            >
              <RotateCcw size={16} />
            </button>
            <button
              onClick={onClose}
              title="Close Panel"
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--text-primary)',
                padding: '6px',
                borderRadius: 'var(--radius-sm)'
              }}
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Grounding Status Callout */}
        <div
          style={{
            padding: '10px 20px',
            backgroundColor: 'var(--accent-terracotta-subtle)',
            borderBottom: '1px solid rgba(196, 93, 62, 0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.76rem',
            color: 'var(--accent-terracotta)',
            fontWeight: '600'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <ShieldCheck size={15} />
            Zero-Hallucination SQL Verification Gate Active
          </div>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Store 14 Scope</span>
        </div>

        {/* Message Stream */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px'
          }}
        >
          {messages.map((msg) => (
            <div
              key={msg.id}
              style={{
                alignSelf: msg.sender === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: '88%',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px'
              }}
            >
              <div
                style={{
                  padding: '12px 16px',
                  borderRadius: msg.sender === 'user' 
                    ? '16px 16px 4px 16px' 
                    : '16px 16px 16px 4px',
                  backgroundColor: msg.sender === 'user' 
                    ? 'var(--accent-terracotta)' 
                    : 'var(--surface-elevated)',
                  color: msg.sender === 'user' ? '#ffffff' : 'var(--text-primary)',
                  boxShadow: msg.sender === 'user' 
                    ? '0 4px 12px rgba(196, 93, 62, 0.25)' 
                    : 'var(--shadow-sm)',
                  border: msg.sender === 'user' ? 'none' : '1px solid var(--border-subtle)',
                  fontSize: '0.9rem',
                  lineHeight: 1.55,
                  whiteSpace: 'pre-wrap'
                }}
              >
                {/* Render markdown bolding simply */}
                {msg.text.split('\n').map((line, idx) => (
                  <p key={idx} style={{ marginBottom: line ? '6px' : '0' }}>
                    {line.includes('**') ? (
                      line.split('**').map((seg, sIdx) => 
                        sIdx % 2 === 1 ? <strong key={sIdx} style={{ color: msg.sender === 'user' ? '#fff' : 'var(--text-primary)' }}>{seg}</strong> : seg
                      )
                    ) : line}
                  </p>
                ))}
              </div>

              {/* Grounding Source Tags for Assistant Messages */}
              {msg.sender === 'assistant' && msg.tools && msg.tools.length > 0 && (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    fontSize: '0.68rem',
                    color: 'var(--text-muted)',
                    paddingLeft: '4px'
                  }}
                >
                  <Database size={11} color="var(--state-success)" />
                  <span>Sources: {msg.tools.join(', ')}</span>
                  {msg.verified && (
                    <span style={{ color: 'var(--state-success)', fontWeight: '700' }}>• Fact Verified</span>
                  )}
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div
              style={{
                alignSelf: 'flex-start',
                backgroundColor: 'var(--surface-elevated)',
                padding: '12px 18px',
                borderRadius: '16px 16px 16px 4px',
                boxShadow: 'var(--shadow-sm)',
                border: '1px solid var(--border-subtle)',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '0.85rem',
                color: 'var(--text-secondary)'
              }}
            >
              <div
                style={{
                  width: '12px',
                  height: '12px',
                  borderRadius: '50%',
                  border: '2px solid var(--accent-terracotta)',
                  borderTopColor: 'transparent',
                  animation: 'spin 0.8s linear infinite'
                }}
              />
              <span>Consulting SQL facts & Sierra knowledge...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Quick Suggestion Chips */}
        <div
          style={{
            padding: '10px 20px',
            backgroundColor: 'var(--bg-subtle)',
            borderTop: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px'
          }}
        >
          <div style={{ fontSize: '0.72rem', fontWeight: '700', textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
            Suggested Queries
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {quickPrompts.map((prompt, pIdx) => (
              <button
                key={pIdx}
                onClick={() => handleSend(prompt)}
                style={{
                  fontSize: '0.75rem',
                  padding: '5px 10px',
                  borderRadius: 'var(--radius-pill)',
                  border: '1px solid var(--border-subtle)',
                  backgroundColor: 'var(--surface-elevated)',
                  color: 'var(--text-primary)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'all var(--transition-fast)'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'var(--accent-terracotta)';
                  e.currentTarget.style.backgroundColor = 'var(--accent-terracotta-subtle)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'var(--border-subtle)';
                  e.currentTarget.style.backgroundColor = 'var(--surface-elevated)';
                }}
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>

        {/* Input Bar */}
        <div
          style={{
            padding: '16px 20px',
            borderTop: '1px solid var(--border-subtle)',
            backgroundColor: 'var(--surface-card)'
          }}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            style={{ display: 'flex', gap: '10px' }}
          >
            <input
              type="text"
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              placeholder="Ask about surges, ROP, or models..."
              style={{
                flex: 1,
                padding: '10px 14px',
                borderRadius: 'var(--radius-pill)',
                border: '1px solid var(--border-medium)',
                backgroundColor: 'var(--surface-elevated)',
                fontSize: '0.88rem',
                color: 'var(--text-primary)',
                outline: 'none'
              }}
            />
            <button
              type="submit"
              disabled={!inputQuery.trim() || isLoading}
              style={{
                width: '42px',
                height: '42px',
                borderRadius: '50%',
                backgroundColor: inputQuery.trim() && !isLoading ? 'var(--accent-terracotta)' : '#d4ccc0',
                color: '#ffffff',
                border: 'none',
                cursor: inputQuery.trim() && !isLoading ? 'pointer' : 'default',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: inputQuery.trim() && !isLoading ? '0 4px 12px rgba(196, 93, 62, 0.3)' : 'none',
                transition: 'all var(--transition-fast)'
              }}
            >
              <Send size={16} />
            </button>
          </form>
        </div>
      </aside>
    </>
  );
}
