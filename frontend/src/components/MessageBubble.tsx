// this file is responsible for defining the MessageBubble component
// It displays individual chat messages and, if applicable, the recalled facts associated with assistant messages.
// In simple words,
    // it shows a single message in the chat,
    // and if the message is from the assistant and has recalled facts,
    // it displays those facts below the message.

import React from "react";
import type { ChatMessage, RecalledFact } from "../api/types";
import { RecalledChips } from "./RecalledChips";

export interface MessageBubbleProps {
  message: ChatMessage;
  recalled?: RecalledFact[];
  onFactHover?: (factId: string | null) => void;
  onFactClick?: (factId: string) => void;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  recalled,
  onFactHover,
  onFactClick,
}) => {
  const isUser = message.role === "user";

  return (
    <div className={`message-bubble-wrapper ${isUser ? "wrapper-user" : "wrapper-assistant"}`}>
      <div className={`message-bubble ${isUser ? "bubble-user" : "bubble-assistant"}`}>
        <div className="bubble-text">{message.text}</div>
      </div>
      {!isUser && recalled && recalled.length > 0 && (
        <RecalledChips
          recalled={recalled}
          onFactHover={onFactHover}
          onFactClick={onFactClick}
        />
      )}
    </div>
  );
};
