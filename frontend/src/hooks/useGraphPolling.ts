// this file is responsible for defining the useGraphPolling hook
// that will be used to manage the graph polling state in the frontend
// in simple words,
    // it handles the graph snapshot, pending extraction count, connection status,
    // and provides functions to refresh the graph and enter fast polling mode

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { GraphSnapshot } from "../api/types";

const FAST_INTERVAL_MS = 700;
const NORMAL_INTERVAL_MS = 2000;
const FAST_MODE_DURATION_MS = 15000;
const ERROR_BACKOFF_MS = 5000;

export interface UseGraphPollingReturn {
  graph: GraphSnapshot | null;
  pendingCount: number;
  connected: boolean;
  refreshNow: () => void;
  enterFastMode: () => void;
}

export function useGraphPolling(): UseGraphPollingReturn {
  const [graph, setGraph] = useState<GraphSnapshot | null>(null);
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [connected, setConnected] = useState<boolean>(true);

  const fastUntilRef = useRef<number>(0);
  const consecutiveZeroPendingRef = useRef<number>(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const enterFastMode = useCallback(() => {
    fastUntilRef.current = Date.now() + FAST_MODE_DURATION_MS;
    consecutiveZeroPendingRef.current = 0;
  }, []);

  const fetchGraph = useCallback(async () => {
    if (document.visibilityState === "hidden") {
      // Pause polling while tab is hidden
      return;
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const snapshot = await api.getGraph();
      setGraph(snapshot);
      setConnected(true);
      setPendingCount(snapshot.extraction_pending);

      if (snapshot.extraction_pending === 0) {
        consecutiveZeroPendingRef.current += 1;
      } else {
        consecutiveZeroPendingRef.current = 0;
      }
    } catch {
      setConnected(false);
    }
  }, []);

  const scheduleNext = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }

    let interval = NORMAL_INTERVAL_MS;

    if (!connected) {
      interval = ERROR_BACKOFF_MS;
    } else {
      const isFastTime = Date.now() < fastUntilRef.current;
      const isPending = pendingCount > 0;
      const isDraining = consecutiveZeroPendingRef.current < 2;

      if (isPending || (isFastTime && isDraining)) {
        interval = FAST_INTERVAL_MS;
      }
    }

    timerRef.current = setTimeout(async () => {
      await fetchGraph();
      scheduleNext();
    }, interval);
  }, [connected, pendingCount, fetchGraph]);

  const refreshNow = useCallback(() => {
    fetchGraph().then(() => {
      scheduleNext();
    });
  }, [fetchGraph, scheduleNext]);

  useEffect(() => {
    // Initial fetch
    fetchGraph().then(() => {
      scheduleNext();
    });

    const handleVisibility = () => {
      if (document.visibilityState === "visible") {
        fetchGraph().then(() => {
          scheduleNext();
        });
      }
    };

    document.addEventListener("visibilitychange", handleVisibility);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      if (abortControllerRef.current) abortControllerRef.current.abort();
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [fetchGraph, scheduleNext]);

  return {
    graph,
    pendingCount,
    connected,
    refreshNow,
    enterFastMode,
  };
}
