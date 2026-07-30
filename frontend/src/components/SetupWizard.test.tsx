import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SetupWizard } from "./SetupWizard";
import { labelFor } from "@/lib/i18n";

const labels = labelFor("ko").setup;

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const defaultProps = {
  onCompleted: vi.fn(),
  language: "ko" as const,
  labels,
  onLanguageChange: vi.fn(),
};

describe("SetupWizard", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    vi.clearAllMocks();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders title and form fields", () => {
    render(<SetupWizard {...defaultProps} />);
    expect(screen.getByText(labels.title)).toBeInTheDocument();
    expect(screen.getByLabelText(labels.dataDirectoryField)).toBeInTheDocument();
    expect(screen.getByLabelText(labels.databaseModeField)).toBeInTheDocument();
    expect(screen.getByLabelText(labels.obsidianVaultField)).toBeInTheDocument();
    expect(screen.getByLabelText(labels.aiModeField)).toBeInTheDocument();
  });

  it("disables submit when vault path is empty", () => {
    render(<SetupWizard {...defaultProps} />);
    const submitButton = screen.getByRole("button", { name: labels.completeButton });
    expect(submitButton).toBeDisabled();
  });

  it("enables submit when vault path is filled", () => {
    render(<SetupWizard {...defaultProps} />);
    fireEvent.change(screen.getByLabelText(labels.obsidianVaultField), {
      target: { value: "/home/user/vault" },
    });
    const submitButton = screen.getByRole("button", { name: labels.completeButton });
    expect(submitButton).not.toBeDisabled();
  });

  it("submits setup and calls onCompleted on success", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ ok: true }));
    render(<SetupWizard {...defaultProps} />);

    fireEvent.change(screen.getByLabelText(labels.obsidianVaultField), {
      target: { value: "/vault" },
    });
    fireEvent.click(screen.getByRole("button", { name: labels.completeButton }));

    await waitFor(() => {
      expect(defaultProps.onCompleted).toHaveBeenCalled();
    });
    expect(fetch).toHaveBeenCalledWith(
      "/api/settings/first-run",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("shows error message on API failure", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ detail: "vault path invalid" }, 400));
    render(<SetupWizard {...defaultProps} />);

    fireEvent.change(screen.getByLabelText(labels.obsidianVaultField), {
      target: { value: "/bad" },
    });
    fireEvent.click(screen.getByRole("button", { name: labels.completeButton }));

    await waitFor(() => {
      expect(screen.getByText("vault path invalid")).toBeInTheDocument();
    });
  });

  it("shows network error message on fetch failure", async () => {
    vi.mocked(fetch).mockRejectedValue(new Error("connection refused"));
    render(<SetupWizard {...defaultProps} />);

    fireEvent.change(screen.getByLabelText(labels.obsidianVaultField), {
      target: { value: "/vault" },
    });
    fireEvent.click(screen.getByRole("button", { name: labels.completeButton }));

    await waitFor(() => {
      expect(screen.getByText("connection refused")).toBeInTheDocument();
    });
  });

  it("shows postgres URL field when database mode is postgres_url", () => {
    render(<SetupWizard {...defaultProps} />);
    fireEvent.change(screen.getByLabelText(labels.databaseModeField), {
      target: { value: "postgres_url" },
    });
    expect(screen.getByLabelText(labels.postgresDsnField)).toBeInTheDocument();
  });

  it("shows AI provider fields when ai mode is openai_compatible", () => {
    render(<SetupWizard {...defaultProps} />);
    fireEvent.change(screen.getByLabelText(labels.aiModeField), {
      target: { value: "openai_compatible" },
    });
    expect(screen.getByLabelText(labels.aiBaseUrlField)).toBeInTheDocument();
    expect(screen.getByLabelText(labels.aiModelField)).toBeInTheDocument();
    expect(screen.getByLabelText(labels.aiContextSizeField)).toBeInTheDocument();
  });

  it("renders cancel button when onCancel is provided", () => {
    const onCancel = vi.fn();
    render(<SetupWizard {...defaultProps} onCancel={onCancel} />);
    const cancelButton = screen.getByRole("button", { name: "Cancel" });
    fireEvent.click(cancelButton);
    expect(onCancel).toHaveBeenCalled();
  });

  it("uses initial values when provided", () => {
    render(
      <SetupWizard
        {...defaultProps}
        initialValues={{
          dataDirectory: "/custom/dir",
          databaseMode: "postgres_url",
          postgresUrl: "postgresql://localhost/db",
          vaultPath: "/my/vault",
          exportMode: "symlink",
          opendartKey: "dart-key",
          aiMode: "openai_compatible",
          aiApiType: "cloud",
          aiProviderName: "openrouter",
          aiBaseUrl: "https://openrouter.ai/api/v1",
          aiModel: "gpt-4",
          aiContextSize: 16384,
        }}
      />,
    );
    expect(screen.getByLabelText(labels.dataDirectoryField)).toHaveValue("/custom/dir");
    expect(screen.getByLabelText(labels.obsidianVaultField)).toHaveValue("/my/vault");
    expect(screen.getByLabelText(labels.aiModelField)).toHaveValue("gpt-4");
  });

  it("has accessible form structure (fec: aria-labels, semantic HTML)", () => {
    render(<SetupWizard {...defaultProps} />);
    // Section has aria-label
    expect(screen.getByRole("region", { name: "first run setup" })).toBeInTheDocument();
    // All inputs have accessible labels
    const inputs = screen.getAllByRole("textbox");
    for (const input of inputs) {
      expect(input).toHaveAccessibleName();
    }
    // Selects have accessible labels
    const selects = screen.getAllByRole("combobox");
    for (const select of selects) {
      expect(select).toHaveAccessibleName();
    }
  });
});
