import { useCallback, useEffect, useRef } from "react";
import { logWarn } from "./logger";

type SerialPollingOptions = {
  enabled?: boolean;
  immediate?: boolean;
  onError?: (error: unknown) => void;
  restartKey?: string | number | boolean | null;
};

export type SerialPollingController = {
  runNow: () => Promise<void>;
  waitForIdle: () => Promise<void>;
};

const MIN_POLL_INTERVAL_MS = 50;

/**
 * Run asynchronous polling through one shared in-flight task.
 *
 * Effect restarts, StrictMode replays, timer ticks and explicit refreshes all
 * reuse the same promise. A restart waits for previous work to settle before
 * running the latest task, so old and new query scopes cannot overlap.
 */
export function useSerialPolling(
  task: () => Promise<void>,
  intervalMs: number,
  options: SerialPollingOptions = {},
): SerialPollingController {
  const taskRef = useRef(task);
  const errorRef = useRef(options.onError);
  const inFlightRef = useRef<Promise<void> | null>(null);
  taskRef.current = task;
  errorRef.current = options.onError;

  const enabled = options.enabled ?? true;
  const immediate = options.immediate ?? true;
  const restartKey = options.restartKey ?? null;
  const safeIntervalMs = Math.max(MIN_POLL_INTERVAL_MS, intervalMs);

  const waitForIdle = useCallback(async () => {
    const active = inFlightRef.current;
    if (active) await active;
  }, []);

  const runNow = useCallback((): Promise<void> => {
    const active = inFlightRef.current;
    if (active) return active;

    const current = Promise.resolve()
      .then(() => taskRef.current())
      .catch((error) => {
        try {
          if (errorRef.current) errorRef.current(error);
          else logWarn("polling", "Serial poll failed", { error });
        } catch (handlerError) {
          logWarn("polling", "Serial poll error handler failed", { error: handlerError });
        }
      })
      .finally(() => {
        if (inFlightRef.current === current) inFlightRef.current = null;
      });

    inFlightRef.current = current;
    return current;
  }, []);

  useEffect(() => {
    if (!enabled) return undefined;

    let cancelled = false;
    let timerId: number | undefined;

    const schedule = () => {
      if (!cancelled) {
        timerId = window.setTimeout(() => void runScheduled(), safeIntervalMs);
      }
    };

    async function runScheduled() {
      await runNow();
      schedule();
    }

    async function runImmediateLatest() {
      await waitForIdle();
      if (cancelled) return;
      await runNow();
      schedule();
    }

    if (immediate) void runImmediateLatest();
    else schedule();

    return () => {
      cancelled = true;
      if (timerId !== undefined) window.clearTimeout(timerId);
    };
  }, [enabled, immediate, restartKey, runNow, safeIntervalMs, waitForIdle]);

  return { runNow, waitForIdle };
}
