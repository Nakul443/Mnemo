// this file is responsible for defining the useSession hook
// that will be used to manage the session state in the frontend
// in simple words,
    // it handles the session ID, loading state, and error state for the application

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../api/client";

const SESSION_STORAGE_KEY = "mnemo.sessionId";

export interface UseSessionReturn {
  sessionId: string | null;
  loading: boolean;
  error: string | null;
  newSession: () => Promise<string | null>;
}

// this function defines a custom React hook called useSession
// that manages the session state for the application.
// It handles the session ID, loading state, and error state,
// and provides a function to create a new session when needed.
// The hook uses localStorage to persist the session ID across page reloads
// and attempts to restore the session on initialization.
// If the stored session is invalid or does not exist,
// it creates a new session and updates the state accordingly.
export function useSession(): UseSessionReturn {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const initSession = useCallback(async () => {
    setLoading(true);
    setError(null);
    const stored = localStorage.getItem(SESSION_STORAGE_KEY);

    if (stored) {
      try {
        await api.getMessages(stored);
        setSessionId(stored);
        setLoading(false);
        return;
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          // Stored session no longer exists in backend
          localStorage.removeItem(SESSION_STORAGE_KEY);
        } else {
          // Network or server error on session restore
          setError("Failed to restore session.");
          setSessionId(stored); // Keep ID locally
          setLoading(false);
          return;
        }
      }
    }

    // Create a new session if no valid stored session
    try {
      const res = await api.createSession();
      localStorage.setItem(SESSION_STORAGE_KEY, res.session_id);
      setSessionId(res.session_id);
    } catch {
      setError("Failed to create a new session.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    initSession();
  }, [initSession]);

  const newSession = useCallback(async (): Promise<string | null> => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.createSession();
      localStorage.setItem(SESSION_STORAGE_KEY, res.session_id);
      setSessionId(res.session_id);
      setLoading(false);
      return res.session_id;
    } catch {
      setError("Failed to create a new session.");
      setLoading(false);
      return null;
    }
  }, []);

  return { sessionId, loading, error, newSession };
}
