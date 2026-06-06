import { useEffect, useRef, useState } from "react";
import { getJobResult } from "../api/client";
import type { JobResult, JobStatus } from "../types/api";

const TERMINAL: JobStatus[] = ["done", "error"];
const DEFAULT_INTERVAL_MS = 1500;

export function useJobPolling(jobId: string | null, intervalMs = DEFAULT_INTERVAL_MS) {
  const [result, setResult] = useState<JobResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!jobId) return;

    const poll = async () => {
      try {
        const data = await getJobResult(jobId);
        setResult(data);
        if (TERMINAL.includes(data.status)) {
          clearInterval(timerRef.current!);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error desconocido");
        clearInterval(timerRef.current!);
      }
    };

    poll();
    timerRef.current = setInterval(poll, intervalMs);

    return () => clearInterval(timerRef.current!);
  }, [jobId, intervalMs]);

  return { result, error };
}
