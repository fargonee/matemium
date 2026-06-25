export type PlanId = "free" | "pro" | "teams";

export interface Plan {
  id: PlanId;
  name: string;
  priceLabel: string;
  description: string;
  features: string[];
  highlighted?: boolean;
  contactSales?: boolean;
}

export const PLANS: Plan[] = [
  {
    id: "free",
    name: "Free",
    priceLabel: "$0",
    description: "Explore the editor and render short previews.",
    features: [
      "Desktop editor & AI chat",
      "Preview-quality renders",
      "Single workspace",
    ],
  },
  {
    id: "pro",
    name: "Pro",
    priceLabel: "Paid",
    description: "Full-quality exports for creators and educators.",
    features: [
      "High & final render quality",
      "Reel cutting & static export",
      "Priority AI usage",
      "Multiple workspaces",
    ],
    highlighted: true,
  },
  {
    id: "teams",
    name: "Teams",
    priceLabel: "Contact us",
    description: "For schools, tutoring companies, and content studios.",
    features: [
      "Volume licensing",
      "Shared asset libraries",
      "Admin & billing controls",
    ],
    contactSales: true,
  },
];

export function planById(id: PlanId): Plan | undefined {
  return PLANS.find((p) => p.id === id);
}