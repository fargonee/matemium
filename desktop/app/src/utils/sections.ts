import type { SectionItem } from "../api/types";

const SECTION_RE = /^#\s*---DIV:\s*(.+?)---\s*$/;

export function parseSections(source: string): SectionItem[] {
  const lines = source.split("\n");
  const sections: SectionItem[] = [];

  for (let i = 0; i < lines.length; i += 1) {
    const match = SECTION_RE.exec(lines[i].trim());
    if (match) {
      sections.push({ title: match[1].trim(), line: i + 1 });
    }
  }

  return sections;
}