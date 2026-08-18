import type { ReactNode } from "react";
import { APP_SECTIONS, APP_VERSION_LABEL, PAGE_DETAILS } from "../constants/appNavigation";
import type { AppPageId } from "../types/app";

type Props = {
  activePage: AppPageId;
  onPageChange: (page: AppPageId) => void;
  children: ReactNode;
};

export function AppShell({ activePage, onPageChange, children }: Props) {
  const page = PAGE_DETAILS[activePage];

  return (
    <div className="app-frame">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="eyebrow">{APP_VERSION_LABEL}</div>
          <h1>AI Traffic Light</h1>
          <p>Simulation & vision workbench</p>
        </div>

        <nav className="side-nav" aria-label="PC Studio pages">
          {APP_SECTIONS.map((section) => (
            <section key={section.id} className="nav-section">
              <h2>{section.label}</h2>
              {section.pages.map((navPage) => (
                <button
                  key={navPage.id}
                  className={activePage === navPage.id ? "nav-button active" : "nav-button"}
                  onClick={() => onPageChange(navPage.id)}
                >
                  <span>{navPage.shortLabel}</span>
                  <small>{navPage.status}</small>
                </button>
              ))}
            </section>
          ))}
        </nav>
      </aside>

      <div className="content-frame">
        <header className="page-header">
          <div className="section-intro">
            <div className="eyebrow">{page.status}</div>
            <h1>{page.label}</h1>
            <p>{page.description}</p>
          </div>
          <span className="status-pill muted">Local simulation only</span>
        </header>
        {children}
      </div>
    </div>
  );
}
