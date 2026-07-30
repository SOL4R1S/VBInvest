import { SetupWizard } from "@/components/SetupWizard";
import type { RuntimeSetupValues } from "@/lib/startup-status";
import type { Language, LocalizedLabels } from "@/lib/i18n";

type SettingsModalProps = {
  readonly onCompleted: () => void;
  readonly onClose: () => void;
  readonly language: Language;
  readonly labels: LocalizedLabels;
  readonly onLanguageChange: (language: Language) => void;
  readonly initialValues: RuntimeSetupValues | null;
};

export function SettingsModal({ onCompleted, onClose, language, labels, onLanguageChange, initialValues }: SettingsModalProps) {
  return (
    <div className="settings-modal-backdrop" onKeyDown={(event) => { if (event.key === "Escape") onClose(); }}>
      <div className="settings-modal" role="dialog" aria-modal="true" aria-label={labels.controls.settingsAction}>
        <SetupWizard
          onCompleted={onCompleted}
          onCancel={onClose}
          language={language}
          labels={labels.setup}
          onLanguageChange={onLanguageChange}
          initialValues={initialValues}
          submitLabel={labels.controls.settingsSaveAction}
          cancelLabel={labels.controls.settingsCancelAction}
        />
      </div>
    </div>
  );
}
