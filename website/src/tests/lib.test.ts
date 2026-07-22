import { describe, expect, it, vi } from "vitest";
import type { User } from "@supabase/supabase-js";

import { displayName, isAdmin } from "@/lib/auth";
import { planById } from "@/lib/plans";

vi.mock("@/lib/env", () => ({
  env: {
    adminEmails: "admin@example.com,other@example.com",
  },
}));

function makeUser(overrides: Partial<User> = {}): User {
  return {
    id: "user-1",
    email: "user@example.com",
    app_metadata: {},
    user_metadata: {},
    aud: "authenticated",
    created_at: "",
    ...overrides,
  } as User;
}

describe("isAdmin", () => {
  it("returns true when profile role is admin", () => {
    const user = makeUser();
    expect(
      isAdmin(user, {
        id: "1",
        email: "user@example.com",
        full_name: null,
        role: "admin",
        plan: "pro",
      })
    ).toBe(true);
  });

  it("returns true when email is in admin list", () => {
    const user = makeUser({ email: "admin@example.com" });
    expect(isAdmin(user, null)).toBe(true);
  });

  it("returns false for regular users", () => {
    const user = makeUser({ email: "user@example.com" });
    expect(
      isAdmin(user, {
        id: "1",
        email: "user@example.com",
        full_name: null,
        role: "user",
        plan: "free",
      })
    ).toBe(false);
  });
});

describe("displayName", () => {
  it("prefers profile full_name", () => {
    const user = makeUser({ email: "user@example.com" });
    expect(
      displayName(user, {
        id: "1",
        email: "user@example.com",
        full_name: "Ada Lovelace",
        role: "user",
        plan: "free",
      })
    ).toBe("Ada Lovelace");
  });

  it("falls back to email local part", () => {
    const user = makeUser({ email: "ada@example.com" });
    expect(displayName(user, null)).toBe("ada");
  });
});

describe("planById", () => {
  it("returns the matching plan", () => {
    expect(planById("free")?.name).toBe("Matemium");
  });

  it("returns undefined for unknown ids", () => {
    expect(planById("unknown" as "free")).toBeUndefined();
  });
});
