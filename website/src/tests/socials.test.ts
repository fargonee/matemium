import { describe, expect, it } from "vitest";

import { CONTACT_EMAIL, SOCIAL_LINKS } from "@/content/socials";

const CANONICAL_DESTINATIONS = [
  "https://github.com/fargonee/matemium",
  "https://youtube.com/@matemium",
  "https://www.instagram.com/matemium",
  "https://t.me/matemium",
  "mailto:matemiumm@gmail.com",
  "https://www.reddit.com/user/matemium/",
  "https://www.producthunt.com/@matemium",
  "https://x.com/matemium",
  "https://bsky.app/profile/matemium.bsky.social",
  "https://dev.to/matemium",
];

describe("official Matemium links", () => {
  it("keeps every canonical social and contact destination in one directory", () => {
    expect(SOCIAL_LINKS.map((item) => item.href)).toEqual(CANONICAL_DESTINATIONS);
    expect(CONTACT_EMAIL).toBe("matemiumm@gmail.com");
  });

  it("uses stable unique identifiers", () => {
    expect(new Set(SOCIAL_LINKS.map((item) => item.id)).size).toBe(SOCIAL_LINKS.length);
  });
});
