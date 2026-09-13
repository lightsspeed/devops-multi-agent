import React from 'react';
import { User, Bot, Server } from 'lucide-react';

export interface Message {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  selected_agent?: 'kubernetes' | 'aws' | 'linux' | string;
  timestamp: string;
}

interface ChatMessageProps {
  message: Message;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.sender === 'user';

  const getBadgeClass = (agent?: string) => {
    switch (agent?.toLowerCase()) {
      case 'kubernetes':
        return 'badge-k8s';
      case 'aws':
        return 'badge-aws';
      case 'linux':
        return 'badge-linux';
      default:
        return 'badge-linux';
    }
  };

  return (
    <div className={`message-item ${isUser ? 'user' : 'assistant'}`}>
      <div className="avatar">
        {isUser ? <User size={18} /> : <Bot size={18} />}
      </div>

      <div className="message-content">
        <div className="message-bubble">
          {message.text}
        </div>

        <div className="message-meta">
          <span>{message.timestamp}</span>
          {!isUser && message.selected_agent && (
            <span className={`badge ${getBadgeClass(message.selected_agent)}`} style={{ padding: '0.1rem 0.4rem', fontSize: '0.65rem' }}>
              <Server size={10} /> {message.selected_agent} agent
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
