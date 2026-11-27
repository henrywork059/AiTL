/** A committed polling scope owns its cancellation and all result publication. */
export type PollingContext = {
  signal: AbortSignal;
  isCurrent: () => boolean;
};

export function createPollingScope(): PollingContext & { retire: () => void } {
  const controller = new AbortController();
  return {
    signal: controller.signal,
    isCurrent: () => !controller.signal.aborted,
    retire: () => controller.abort(),
  };
}

export type InFlightRef = { current: Promise<void> | null };

/** Reuse the same promise until the underlying task settles, even after abort. */
export function runScopedSerialTask(
  inFlight: InFlightRef,
  scope: PollingContext,
  task: (context: PollingContext) => Promise<void>,
  onError: (error: unknown) => void,
): Promise<void> {
  if (inFlight.current) return inFlight.current;
  const current = Promise.resolve()
    .then(() => scope.isCurrent() ? task(scope) : undefined)
    .catch((error) => {
      if (scope.isCurrent()) onError(error);
    })
    .finally(() => {
      if (inFlight.current === current) inFlight.current = null;
    });
  inFlight.current = current;
  return current;
}
