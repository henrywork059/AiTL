/** Ownership of one experiment operation; retired responses cannot publish. */
export function createExperimentOperationGate() {
  let active: symbol | null = null;
  return {
    begin() {
      if (active !== null) return null;
      const token = Symbol("experiment-operation");
      active = token;
      return {
        isCurrent: () => active === token,
        finish: () => { if (active === token) active = null; },
      };
    },
    retire() { active = null; },
  };
}

export function chooseStoredRunId(runs: readonly { run_id: string }[], preferred?: string): string {
  return preferred === undefined ? (runs[0]?.run_id ?? "")
    : runs.some(run => run.run_id === preferred) ? preferred : "";
}

export function verifiedExperimentResult<T extends { run_id: string }>(id: string, result: T | null): T | null {
  return id && result?.run_id === id ? result : null;
}
