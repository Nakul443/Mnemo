// this file is responsible for defining the Composer component
// It provides a text area for user input,
// handles submission of messages, and manages the state of the input field.
// In simple words,
    // it allows users to type messages,
    // automatically grows the text area as they type,
    // and sends the message when they press Enter or click the send button.

import React, { useEffect, useRef, useState } from "react";

export interface ComposerProps {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export const Composer: React.FC<ComposerProps> = ({ onSend, disabled = false }) => {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-grow textarea up to 5 rows
  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      const newHeight = Math.min(el.scrollHeight, 120); // ~5 rows
      el.style.height = `${newHeight}px`;
    }
  }, [text]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const charCount = text.length;
  const showCounter = charCount > 3500;

  return (
    <div className="composer-container">
      {showCounter && (
        <div className="char-counter">
          {charCount}/4000
        </div>
      )}
      <div className="composer-input-row">
        <textarea
          ref={textareaRef}
          className="composer-textarea"
          rows={1}
          placeholder="Tell Mnemo about your project…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          maxLength={4000}
        />
        <button
          type="button"
          className="btn-send"
          onClick={handleSubmit}
          disabled={disabled || !text.trim()}
          title="Send message (Enter)"
        >
          {disabled ? <span className="btn-spinner" /> : "↑"}
        </button>
      </div>
    </div>
  );
};
