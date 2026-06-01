import { describe, expect, it } from "vitest";

import { authCallbackUrl, providerLabel, supabaseRedirectConfig } from "./supabase-auth";

describe("supabase auth helpers", () => {
  it("builds exact local callback URL for OAuth redirectTo", () => {
    expect(authCallbackUrl("http://localhost:3000")).toBe("http://localhost:3000/auth/callback");
  });

  it("keeps Kakao usable without an email requirement", () => {
    expect(providerLabel("kakao")).toBe("Kakao");
    expect(supabaseRedirectConfig.kakao.requiredProfileFields).toEqual(["nickname"]);
  });

  it("documents Google and Kakao callback setup values", () => {
    expect(supabaseRedirectConfig.google.supabaseCallbackPath).toBe("/auth/v1/callback");
    expect(supabaseRedirectConfig.kakao.supabaseCallbackPath).toBe("/auth/v1/callback");
  });
});
