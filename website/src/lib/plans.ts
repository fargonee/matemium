export type PlanId = "free";

export interface Plan {
  id: PlanId;
  name: string;
  priceLabel: string;
  description: string;
  features: string[];
  highlighted?: boolean;
}

export const PLANS: Plan[] = [
  {
    id: "free",
    name: "Matemium",
    priceLabel: "$0",
    description: "Free desktop authoring, rendering, exports, and AI-assisted workflows with your own provider keys.",
    features: [
      "Desktop editor and local rendering",
      "Full-quality exports and reel cutting",
      "OpenRouter-first BYO AI provider support",
      "Optional local models for offline workflows",
    ],
    highlighted: true,
  },
];

export function planById(id: PlanId): Plan | undefined {
  return PLANS.find((p) => p.id === id);
}

export const ALL_PURCHASABLE: Plan[] = [];
