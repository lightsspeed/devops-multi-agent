import React, { useState, KeyboardEvent } from 'react';
import { Send, Loader2 } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  isLoading: boolean;
  disabled?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSend,
  isLoading,
  disabled = false,
}) => {
  const [text, setText] = useState('');

  const handleSend = () => {
    if (!text.trim() || isLoading || disabled) return;
    onSend(text.trim());
    setText('');
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="input-container">
      <div className="input-box glass">
        <textarea
          className="chat-textarea"
          rows={1}
          placeholder="Ask a DevOps question or describe an incident... (Press Enter to send, Shift+Enter for newline)"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled || isLoading}
        />
        <button
          className="btn-send"
          onClick={handleSend}
          disabled={!text.trim() || isLoading || disabled}
          title="Send message"
        >
          {isLoading ? <Loader2 size={18} className="spin" /> : <Send size={18} />}
        </button>
      </div>
    </div>
  );
};
