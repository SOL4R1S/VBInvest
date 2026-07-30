import type { LocalizedLabels } from "@/lib/i18n";

const ESTIMATED_STARTUP_REFRESH_SECONDS = 120;
const STARTUP_PROGRESS_CAP = 92;

export function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return minutes > 0 ? `${minutes}m ${remainder}s` : `${remainder}s`;
}

export function estimatedStartupProgress(elapsedSeconds: number): { percent: number; remainingSeconds: number } {
  const rawPercent = Math.floor((elapsedSeconds / ESTIMATED_STARTUP_REFRESH_SECONDS) * 100);
  const percent = Math.max(5, Math.min(STARTUP_PROGRESS_CAP, rawPercent));
  const remainingSeconds = Math.max(0, ESTIMATED_STARTUP_REFRESH_SECONDS - elapsedSeconds);
  return { percent, remainingSeconds };
}

type StartupProgressModalProps = {
  readonly percent: number;
  readonly remainingSeconds: number;
  readonly elapsedSeconds: number;
  readonly labels: LocalizedLabels["startup"];
};

export function StartupProgressModal({ percent, remainingSeconds, elapsedSeconds, labels }: StartupProgressModalProps) {
  return (
    <div className="startup-refresh-modal" role="status" aria-live="polite">
      <strong>{labels.checkingText}</strong>
      <div className="startup-refresh-progress" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100} aria-label={labels.progressLabel}>
        <span style={{ width: `${percent}%` }} />
      </div>
      <div className="startup-refresh-progress-copy">
        <span>{labels.progressLabel} {percent}%</span>
        <span>{labels.elapsedLabel} {formatDuration(elapsedSeconds)}</span>
        <span>{labels.remainingLabel} {formatDuration(remainingSeconds)}</span>
      </div>
      <small>{labels.progressEstimateNotice}</small>
    </div>
  );
}
