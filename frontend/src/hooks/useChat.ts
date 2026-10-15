// this file is responsible for defining the useChat hook
// that will be used to manage the chat state in the frontend
// in simple words,
    // it handles the chat messages, pending state, last error, recalled facts,
    // and provides functions to send messages, retry failed messages, clear messages,
    // and load messages for a given session ID

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { ChatMessage, RecalledFact } from "../api/types";

export interface ChatError {
  message: string;
  failedText: string;
  isRetryable: boolean;
}

export interface UseChatReturn {
  messages: ChatMessage[];
  pending: boolean;
  lastError: ChatError | null;
  recalledBySeq: Record<number, RecalledFact[]>;
  sendMessage: (text: string) => Promise<void>;
  retryMessage: () => Promise<void>;
  clearMessages: () => void;
  loadMessages: (sessionId: string) => Promise<void>;
}

export function useChat(
  sessionId: string | null,
  onRecalled?: (factIds: string[], entityIds: string[]) => void,
  onChatDone?: () => void
): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pending, setPending] = useState<boolean>(false);
  const [lastError, setLastError] = useState<ChatError | null>(null);
  const [recalledBySeq, setRecalledBySeq] = useState<
    Record<number, RecalledFact[]>
  >({});

  const loadMessages = useCallback(async (sid: string) => {
    try {
      const res = await api.getMessages(sid);
      setMessages(res.messages);
      setLastError(null);
    } catch {
      // Failed to load messages
    }
  }, []);

  useEffect(() => {
    if (sessionId) {
      loadMessages(sessionId);
    } else {
      setMessages([]);
    }
  }, [sessionId, loadMessages]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setLastError(null);
    setRecalledBySeq({});
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!sessionId || pending) return;
      const trimmed = text.trim();
      if (!trimmed) return;

      setPending(true);
      setLastError(null);

      // Optimistically append user message
      const nextSeq =
        messages.length > 0
          ? Math.max(...messages.map((m) => m.seq)) + 1
          : 1;
      const userMsg: ChatMessage = {
        role: "user",
        text: trimmed,
        seq: nextSeq,
        ts: Date.now(),
      };

      setMessages((prev) => [...prev, userMsg]);

      try {
        const res = await api.sendChat(sessionId, trimmed);
        const assistantMsg: ChatMessage = {
          role: "assistant",
          text: res.reply,
          seq: nextSeq + 1,
          ts: Date.now(),
        };

        // Update messages with assistant reply and recalled facts
        setMessages((prev) => [...prev, assistantMsg]);
        if (res.recalled && res.recalled.length > 0) {
          setRecalledBySeq((prev) => ({
            ...prev,
            [nextSeq + 1]: res.recalled,
          }));
        }

        if (onRecalled) {
          onRecalled(res.recalled_fact_ids, res.matched_entity_ids);
        }
        if (onChatDone) {
          onChatDone();
        }
      } catch (err) {
        let msg = "An error occurred while sending your message.";
        let retryable = true;

        if (err instanceof ApiError) {
          if (err.status === 502) {
            msg = "The language model is unavailable. Try again in a moment.";
          } else if (err.status === 503) {
            msg = "Memory store unavailable. Check that FalkorDB is running.";
          } else if (err.status === 422) {
            msg = "Message not accepted.";
            retryable = false;
          } else if (err.status === 404) {
            msg = "Session lost. Please try sending again.";
            retryable = true;
          } else if (err.status === 0) {
            msg = "Can't reach the API. Please check your connection.";
          }
        }

        setLastError({
          message: msg,
          failedText: trimmed,
          isRetryable: retryable,
        });
      } finally {
        setPending(false);
      }
    },
    [sessionId, pending, messages, onRecalled, onChatDone]
  );

  const retryMessage = useCallback(async () => {
    if (!lastError || !lastError.failedText) return;
    const textToRetry = lastError.failedText;
    // Remove the last optimistic user message if present
    setMessages((prev) => {
      if (
        prev.length > 0 &&
        prev[prev.length - 1].role === "user" &&
        prev[prev.length - 1].text === textToRetry
      ) {
        return prev.slice(0, -1);
      }
      return prev;
    });
    setLastError(null);
    await sendMessage(textToRetry);
  }, [lastError, sendMessage]);

  return {
    messages,
    pending,
    lastError,
    recalledBySeq,
    sendMessage,
    retryMessage,
    clearMessages,
    loadMessages,
  };
}
