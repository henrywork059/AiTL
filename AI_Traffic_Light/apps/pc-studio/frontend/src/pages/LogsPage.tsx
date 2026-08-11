import { FunctionChecklist } from "../components/FunctionChecklist";
import type { ApiConnectionState, RecentLog } from "../types";

type Props = {
  logs: RecentLog[];
  apiState: ApiConnectionState;
  onRefresh: () => void;
  refreshing: boolean;
};

export function LogsPage({ logs, apiState, onRefresh, refreshing }: Props) {
  return (
    <div className="page-stack">
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Recent mock logs</h2>
            <p className="placeholder-copy">API state: {apiState.message}</p>
          </div>
          <button onClick={onRefresh} disabled={refreshing}>{refreshing ? "Refreshing..." : "Refresh logs"}</button>
        </div>
        <div className="log-list">
          {logs.map((log) => (
            <article className="log-row" key={`${log.code}-${log.message}`}>
              <span className={`status-pill log-level-${log.level}`}>{log.level}</span>
              <code>{log.code}</code>
              <strong>{log.scope ?? "app"}</strong>
              <p>{log.message}</p>
            </article>
          ))}
        </div>
      </section>
      <FunctionChecklist area="Debug" />
    </div>
  );
}
