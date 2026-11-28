import { useEffect, useRef, useState } from "react";
import { DEMO_SCENARIOS, runFakeJunctionDemo, type DemoScenario, type FakeDemoReport } from "../lib/fakeDemoApi";

const LABELS: Record<DemoScenario, string> = {
  nominal: "Nominal lease and expiry", missing_ack: "Missing acknowledgment",
  rejected_ack: "Rejected acknowledgment", wrong_ack: "Wrong acknowledgment ID",
  late_ack: "Late acknowledgment", disconnect: "Disconnect", manual_stop: "Explicit stop",
};

export function FakeJunctionDemoPage() {
  const [scenario, setScenario] = useState<DemoScenario>("nominal");
  const [authorized, setAuthorized] = useState(false);
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState<FakeDemoReport | null>(null);
  const [download, setDownload] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const active = useRef<AbortController | null>(null);
  useEffect(() => () => active.current?.abort(), []);
  useEffect(() => () => { if (download) URL.revokeObjectURL(download); }, [download]);

  async function run() {
    if (active.current) return;
    const controller = new AbortController();
    active.current = controller;
    setBusy(true); setError(null); setReport(null); setDownload(null);
    try {
      const result = await runFakeJunctionDemo(scenario, authorized, controller.signal);
      if (controller.signal.aborted) return;
      setReport(result);
      setDownload(URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], { type: "application/json" })));
    } catch (reason) {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "Synthetic demonstration unavailable.");
    } finally {
      if (active.current === controller) active.current = null;
      if (!controller.signal.aborted) setBusy(false);
    }
  }

  const checks = report ? Object.entries(report.checks) : [];
  return <section className="panel page-stack">
    <div className="panel-header"><div><h2>Simulated junction demonstration</h2>
      <p className="placeholder-copy">Execute isolated fake lighting and speaker leases, with virtual time and no connection to cameras, live traffic signals or physical devices. No sound is played.</p></div>
      <span className="status-pill muted">Simulation only</span></div>
    <div className="form-grid">
      <label>Scenario<select aria-label="Demo scenario" value={scenario} disabled={busy} onChange={e=>setScenario(e.target.value as DemoScenario)}>
        {DEMO_SCENARIOS.map(key=><option key={key} value={key}>{LABELS[key]}</option>)}
      </select></label>
      <label><input aria-label="Authorize fake leases" type="checkbox" checked={authorized} disabled={busy} onChange={e=>setAuthorized(e.target.checked)}/> Authorize fake leases for this run only</label>
    </div>
    <div className="button-row">
      <button type="button" className="primary" disabled={busy} onClick={()=>void run()}>{busy?"Running...":"Run synthetic demo"}</button>
      {report&&download&&<a href={download} download={`mesh-fake-demo-${report.scenario}.json`}>Download demo JSON</a>}
    </div>
    {error&&<p className="error-message" role="alert">{error}</p>}
    {report&&<>
      <p role="status"><strong>{checks.filter(([,passed])=>passed).length}/{checks.length} synthetic checks passed</strong> · {LABELS[report.scenario]} · {report.authorization_requested?"fake authorization granted":"authorization denied"} · virtual time</p>
      <div className="experiment-table-scroll"><table className="experiment-table">
        <thead><tr><th>Virtual ms</th><th>Event</th><th>Lighting</th><th>Speaker metadata</th></tr></thead>
        <tbody>{report.trace.map((row,i)=><tr key={i}><td>{row.time_ms}</td><td>{row.event.replaceAll("_"," ")}</td>
          <td>{row.lighting.active?"active":"off"} · {row.lighting.reason}</td>
          <td>{row.speaker.active?"active":"off"} · {row.speaker.reason}</td></tr>)}</tbody>
      </table></div>
      <details><summary>Detailed synthetic checks</summary>{checks.map(([key,passed])=><p key={key}>{key.replaceAll("_"," ")}: {passed?"PASS":"FAIL"}</p>)}</details>
      <p className="small-note">Physical output unavailable. This report is not hardware or road-safety qualification.</p>
    </>}
  </section>;
}
