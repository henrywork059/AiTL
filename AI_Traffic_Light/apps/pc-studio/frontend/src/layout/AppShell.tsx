import type { ReactNode } from "react";
import { APP_SECTIONS, PAGE_DETAILS } from "../constants/appNavigation";
import type { AppPageId } from "../types/app";

type Props = {
  activePage: AppPageId;
  onPageChange: (page: AppPageId) => void;
  showSimulationTools: boolean;
  onSimulationToolsToggle: () => void;
  children: ReactNode;
};

export function AppShell({ activePage, onPageChange, showSimulationTools, onSimulationToolsToggle, children }: Props) {
  const page = PAGE_DETAILS[activePage];

  return (
    <div className="app-frame">
      <aside className="sidebar">
        <div className="brand-block">
          <h1>AI Traffic Light</h1>
          <button
            type="button"
            className="simulation-tools-toggle"
            aria-pressed={showSimulationTools}
            onClick={onSimulationToolsToggle}
          >
            Simulation tools
          </button>
        </div>

        <nav className="side-nav" aria-label="PC Studio pages">
          {APP_SECTIONS.map((section) => (
            <section key={section.id} className="nav-section">
              <h2>{section.label}</h2>
              {section.pages.filter((navPage) => showSimulationTools || navPage.id !== "simulation_lab").map((navPage) => (
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

      <div className="content-frame">
        <header className="page-header">
          <div className="section-intro">
            <h1>{page.label}</h1>
            <p>{page.description}</p>
          </div>

        </header>
        {children}
      </div>
    </div>
  );
}
