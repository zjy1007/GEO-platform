"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, GeoRunProgress, TERMINAL_RUN_STATUSES } from "@/lib/api";

const POLL_MS = 2000;

export function isTerminal(status?: string | null): boolean {
  return !!status && TERMINAL_RUN_STATUSES.includes(status);
}

// Derive a 0..100 percent from a progress snapshot. Prefers finished/total,
// falls back to the server-provided progress fraction.
export function progressPercent(p?: GeoRunProgress | null): number {
  if (!p) return 0;
  if (p.total_jobs > 0) {
    return Math.round((p.finished_jobs / p.total_jobs) * 100);
  }
  return Math.round((p.progress ?? 0) * 100);
}

export interface UseRunProgressResult {
  progress: GeoRunProgress | null;
  setProgress: (p: GeoRunProgress | null) => void;
  terminal: boolean;
  percent: number;
  error: string | null;
  setError: (e: string | null) => void;
  // Begin polling getGeoRun for the given run until a terminal status.
  // onTerminal fires once when the run reaches a terminal state.
  startPolling: (runId: string, onTerminal?: () => void | Promise<void>) => void;
  clearPoll: () => void;
}

/**
 * Shared geo-run polling logic, extracted from EvalSection so multiple
 * surfaces (inline section, progress drawer) can reuse the same loop without
 * duplicating interval / terminal-detection code.
 */
export function useRunProgress(): UseRunProgressResult {
  const [progress, setProgress] = useState<GeoRunProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearPoll = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => clearPoll, [clearPoll]);

  const startPolling = useCallback(
    (runId: string, onTerminal?: () => void | Promise<void>) => {
      clearPoll();
      pollRef.current = setInterval(async () => {
        try {
          const p = await api.getGeoRun(runId);
          setProgress(p);
          if (isTerminal(p.status)) {
            clearPoll();
            if (onTerminal) await onTerminal();
          }
        } catch (e) {
          clearPoll();
          if (e instanceof ApiError) setError(e.message);
        }
      }, POLL_MS);
    },
    [clearPoll]
  );

  return {
    progress,
    setProgress,
    terminal: isTerminal(progress?.status),
    percent: progressPercent(progress),
    error,
    setError,
    startPolling,
    clearPoll,
  };
}
