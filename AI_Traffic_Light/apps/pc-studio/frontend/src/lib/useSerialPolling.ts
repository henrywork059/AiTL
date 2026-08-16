import { useEffect, useRef } from "react";
import { logWarn } from "./logger";

type SerialPollingOptions = {
  enabled?: boolean;
  immediate?: boolean;
  onError?: (error: unknown) => void;
};

const MIN_POLL_INTERVAL_MS = 50;

/**
 * Run an asynchronous poll serially.
 *
 * The next timeout is scheduled only after the current task settles, so slow
 * requests cannot accumulate overlapping fetches. Callback refs keep the
 * interval stable when callers recreate task/error handlers during rendering.
 */
export function useSerialPolling(
  task: () => Promise<void>,
  intervalMs: number,
  options: SerialPollingOptions = {},
) {
  const taskRef = useRef(task);
  const errorRef = useRef(options.onError);
  taskRef.current = task;
  errorRef.current = options.onError;

  const enabled = options.enabled ?? true;
  const immediate = options.immediate ?? true;
  const safeIntervalMs = Math.max(MIN_POLL_INTERVAL_MS, intervalMs);

  useEffect(() => {
    if (!enabled) return undefined;

    let cancelled = false;
    let timerId: number | undefined;

    const schedule = () => {
      if (!cancelled) {
        timerId = window.setTimeout(() => void run(), safeIntervalMs);
      }
    };

    async function run() {
      try {
        await taskRef.current();
      } catch (error) {
        if (errorRef.current) errorRef.current(error);
        else logWarn("polling", "Serial poll failed", { error });
      } finally {
        schedule();
      }
    }

    if (immediate) void run();
    else schedule();

    return () => {
      cancelled = true;
      if (timerId !== undefined) window.clearTimeout(timerId);
    };
  }, [enabled, immediate, safeIntervalMs]);
}
