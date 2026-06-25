import type { User } from "@supabase/supabase-js";

import { env } from "@/lib/env";
import type { Profile, UserRole } from "@/lib/types";

export interface AuthProfile {
  id: string;
  email: string;
  full_name: string | null;
  role: UserRole;
  plan: string;
}

export function getAdminEmails(): string[] {
  return env.adminEmails
    .split(",")
    .map((e) => e.trim().toLowerCase())
    .filter(Boolean);
}

export function isAdmin(user: User | null, profile: AuthProfile | null): boolean {
  if (!user) return false;
  if (profile?.role === "admin") return true;
  const email = user.email?.toLowerCase();
  return Boolean(email && getAdminEmails().includes(email));
}

export function displayName(user: User, profile: AuthProfile | Profile | null): string {
  if (profile?.full_name) return profile.full_name;
  if (user.user_metadata?.full_name) return String(user.user_metadata.full_name);
  if (user.user_metadata?.name) return String(user.user_metadata.name);
  return user.email?.split("@")[0] ?? "User";
}