import React, { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { ChatMessage, Message } from './components/ChatMessage';
import { ChatInput } from './components/ChatInput';
import { checkHealth, sendChatMessage } from './services/api';
import { Terminal, ShieldAlert, Cpu } from 'lucide-react';

export const App: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [threadId, setThreadId] = useState<string>(() => 'thread-' + Math.random().toString(36).substring(2, 9));
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isOnline, setIsOnline] = useState<boolean>(true);
  const [isChecking, setIsChecking] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const historyEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    historyEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const verifyHealth = async () => {
    setIsChecking(true);
    setErrorMsg(null);
    try {
      await checkHealth();
      setIsOnline(true);
    } catch {
      setIsOnline(false);
    } finally {
      setIsChecking(false);
    }
  };

  useEffect(() => {
    verifyHealth();
  }, []);

  const handleNewSession = () => {
    setThreadId('thread-' + Math.random().toString(36).substring(2, 9));
    setMessages([]);
    setErrorMsg(null);
  };

  const handleSendMessage = async (userText: string) => {
    const userMsg: Message = {
      id: 'msg-' + Date.now(),
      sender: 'user',
      text: userText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);
    setErrorMsg(null);

    try {
      const response = await sendChatMessage({
        message: userText,
        thread_id: threadId,
      });

      const assistantMsg: Message = {
        id: 'msg-' + (Date.now() + 1),
        sender: 'assistant',
        text: response.response,
        selected_agent: response.selected_agent,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, assistantMsg]);
      if (response.thread_id) {
        setThreadId(response.thread_id);
      }
    } catch (err: any) {
      console.error('Chat error:', err);
      setErrorMsg(err.message || 'Failed to connect to DevOps Multi-Agent backend.');
    } finally {
      setIsLoading(false);
    }
  };

  const samplePrompts = [
    {
      agent: 'Kubernetes',
      text: 'My payment-api pod is stuck in CrashLoopBackOff. How do I troubleshoot?',
      color: '#60a5fa',
    },
    {
      agent: 'AWS',
      text: 'My EC2 instance cannot connect to my S3 bucket. What IAM/VPC rules should I check?',
      color: '#fbbf24',
    },
    {
      agent: 'Linux',
      text: 'The server disk is at 98% utilization and high CPU load. Which commands should I run?',
      color: '#34d399',
    },
  ];

  return (
    <div className="app-main">
      <Header
        isOnline={isOnline}
        isChecking={isChecking}
        onNewSession={handleNewSession}
        onCheckHealth={verifyHealth}
      />

      <main className="chat-container">
        {messages.length === 0 ? (
          <div className="welcome-screen">
            <div className="header-icon" style={{ width: 48, height: 48 }}>
              <Cpu size={28} color="#ffffff" />
            </div>
            <h2 className="welcome-title">DevOps Multi-Agent Assistant</h2>
            <p className="welcome-subtitle">
              Ask questions about Kubernetes, AWS, or Linux infrastructure. The intelligent supervisor routes your query to the exact specialist agent.
            </p>

            <div className="sample-prompts">
              {samplePrompts.map((p, idx) => (
                <button
                  key={idx}
                  className="prompt-card"
                  onClick={() => handleSendMessage(p.text)}
                >
                  <span className="prompt-card-agent" style={{ color: p.color }}>
                    {p.agent} Agent
                  </span>
                  <span className="prompt-card-text">{p.text}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="chat-history">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
            {isLoading && (
              <div className="message-item assistant">
                <div className="avatar">
                  <Terminal size={18} />
                </div>
                <div className="message-content">
                  <div className="message-bubble" style={{ color: 'var(--text-muted)' }}>
                    Supervisor routing and generating specialist diagnosis...
                  </div>
                </div>
              </div>
            )}
            <div ref={historyEndRef} />
          </div>
        )}

        {errorMsg && (
          <div
            style={{
              padding: '0.75rem 1rem',
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: 'var(--radius-md)',
              color: '#f87171',
              fontSize: '0.85rem',
              margin: '0.5rem 0',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <ShieldAlert size={18} />
            <span>{errorMsg}</span>
          </div>
        )}

        <ChatInput
          onSend={handleSendMessage}
          isLoading={isLoading}
          disabled={!isOnline}
        />
      </main>
    </div>
  );
};

export default App;
