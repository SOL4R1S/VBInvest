import { createClient, type Provider, type SupabaseClient } from "@supabase/supabase-js";

export type VbinvestOAuthProvider = "google" | "kakao";

export const supabaseRedirectConfig = {
  google: {
    label: "Google",
    supabaseCallbackPath: "/auth/v1/callback",
    requiredProfileFields: ["email", "name"],
  },
  kakao: {
    label: "Kakao",
    supabaseCallbackPath: "/auth/v1/callback",
    requiredProfileFields: ["nickname"],
  },
} as const;

export function authCallbackUrl(origin: string = browserOrigin()) {
  return `${origin.replace(/\/$/, "")}/auth/callback`;
}

export function providerLabel(provider: VbinvestOAuthProvider) {
  return supabaseRedirectConfig[provider].label;
}

export function supabaseBrowserClient(): SupabaseClient | null {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const publishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if (!url || !publishableKey) {
    return null;
  }
  return createClient(url, publishableKey);
}

export async function signInWithProvider(provider: VbinvestOAuthProvider) {
  const supabase = supabaseBrowserClient();
  if (supabase === null) {
    return { ok: false, error: "supabase env not configured" };
  }
  const { error } = await supabase.auth.signInWithOAuth({
    provider: provider satisfies Provider,
    options: { redirectTo: authCallbackUrl() },
  });
  return { ok: !error, error: error?.message ?? null };
}

function browserOrigin() {
  if (typeof window === "undefined") {
    return process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
  }
  return window.location.origin;
}
