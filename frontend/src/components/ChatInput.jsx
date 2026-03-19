import React, { useState, useRef, useEffect } from 'react';

export default function ChatInput({ onSend, isLoading }) {
  const [text, setText] = useState('');
  const textareaRef = useRef(null);

  useEffect(() => {
    if (!isLoading && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isLoading]);

  function handleSubmit(e) {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;
    onSend(trimmed);
    setText('');
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      handleSubmit(e);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="chat-input-area">
      <div className="card" style={{ marginBottom: 0 }}>
        <textarea
          ref={textareaRef}
          className="form-textarea"
          rows={4}
          placeholder="Type your trading thought or feeling... e.g. 'I feel like BTC is going to moon, I want to go all in right now'"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          style={{ marginBottom: '0.75rem', minHeight: '100px' }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Ctrl+Enter to send
          </span>
          <button type="submit" className="btn btn-primary btn-lg" disabled={isLoading || !text.trim()}>
            {isLoading ? (
              <>
                <span className="spinner" />
                Analyzing...
              </>
            ) : (
              'Analyze'
            )}
          </button>
        </div>
      </div>
    </form>
  );
}
