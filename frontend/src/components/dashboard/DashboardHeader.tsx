import { NotificationBell } from "@/components/notifications/NotificationBell";
import type { Language, LocalizedLabels } from "@/lib/i18n";
import { isLanguage } from "@/lib/i18n";

type DashboardHeaderProps = {
  readonly labels: LocalizedLabels;
  readonly language: Language;
  readonly onLanguageChange: (language: Language) => void;
  readonly onSettingsOpen: () => void;
  readonly onShutdown: () => void;
  readonly systemShuttingDown: boolean;
  readonly systemShutdownComplete: boolean;
  readonly systemShutdownMessage: string | null;
};

export function DashboardHeader({
  labels,
  language,
  onLanguageChange,
  onSettingsOpen,
  onShutdown,
  systemShuttingDown,
  systemShutdownComplete,
  systemShutdownMessage,
}: DashboardHeaderProps) {
  return (
    <header className="hero">
      <div>
        <p className="eyebrow">{labels.app.title}</p>
        <h1>{labels.app.dashboardHeading}</h1>
        <p className="subtle">{labels.app.dashboardSubtitle}</p>
      </div>
      <div className="hero-actions" aria-label="application actions">
        <div className="hero-action-row">
          <NotificationBell />
          <button type="button" className="hero-action-button" onClick={onSettingsOpen}>
            {labels.controls.settingsAction}
          </button>
          <button
            type="button"
            className="hero-action-button shutdown"
            onClick={onShutdown}
            disabled={systemShuttingDown || systemShutdownComplete}
          >
            {labels.controls.shutdownAction}
          </button>
        </div>
        {systemShutdownMessage ? (
          <p className={`hero-action-status ${systemShutdownComplete ? "success" : systemShuttingDown ? "" : "error"}`}>
            {systemShutdownMessage}
          </p>
        ) : null}
        <label>
          <span className="sr-only">{labels.app.languageLabel}</span>
          <select
            value={language}
            aria-label={labels.app.languageLabel}
            onChange={(event) => {
              if (isLanguage(event.target.value)) {
                onLanguageChange(event.target.value);
              }
            }}
          >
            <option value="ko">{labels.app.languageOptionKo}</option>
            <option value="en">{labels.app.languageOptionEn}</option>
          </select>
        </label>
      </div>
    </header>
  );
}
