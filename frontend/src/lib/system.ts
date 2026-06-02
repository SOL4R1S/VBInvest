export type SystemShutdownResult =
  | {
      readonly ok: true;
      readonly message: null;
    }
  | {
      readonly ok: false;
      readonly message: string;
    };

export async function shutdownSystem(): Promise<SystemShutdownResult> {
  let response: Response;
  try {
    response = await fetch("/api/system/shutdown", {
      method: "POST",
      headers: authHeaders(),
    });
  } catch (_error) {
    return {
      ok: false,
      message: "종료 요청을 보낼 수 없습니다. 네트워크 상태를 확인한 뒤 다시 시도해주세요.",
    };
  }

  if (response.ok) {
    return { ok: true, message: null };
  }
  if (response.status === 401) {
    return {
      ok: false,
      message: "로컬 세션이 유효하지 않습니다. 로컬 프로그램을 다시 시작한 뒤 재시도해주세요.",
    };
  }
  if (response.status === 503) {
    return {
      ok: false,
      message: "종료 요청이 현재 비활성화되어 있습니다.",
    };
  }
  return {
    ok: false,
    message: "종료 요청이 실패했습니다. 잠시 후 다시 시도해주세요.",
  };
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
