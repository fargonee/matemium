import type { SectionItem } from "../api/types";

interface SectionOutlineProps {
  sections: SectionItem[];
  onJump: (line: number) => void;
  embedded?: boolean;
}

export function SectionOutline({ sections, onJump, embedded = false }: SectionOutlineProps) {
  if (sections.length === 0) {
    return embedded ? (
      <p className="sidebar-empty-hint">No sections yet — add `# ---DIV: Title---` markers</p>
    ) : null;
  }

  return (
    <>
      <h2 className="panel-title">Sections</h2>
      <ul className={`section-list ${embedded ? "section-list-embedded" : ""}`}>
        {sections.map((section) => (
          <li key={`${section.line}-${section.title}`}>
            <button type="button" onClick={() => onJump(section.line)}>
              {section.title}
              <span style={{ color: "#5f6775", marginLeft: 6 }}>L{section.line}</span>
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}