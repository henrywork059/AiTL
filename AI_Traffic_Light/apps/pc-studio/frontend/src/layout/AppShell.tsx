import type { ReactNode } from "react";
import { APP_VERSION_LABEL, PAGE_DETAILS, visibleSections } from "../constants/appNavigation";
import type { ApiConnectionState, CameraStatus } from "../types";
import type { AppPageId } from "../types/app";

type Props = {
  activePage: AppPageId;
  onPageChange: (page: AppPageId) => void;
  showSimulationTools: boolean;
  onSimulationToolsToggle: () => void;
  apiState: ApiConnectionState;
  cameraStatus: CameraStatus | null;
  children: ReactNode;
};

export function AppShell({ activePage, onPageChange, showSimulationTools, onSimulationToolsToggle, apiState, cameraStatus, children }: Props) {
  const page = PAGE_DETAILS[activePage];
  const sections = visibleSections(showSimulationTools);
  const mode = apiState.status !== "connected" || !cameraStatus ? "Source unknown" : cameraStatus.simulation_enabled ? (cameraStatus.simulation_paused ? "Simulation paused" : "Simulation") : "Receiver mode";

  return (
    <div className="app-frame">
      <a className="workspace-skip-link" href="#workspace-content">Skip to workspace</a>
      <aside className="sidebar">
        <div className="brand-block">
          <h1>M.E.S.H.</h1>
          <button
            type="button"
            className="simulation-tools-toggle"
            aria-pressed={showSimulationTools}
            onClick={onSimulationToolsToggle}
          >
            Simulation tools
          </button>
        </div>

        <label className="workspace-mobile-picker">Workspace
          <select value={sections.some(section => section.pages.some(item => item.id === activePage)) ? activePage : ""} onChange={event => onPageChange(event.target.value as AppPageId)}>
            {!sections.some(section => section.pages.some(item => item.id === activePage)) && <option value="" disabled>{page.label}</option>}
            {sections.map(section => <optgroup key={section.id} label={section.label}>{section.pages.map(item => <option key={item.id} value={item.id}>{item.shortLabel}</option>)}</optgroup>)}
          </select>
        </label>
        <nav className="side-nav" aria-label="PC Studio pages">
          {sections.map((section) => (
            <section key={section.id} className="nav-section">
              <h2>{section.label}</h2>
              {section.pages.map((navPage) => (
                <button
                  key={navPage.id}
                  className={activePage === navPage.id ? "nav-button active" : "nav-button"}
                  aria-current={activePage === navPage.id ? "page" : undefined}
                  onClick={() => onPageChange(navPage.id)}
                >
                  <span>{navPage.shortLabel}</span>
                  {navPage.status === "planned" && <small>planned</small>}
                </button>
              ))}
            </section>
          ))}
        </nav>
      </aside>

      <main className="content-frame" id="workspace-content" tabIndex={-1}>
        <header className="page-header">
          <div className="section-intro">
            <h1>{page.label}</h1>
            <p>{page.description}</p>
          </div>

          <div className="workspace-context" aria-label="Last reported system context"><span>API: {apiState.status}</span><span>{mode}</span><span>{APP_VERSION_LABEL}</span></div>
        </header>
        {children}
      </main>
    </div>
  );
}
