"use client";

import { useState } from "react";

import { isLanguage, labelsFor, persistLanguage, type Language, type LocalizedLabels } from "@/lib/i18n";
import type { RuntimeSetupValues } from "@/lib/startup-status";

type SetupWizardProps = {
  readonly onCompleted: () => void;
  readonly onCancel?: () => void;
  readonly language: Language;
  readonly labels: LocalizedLabels["setup"];
  readonly onLanguageChange: (language: Language) => void;
  readonly initialValues?: RuntimeSetupValues | null;
  readonly submitLabel?: string;
  readonly submittingLabel?: string;
  readonly cancelLabel?: string;
};

type SetupError = {
  readonly message: string;
};

const DEFAULT_DATA_DIRECTORY = "~/Library/Application Support/VBinvest";

export function SetupWizard({
  onCompleted,
  onCancel,
  language,
  labels: initialLabels,
  onLanguageChange,
  initialValues = null,
  submitLabel,
  submittingLabel,
  cancelLabel,
}: SetupWizardProps) {
  const [selectedLanguage, setSelectedLanguage] = useState(language);
  const labels = selectedLanguage === language ? initialLabels : labelsFor(selectedLanguage).setup;
  const [dataDirectory, setDataDirectory] = useState(initialValues?.dataDirectory ?? DEFAULT_DATA_DIRECTORY);
  const [databaseMode, setDatabaseMode] = useState(initialValues?.databaseMode ?? "sqlite");
  const [postgresUrl, setPostgresUrl] = useState(initialValues?.postgresUrl ?? "");
  const [vaultPath, setVaultPath] = useState(initialValues?.vaultPath ?? "");
  const [exportMode, setExportMode] = useState(initialValues?.exportMode ?? "direct");
  const [opendartKey, setOpendartKey] = useState(initialValues?.opendartKey ?? "");
  const [aiMode, setAiMode] = useState(initialValues?.aiMode ?? "none");
  const [aiApiType, setAiApiType] = useState(initialValues?.aiApiType ?? "cloud");
  const [aiProviderName, setAiProviderName] = useState(initialValues?.aiProviderName ?? "openai");
  const [aiBaseUrl, setAiBaseUrl] = useState(initialValues?.aiBaseUrl ?? "https://api.openai.com/v1");
  const [aiModel, setAiModel] = useState(initialValues?.aiModel ?? "");
  const [aiContextSize, setAiContextSize] = useState(initialValues?.aiContextSize ?? 8192);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<SetupError | null>(null);

  function selectLanguage(value: string) {
    if (!isLanguage(value)) {
      return;
    }
    setSelectedLanguage(value);
    persistLanguage(value);
    onLanguageChange(value);
  }

  async function submitSetup() {
    if (!vaultPath.trim() || submitting) {
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch("/api/settings/first-run", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({
          language: selectedLanguage,
          data_directory: dataDirectory,
          database: {
            mode: databaseMode,
            postgres_url: postgresUrl,
          },
          obsidian: {
            vault_path: vaultPath,
            export_mode: exportMode,
          },
          providers: {
            opendart_api_key: opendartKey,
            ai_mode: aiMode,
            ai_provider_name: aiMode === "openai_compatible" ? aiProviderName : "",
            ai_base_url: aiMode === "openai_compatible" ? aiBaseUrl : "",
            ai_model: aiMode === "openai_compatible" ? aiModel : "",
            ai_context_size: aiContextSize,
            ai_api_key: "",
          },
        }),
      });
      const payload: unknown = await readJson(response);
      if (!response.ok) {
        setError({ message: readDetail(payload) || labels.defaultErrorMessage });
        return;
      }
      onCompleted();
    } catch (caught) {
      if (caught instanceof Error) {
        setError({ message: caught.message });
        return;
      }
      setError({ message: labels.defaultErrorMessage });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="setup-wizard" aria-label="first run setup">
      <div className="setup-heading">
        <p className="eyebrow">VBinvest</p>
        <h1>{labels.title}</h1>
        <p className="subtle">{labels.setupInstruction}</p>
      </div>

      <label>
        <span>{labels.languageField}</span>
        <select
          value={selectedLanguage}
          aria-label={labels.languageField}
          onChange={(event) => selectLanguage(event.currentTarget.value)}
          onInput={(event) => selectLanguage(event.currentTarget.value)}
        >
          <option value="ko">{labels.languageOptionKo}</option>
          <option value="en">{labels.languageOptionEn}</option>
        </select>
      </label>

      <div className="setup-grid">
        <label>
          <span>{labels.dataDirectoryField}</span>
          <input aria-label={labels.dataDirectoryField} value={dataDirectory} onChange={(event) => setDataDirectory(event.target.value)} />
        </label>

        <label>
          <span>{labels.databaseModeField}</span>
          <select aria-label={labels.databaseModeField} value={databaseMode} onChange={(event) => setDatabaseMode(event.target.value)}>
            <option value="sqlite">{labels.databaseModeSqlite}</option>
            <option value="postgres_docker">{labels.databaseModePostgresDocker}</option>
            <option value="postgres_url">{labels.databaseModePostgresUrl}</option>
          </select>
        </label>

        {databaseMode === "postgres_docker" ? (
          <p className="setup-note">{labels.databaseModeDockerHint}</p>
        ) : null}

        {databaseMode === "postgres_url" ? (
          <label className="setup-wide">
            <span>{labels.postgresDsnField}</span>
            <input
              aria-label={labels.postgresDsnField}
              value={postgresUrl}
              onChange={(event) => setPostgresUrl(event.target.value)}
              placeholder={labels.postgresDsnPlaceholder}
            />
          </label>
        ) : null}

        <label className="setup-wide">
          <span>{labels.obsidianVaultField}</span>
          <input
            aria-label={labels.obsidianVaultField}
            value={vaultPath}
            onChange={(event) => setVaultPath(event.target.value)}
            placeholder={labels.obsidianVaultPlaceholder}
          />
        </label>

        <label>
          <span>{labels.exportModeField}</span>
          <select aria-label={labels.exportModeField} value={exportMode} onChange={(event) => setExportMode(event.target.value)}>
            <option value="direct">{labels.exportModeDirect}</option>
            <option value="symlink">{labels.exportModeSymlink}</option>
          </select>
        </label>

        <label>
          <span>{labels.opendartApiKeyField}</span>
          <input
            aria-label={labels.opendartApiKeyField}
            value={opendartKey}
            onChange={(event) => setOpendartKey(event.target.value)}
            placeholder={labels.opendartApiKeyHint}
          />
        </label>

        <p className="setup-note">
          {labels.opendartApiKeyHint}
        </p>

        <label>
          <span>{labels.aiModeField}</span>
          <select aria-label={labels.aiModeField} value={aiMode} onChange={(event) => setAiMode(event.target.value)}>
            <option value="none">{labels.aiModeNone}</option>
            <option value="openai_compatible">{labels.aiModeCompatible}</option>
            <option value="codex_cli">{labels.aiModeCodex}</option>
            <option value="copilot_cli">{labels.aiModeCopilot}</option>
          </select>
        </label>

        {aiMode === "openai_compatible" ? (
          <>
            <label>
              <span>{labels.aiTypeField}</span>
              <select aria-label={labels.aiTypeField} value={aiApiType} onChange={(event) => setAiApiType(event.target.value)}>
                <option value="cloud">{labels.aiTypeCloud}</option>
                <option value="local">{labels.aiTypeLocal}</option>
              </select>
            </label>

            {aiApiType === "cloud" ? (
              <label>
                <span>{labels.cloudProviderField}</span>
                <select
                  aria-label={labels.cloudProviderField}
                  value={aiProviderName}
                  onChange={(event) => setAiProviderName(event.target.value)}
                >
                  <option value="openai">{labels.cloudProviderOpenai}</option>
                  <option value="openrouter">{labels.cloudProviderOpenrouter}</option>
                  <option value="deepseek">{labels.cloudProviderDeepseek}</option>
                  <option value="qwen_dashscope">{labels.cloudProviderQwen}</option>
                  <option value="kimi_moonshot">{labels.cloudProviderKimi}</option>
                  <option value="glm_zai">{labels.cloudProviderGlm}</option>
                  <option value="custom">{labels.cloudProviderCustom}</option>
                </select>
              </label>
            ) : (
              <p className="setup-note">{labels.localProviderHint}</p>
            )}

            <label className="setup-wide">
              <span>{labels.aiBaseUrlField}</span>
              <input
                aria-label={labels.aiBaseUrlField}
                value={aiBaseUrl}
                onChange={(event) => setAiBaseUrl(event.target.value)}
                placeholder={labels.aiBaseUrlPlaceholder}
              />
            </label>

            <label>
              <span>{labels.aiModelField}</span>
              <input
                aria-label={labels.aiModelField}
                value={aiModel}
                onChange={(event) => setAiModel(event.target.value)}
                placeholder={labels.aiModelPlaceholder}
              />
            </label>

            <label>
              <span>{labels.aiContextSizeField}</span>
              <input
                aria-label={labels.aiContextSizeField}
                type="number"
                min={1024}
                max={262144}
                value={aiContextSize}
                onChange={(event) => setAiContextSize(Number(event.target.value))}
              />
            </label>
          </>
        ) : null}
      </div>

      {error ? <p className="research-status error">{error.message}</p> : null}

      <div className="setup-actions">
        <button type="button" onClick={() => void submitSetup()} disabled={!vaultPath.trim() || submitting}>
          {submitting ? submittingLabel ?? labels.completeButtonSaving : submitLabel ?? labels.completeButton}
        </button>
        {onCancel ? (
          <button type="button" onClick={onCancel} disabled={submitting}>
            {cancelLabel ?? "Cancel"}
          </button>
        ) : null}
      </div>
    </section>
  );
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch (caught) {
    if (caught instanceof SyntaxError) {
      return null;
    }
    throw caught;
  }
}

function readDetail(payload: unknown): string {
  if (!isRecord(payload)) {
    return "";
  }
  const detail = payload.detail;
  return typeof detail === "string" ? detail : "";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function authHeaders(): Record<string, string> {
  const token = localSessionToken();
  if (!token) {
    return {};
  }
  return { Authorization: `Bearer ${token}` };
}

function localSessionToken(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return window.__VBINVEST_LOCAL_SESSION_TOKEN__ ?? "";
}

declare global {
  interface Window {
    __VBINVEST_LOCAL_SESSION_TOKEN__?: string;
  }
}
