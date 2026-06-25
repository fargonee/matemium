export type UserRole = "user" | "admin";

export type SubscriptionPlan = "free" | "pro" | "teams";
export type SubscriptionStatus =
  | "active"
  | "trialing"
  | "past_due"
  | "canceled"
  | "incomplete";

export interface Profile {
  id: string;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  role: UserRole;
  plan: SubscriptionPlan;
  lemon_customer_id: string | null;
  created_at: string;
  updated_at: string;
}