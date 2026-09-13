import React from 'react';
import { Cpu, PlusCircle, Server, RefreshCw } from 'lucide-react';

interface HeaderProps {
  isOnline: boolean;
  isChecking: boolean;
  onNewSession: () => void;
  onCheckHealth: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  isOnline,
  isChecking,
  onNewSession,
  onCheckHealth,
}) => {
  return (
    <header className="app-header glass">
      <div className="header-brand">
        <div className="header-icon">
          <Cpu size={20} color="#ffffff" />
        </div>
        <div>
          <h1 className="header-title">DevOps Multi-Agent</h1>
          <div className="status-indicator">
            <span className={`status-dot ${isOnline ? '' : 'offline'}`} />
            <span>{isChecking ? 'Checking API...' : isOnline ? 'Backend Connected' : 'Backend Offline'}</span>
            <button
              onClick={onCheckHealth}
              title="Refresh connection status"
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center' }}
            >
              <RefreshCw size={12} className={isChecking ? 'spin' : ''} />
            </button>
          </div>
        </div>
      </div>

      <div className="agent-badges">
        <span className="badge badge-k8s">
          <Server size={12} /> Kubernetes
        </span>
        <span className="badge badge-aws">
          <Server size={12} /> AWS
        </span>
        <span className="badge badge-linux">
          <Server size={12} /> Linux
        </span>
      </div>

      <button className="btn-new-session" onClick={onNewSession} title="Start new conversation thread">
        <PlusCircle size={15} />
        <span>New Session</span>
      </button>
    </header>
  );
};
