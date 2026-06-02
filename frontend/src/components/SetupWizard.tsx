"use client";

import { useState } from "react";

type SetupWizardProps = {
  readonly onCompleted: () => void;
};

type SetupError = {
  readonly message: string;
};

const DEFAULT_DATA_DIRECTORY = "~/Library/Application Support/VBinvest";

export function SetupWizard({ onCompleted }: SetupWizardProps) {
  const [dataDirectory, setDataDirectory] = useState(DEFAULT_DATA_DIRECTORY);
  const [databaseMode, setDatabaseMode] = useState("sqlite");
  const [postgresUrl, setPostgresUrl] = useState("");
  const [vaultPath, setVaultPath] = useState("");
  const [exportMode, setExportMode] = useState("direct");
  const [opendartKey, setOpendartKey] = useState("");
  const [aiMode, setAiMode] = useState("none");
  const [aiApiType, setAiApiType] = useState("cloud");
  const [aiProviderName, setAiProviderName] = useState("openai");
  const [aiBaseUrl, setAiBaseUrl] = useState("https://api.openai.com/v1");
  const [aiModel, setAiModel] = useState("");
  const [aiContextSize, setAiContextSize] = useState(8192);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<SetupError | null>(null);

  async function submitSetup() {
    if (!vaultPath.trim() || submitting) {
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch("/api/settings/first-run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          language: "ko",
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
        setError({ message: readDetail(payload) || "설정 저장에 실패했습니다." });
        return;
      }
      onCompleted();
    } catch (caught) {
      if (caught instanceof Error) {
        setError({ message: caught.message });
        return;
      }
      setError({ message: "설정 저장에 실패했습니다." });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="setup-wizard" aria-label="first run setup">
      <div className="setup-heading">
        <p className="eyebrow">VBinvest</p>
        <h1>초기 설정</h1>
        <p className="subtle">로컬 데이터와 Obsidian 저장 위치를 정하면 대시보드가 시작됩니다.</p>
      </div>

      <div className="setup-grid">
        <label>
          <span>Data Directory</span>
          <input aria-label="Data Directory" value={dataDirectory} onChange={(event) => setDataDirectory(event.target.value)} />
        </label>

        <label>
          <span>Database Mode</span>
          <select aria-label="Database Mode" value={databaseMode} onChange={(event) => setDatabaseMode(event.target.value)}>
            <option value="sqlite">SQLite 내장 DB (권장)</option>
            <option value="postgres_docker">PostgreSQL Docker 자동 실행</option>
            <option value="postgres_url">PostgreSQL 직접 연결</option>
          </select>
        </label>

        {databaseMode === "postgres_docker" ? (
          <p className="setup-note">Docker Desktop/Engine이 필요합니다. 없으면 설치 후 다시 시도하세요.</p>
        ) : null}

        {databaseMode === "postgres_url" ? (
          <label className="setup-wide">
            <span>Postgres DSN</span>
            <input aria-label="Postgres DSN" value={postgresUrl} onChange={(event) => setPostgresUrl(event.target.value)} placeholder="postgresql://user:password@127.0.0.1:5432/vbinvest" />
          </label>
        ) : null}

        <label className="setup-wide">
          <span>Obsidian Vault Path</span>
          <input aria-label="Obsidian Vault Path" value={vaultPath} onChange={(event) => setVaultPath(event.target.value)} placeholder="/Volumes/.../ObsidianVault" />
        </label>

        <label>
          <span>Export Mode</span>
          <select aria-label="Export Mode" value={exportMode} onChange={(event) => setExportMode(event.target.value)}>
            <option value="direct">직접 저장</option>
            <option value="symlink">심링크 (고급)</option>
          </select>
        </label>

        <label>
          <span>OpenDART API Key</span>
          <input aria-label="OpenDART API Key" value={opendartKey} onChange={(event) => setOpendartKey(event.target.value)} placeholder="선택 사항" />
        </label>

        <p className="setup-note">
          OpenDART 공시를 받으려면 OpenDART에서 API 키를 발급해 입력하세요. 사용량과 제한은 사용자 키 책임이며, 비워두면 한국 공시 수집만 비활성화됩니다.
        </p>

        <label>
          <span>AI Mode</span>
          <select aria-label="AI Mode" value={aiMode} onChange={(event) => setAiMode(event.target.value)}>
            <option value="none">사용 안 함</option>
            <option value="openai_compatible">AI API 연동</option>
            <option value="codex_cli">Codex CLI (계정 제한/정지 가능성 있음)</option>
            <option value="copilot_cli">Copilot CLI (계정 제한/정지 가능성 있음)</option>
          </select>
        </label>

        {aiMode === "openai_compatible" ? (
          <>
            <label>
              <span>AI API Type</span>
              <select aria-label="AI API Type" value={aiApiType} onChange={(event) => setAiApiType(event.target.value)}>
                <option value="cloud">Cloud model provider</option>
                <option value="local">Local LLM</option>
              </select>
            </label>

            {aiApiType === "cloud" ? (
              <label>
                <span>Cloud Model Provider</span>
                <select aria-label="Cloud Model Provider" value={aiProviderName} onChange={(event) => setAiProviderName(event.target.value)}>
                  <option value="openai">OpenAI</option>
                  <option value="openrouter">OpenRouter</option>
                  <option value="deepseek">DeepSeek</option>
                  <option value="qwen_dashscope">Qwen / DashScope</option>
                  <option value="kimi_moonshot">Kimi / Moonshot</option>
                  <option value="glm_zai">GLM / Z.AI</option>
                  <option value="custom">Custom provider</option>
                </select>
              </label>
            ) : (
              <p className="setup-note">Ollama, LM Studio, llama.cpp 같은 로컬 OpenAI-compatible endpoint를 사용할 수 있습니다.</p>
            )}

            <label className="setup-wide">
              <span>AI Base URL</span>
              <input aria-label="AI Base URL" value={aiBaseUrl} onChange={(event) => setAiBaseUrl(event.target.value)} placeholder="https://api.openai.com/v1" />
            </label>

            <label>
              <span>AI Model</span>
              <input aria-label="AI Model" value={aiModel} onChange={(event) => setAiModel(event.target.value)} placeholder="gpt-4.1-mini" />
            </label>

            <label>
              <span>Context Size</span>
              <input aria-label="Context Size" type="number" min={1024} max={262144} value={aiContextSize} onChange={(event) => setAiContextSize(Number(event.target.value))} />
            </label>
          </>
        ) : null}
      </div>

      {error ? <p className="research-status error">{error.message}</p> : null}

      <div className="setup-actions">
        <button type="button" onClick={() => void submitSetup()} disabled={!vaultPath.trim() || submitting}>
          {submitting ? "저장 중" : "설정 완료"}
        </button>
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
