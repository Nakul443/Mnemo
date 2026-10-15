// this file is responsible for defining the ChatPanel component
// It displays the chat messages, handles user input, and manages the state of the chat interface.

import React, { useEffect, useRef } from "react";
import type { ChatMessage, RecalledFact } from "../api/types";
import type { ChatError } from "../hooks/useChat";
import { Composer } from "./Composer";
import { MessageBubble } from "./MessageBubble";

export interface ChatPanelProps {
  messages: ChatMessage[];
  pending: boolean;
  lastError: ChatError | null;
  recalledBySeq: Record<number, RecalledFact[]>;
  onSend: (text: string) => void;
  onRetry: () => void;
  onFactHover?: (factId: string | null) => void;
  onFactClick?: (factId: string) => void;
}

const SUGGESTION_CHIPS = [
  "I'm building Project X, a task manager, in Python.",
  "I prefer short, direct answers.",
  "What do you know about Project X?",
];

export const ChatPanel: React.FC<ChatPanelProps> = ({
  messages,
  pending,
  lastError,
  recalledBySeq,
  onSend,
  onRetry,
  onFactHover,
  onFactClick,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, pending, lastError]);

  const handleChipClick = (chipText: string) => {
    onSend(chipText);
  };

  return (
    <div className="chat-panel">
      <div className="message-list" ref={scrollRef} aria-live="polite">
        {messages.length === 0 ? (
          <div className="chat-empty-state">
            <p className="empty-text">
              Tell Mnemo about your projects. It remembers across sessions.
            </p>
            <div className="suggestion-chips">
              {SUGGESTION_CHIPS.map((chip, i) => (
                <button
                  key={i}
                  type="button"
                  className="suggestion-chip"
                  onClick={() => handleChipClick(chip)}
                >
                  {chip}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <MessageBubble
              key={`${msg.role}-${msg.seq}`}
              message={msg}
              recalled={recalledBySeq[msg.seq]}
              onFactHover={onFactHover}
              onFactClick={onFactClick}
            />
          ))
        )}

        {pending && (
          <div className="message-bubble-wrapper wrapper-assistant">
            <div className="message-bubble bubble-assistant typing-bubble">
              <span className="typing-dot" />
              <span className="typing-dot" />
              <span className="typing-dot" />
              <span className="typing-caption">Mnemo is thinking…</span>
            </div>
          </div>
        )}

        {lastError && (
          <div className="chat-error-banner">
            <span className="error-message">{lastError.message}</span>
            {lastError.isRetryable && (
              <button
                type="button"
                className="btn-error-retry"
                onClick={onRetry}
              >
                Retry
              </button>
            )}
          </div>
        )}
      </div>

      <Composer onSend={onSend} disabled={pending} />
    </div>
  );
};
