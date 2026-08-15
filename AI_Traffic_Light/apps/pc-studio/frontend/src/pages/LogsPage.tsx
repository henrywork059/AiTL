import { useEffect, useState } from "react";
import { fetchRecentLogs } from "../api";
import { FunctionChecklist } from "../components/FunctionChecklist";
import type { ApiConnectionState, RecentLog } from "../types";

type Props = {
  logs: RecentLog[];
  apiState: ApiConnectionState;
  onLogsChange: (logs: RecentLog[]) => void;
};

export function LogsPage({ logs, apiState, onLogsChange }: Props) {
  const [refreshing, setRefreshing] = useState(false);

  async function refresh() {
    setRefreshing(true);
    try {
      onLogsChange(await fetchRecentLogs(100));
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 3000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="page-stack">
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Recent backend logs</h2>
            <p className="placeholder-copy">Actual bounded in-memory backend log records. API state: {apiState.message}</p>
          </div>
          <button onClick={() => void refresh()} disabled={refreshing}>{refreshing ? "Refreshing..." : "Refresh logs"}</button>
        </div>
        <div className="log-list">
          {logs.length === 0 ? <p className="placeholder-copy">No backend log records have been captured yet.</p> : logs.map((log, index) => (
            <article className="log-row" key={`${log.timestamp}-${log.code}-${index}`}>
              <span className={`status-pill log-level-${log.level}`}>{log.level}</span>
              <code>{log.code}</code>
              <strong>{log.scope ?? "app"}</strong>
              <div>
                <p>{log.message}</p>
                <span className="small-note">{log.timestamp ?? "unknown time"}{log.request_id ? ` · ${log.request_id}` : ""}</span>
              </div>
            </article>
          ))}
        </div>
      </section>
      <FunctionChecklist area="Debug" />
    </div>
  );
}
