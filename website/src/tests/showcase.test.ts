import { describe, expect, it } from "vitest";

import {
  SHOWCASE_PROJECTS,
  SUBJECT_AREAS,
  projectBySlug,
  subjectById,
} from "@/content/showcase";

describe("showcase catalog", () => {
  it("uses the launch showcase selection", () => {
    expect(SHOWCASE_PROJECTS.map((project) => project.slug)).toEqual(
      expect.arrayContaining([
        "inscribed-sphere",
        "orbital-mechanics",
        "dna-to-protein",
        "feedback-control",
        "sn2-reaction",
      ]),
    );
    expect(SHOWCASE_PROJECTS).toHaveLength(5);
    expect(SHOWCASE_PROJECTS.every((project) => project.featured)).toBe(true);
  });

  it("uses unique project slugs", () => {
    const slugs = SHOWCASE_PROJECTS.map((project) => project.slug);
    expect(new Set(slugs).size).toBe(slugs.length);
  });

  it("connects every project to a known subject and case-study route", () => {
    const subjectIds = new Set(SUBJECT_AREAS.map((subject) => subject.id));

    for (const project of SHOWCASE_PROJECTS) {
      expect(subjectIds.has(project.subject)).toBe(true);
      expect(projectBySlug(project.slug)).toBe(project);
      expect(project.video).toMatch(/^\/media\/.+\.mp4$/);
      expect(project.poster).toMatch(/^\/media\/.+\.jpg$/);
      expect(project.sourceExcerpt.trim().length).toBeGreaterThan(40);
    }
  });

  it("marks every subject with published projects as published", () => {
    for (const project of SHOWCASE_PROJECTS) {
      expect(subjectById(project.subject).status).toBe("published");
    }
  });

  it("represents the planned cross-subject range", () => {
    expect(SUBJECT_AREAS.map((subject) => subject.id)).toEqual(
      expect.arrayContaining([
        "mathematics",
        "physics",
        "chemistry",
        "computer-science",
        "engineering",
        "economics",
        "biology",
        "history",
        "philosophy",
        "language",
        "general-education",
      ]),
    );
  });
});
