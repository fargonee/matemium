export type PlanId = "free" | "pro" | "teams" | "tokens_1000" | "tokens_5000";

export interface Plan {
  id: PlanId;
  name: string;
  priceLabel: string;
  description: string;
  features: string[];
  highlighted?: boolean;
  contactSales?: boolean;
  isTokenPack?: boolean;
  credits?: number;
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

// Platform credit / token packs for LLM usage (one-time purchases)
export const CREDIT_PACKS: Plan[] = [
  {
    id: "tokens_1000",
    name: "1,000 Credits",
    priceLabel: "Buy",
    description: "Platform LLM & TTS usage. Credits priced with our margin on real provider costs.",
    features: ["~1,000,000 tokens equivalent (model dependent)", "Use with our hosted models", "Auto pricing with profit margin"],
    isTokenPack: true,
    credits: 1000,
  },
  {
    id: "tokens_5000",
    name: "5,000 Credits",
    priceLabel: "Buy",
    description: "Better value for heavy AI usage (code + audio).",
    features: ["~5M tokens equivalent", "Priority in platform pool when available", "Full access to supported models"],
    isTokenPack: true,
    credits: 5000,
    highlighted: true,
  },
];

export const ALL_PURCHASABLE = [...PLANS.filter(p => p.id !== 'free' && !p.contactSales), ...CREDIT_PACKS];