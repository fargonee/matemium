export type SocialLink = {
  id: string;
  label: string;
  handle: string;
  href: string;
  mark: string;
  accent: string;
  description: string;
  email?: boolean;
};

export const CONTACT_EMAIL = "matemiumm@gmail.com";

export const SOCIAL_LINKS: SocialLink[] = [
  {
    id: "github",
    label: "GitHub",
    handle: "fargonee/matemium",
    href: "https://github.com/fargonee/matemium",
    mark: "GH",
    accent: "#f2f1f5",
    description: "Source, issues, releases, and contribution history.",
  },
  {
    id: "youtube",
    label: "YouTube",
    handle: "@matemium",
    href: "https://youtube.com/@matemium",
    mark: "▶",
    accent: "#ff4d5f",
    description: "Finished visual explanations, demos, and longer walkthroughs.",
  },
  {
    id: "instagram",
    label: "Instagram",
    handle: "@matemium",
    href: "https://www.instagram.com/matemium",
    mark: "IG",
    accent: "#e76fc5",
    description: "Short visual stories, reels, and work from the studio.",
  },
  {
    id: "telegram",
    label: "Telegram",
    handle: "@matemium",
    href: "https://t.me/matemium",
    mark: "TG",
    accent: "#62b9f5",
    description: "Project announcements, release notes, and direct updates.",
  },
  {
    id: "email",
    label: "Email",
    handle: CONTACT_EMAIL,
    href: `mailto:${CONTACT_EMAIL}`,
    mark: "@",
    accent: "#61ddb0",
    description: "Questions, partnerships, press, and private conversations.",
    email: true,
  },
  {
    id: "reddit",
    label: "Reddit",
    handle: "u/matemium",
    href: "https://www.reddit.com/user/matemium/",
    mark: "R/",
    accent: "#ff7347",
    description: "Discussions, experiments, and conversations with the community.",
  },
  {
    id: "product-hunt",
    label: "Product Hunt",
    handle: "@matemium",
    href: "https://www.producthunt.com/@matemium",
    mark: "PH",
    accent: "#ff7a66",
    description: "Follow Matemium's launch and product milestones.",
  },
  {
    id: "x",
    label: "X",
    handle: "@matemium",
    href: "https://x.com/matemium",
    mark: "X",
    accent: "#d9dce5",
    description: "Short build updates, releases, and visual work in progress.",
  },
  {
    id: "bluesky",
    label: "Bluesky",
    handle: "@matemium.bsky.social",
    href: "https://bsky.app/profile/matemium.bsky.social",
    mark: "BS",
    accent: "#70b7ff",
    description: "Open-web updates and notes from Matemium's development.",
  },
  {
    id: "dev",
    label: "DEV Community",
    handle: "@matemium",
    href: "https://dev.to/matemium",
    mark: "DEV",
    accent: "#b7adff",
    description: "Technical articles about the engine, desktop studio, and AI workflow.",
  },
];
