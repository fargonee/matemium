export type SubjectId =
  | "mathematics"
  | "physics"
  | "chemistry"
  | "computer-science"
  | "engineering"
  | "economics"
  | "biology"
  | "history"
  | "philosophy"
  | "language"
  | "general-education";

export type ProjectAccent = "violet" | "cyan" | "amber";
export type ProjectStatus = "published" | "in-production";

export interface SubjectArea {
  id: SubjectId;
  name: string;
  shortName: string;
  scope: string;
  symbol: string;
  status: ProjectStatus;
}

export interface ShowcaseProject {
  slug: string;
  title: string;
  subject: SubjectId;
  question: string;
  description: string;
  video: string;
  poster: string;
  accent: ProjectAccent;
  duration: string;
  orientation: "Portrait" | "Landscape";
  productionPath: "Visual-first" | "Voice synthesis" | "Custom voice";
  capabilities: string[];
  sourcePath: string;
  sourceUrl: string;
  docsUrl?: string;
  sourceExcerpt: string;
  featured?: boolean;
}

export const SUBJECT_AREAS: SubjectArea[] = [
  {
    id: "mathematics",
    name: "Mathematics",
    shortName: "Math",
    scope: "Proofs, graphs, geometry, symbolic reasoning",
    symbol: "∑",
    status: "published",
  },
  {
    id: "physics",
    name: "Physics",
    shortName: "Physics",
    scope: "Forces, waves, fields, mechanics, relativity",
    symbol: "ψ",
    status: "published",
  },
  {
    id: "chemistry",
    name: "Chemistry",
    shortName: "Chemistry",
    scope: "Molecules, reactions, orbitals, laboratory processes",
    symbol: "H₂O",
    status: "published",
  },
  {
    id: "computer-science",
    name: "Computer science",
    shortName: "Computing",
    scope: "Algorithms, data structures, architecture, execution",
    symbol: "{ }",
    status: "in-production",
  },
  {
    id: "engineering",
    name: "Engineering",
    shortName: "Engineering",
    scope: "Systems, circuits, mechanisms, control flows",
    symbol: "⌁",
    status: "published",
  },
  {
    id: "economics",
    name: "Economics",
    shortName: "Economics",
    scope: "Models, graphs, incentives, causal relationships",
    symbol: "↗",
    status: "in-production",
  },
  {
    id: "biology",
    name: "Biology",
    shortName: "Biology",
    scope: "Cells, anatomy, cycles, systems, inheritance",
    symbol: "◌",
    status: "published",
  },
  {
    id: "history",
    name: "History",
    shortName: "History",
    scope: "Timelines, maps, relationships, cause and effect",
    symbol: "t→",
    status: "in-production",
  },
  {
    id: "philosophy",
    name: "Philosophy",
    shortName: "Philosophy",
    scope: "Arguments, objections, concepts, relationships",
    symbol: "∴",
    status: "in-production",
  },
  {
    id: "language",
    name: "Language learning",
    shortName: "Language",
    scope: "Structure, transformations, pronunciation, sequence",
    symbol: "Aa",
    status: "in-production",
  },
  {
    id: "general-education",
    name: "General education",
    shortName: "Education",
    scope: "Any idea that benefits from staged visual reasoning",
    symbol: "✦",
    status: "in-production",
  },
];

export const SHOWCASE_PROJECTS: ShowcaseProject[] = [
  {
    slug: "orbital-mechanics",
    title: "Orbital mechanics",
    subject: "physics",
    question: "Why does a satellite keep falling without hitting Earth?",
    description:
      "Follow one persistent 3D world from tangent velocity and inward gravity to re-entry, circular orbit, and escape.",
    video: "/media/orbital-mechanics.mp4",
    poster: "/media/orbital-mechanics.jpg",
    accent: "cyan",
    duration: "64 sec",
    orientation: "Portrait",
    productionPath: "Visual-first",
    capabilities: ["Persistent 3D world", "Vector animation", "Camera choreography", "Parameter sweep"],
    sourcePath: "projects/orbital_mechanics/scenes.py",
    sourceUrl: "https://github.com/fargonee/math/blob/main/projects/orbital_mechanics/scenes.py",
    sourceExcerpt: `b.add_object(
    "OrbitalWorld",
    id=WORLD_ID,
    content=orbital_world_state("circular", vectors=False),
)
b.add_camera_inspect(
    WORLD_ID,
    path=[
        b.inspect_shot(
            phi=68,
            theta=-90,
            zoom=1.15,
            hold=1.8,
        ),
    ],
)`,
    featured: true,
  },
  {
    slug: "inscribed-sphere",
    title: "Inscribed sphere",
    subject: "mathematics",
    question: "When does a sphere fit exactly inside a cube?",
    description:
      "A cube, an inscribed sphere, dimensional labels, and a moving camera within the same reasoning tape.",
    video: "/media/inscribed-sphere.mp4",
    poster: "/media/inscribed-sphere.jpg",
    accent: "amber",
    duration: "24 sec",
    orientation: "Portrait",
    productionPath: "Visual-first",
    capabilities: ["3D solids", "Object lift", "Inspect path", "Camera orbit"],
    sourcePath: "projects/inscribed_sphere/scenes.py",
    sourceUrl: "https://github.com/fargonee/math/blob/main/projects/inscribed_sphere/scenes.py",
    sourceExcerpt: `builder = CanvasBuilder(title="Inscribed Sphere")
tape = builder.add_tape("main")

tape.add_math(r"2r = s \\Rightarrow r = \\frac{s}{2}")
solid = add_inscribed_pair(
    builder,
    id="inscribed_pair",
    cube_side=2.4,
)

builder.add_solid_lift(solid, lift=1.8)
builder.add_camera_inspect(
    solid,
    path=inscribed_tangency_study_path(builder),
)`,
    featured: true,
  },
  {
    slug: "dna-to-protein",
    title: "From DNA to protein",
    subject: "biology",
    question: "How does stored information become a protein?",
    description:
      "Move across cellular scales as one sequence is transcribed, processed, exported, translated, and folded into a teaching model.",
    video: "/media/dna-to-protein.mp4",
    poster: "/media/dna-to-protein.jpg",
    accent: "violet",
    duration: "73 sec",
    orientation: "Landscape",
    productionPath: "Visual-first",
    capabilities: ["Multiscale 3D world", "Sequence transforms", "Molecular states", "Spatial transport"],
    sourcePath: "projects/dna_to_protein/scenes.py",
    sourceUrl: "https://github.com/fargonee/math/blob/main/projects/dna_to_protein/scenes.py",
    sourceExcerpt: `b.add_element_morph(
    WORLD_ID,
    world_target("dna_open"),
    run_time=1.4,
)
for index in range(5):
    b.add_element_morph(
        WORLD_ID,
        world_target("transcription", sequence_index=index),
        run_time=1.05,
    )

author_sequence_tape(b, sequence)`,
    featured: true,
  },
  {
    slug: "feedback-control",
    title: "Feedback control",
    subject: "engineering",
    question: "How does a system detect a disturbance and correct itself?",
    description:
      "Cruise control connects a moving vehicle, a closed-loop diagram, live values, and comparable response histories.",
    video: "/media/feedback-control.mp4",
    poster: "/media/feedback-control.jpg",
    accent: "amber",
    duration: "57 sec",
    orientation: "Landscape",
    productionPath: "Visual-first",
    capabilities: ["System diagrams", "Signal flow", "Time-series plots", "Physical simulation"],
    sourcePath: "projects/feedback_control/scenes.py",
    sourceUrl: "https://github.com/fargonee/math/blob/main/projects/feedback_control/scenes.py",
    sourceExcerpt: `open_time = 6.0
b.add_element_morph(
    WORLD_ID,
    world_target(
        open_time,
        feedback=False,
        stage="disturbance",
    ),
    run_time=1.7,
)

author_dashboard(b, open_dashboard, time=open_time, feedback=False)
author_loop(b, loop)`,
    featured: true,
  },
  {
    slug: "sn2-reaction",
    title: "Inside an SN2 reaction",
    subject: "chemistry",
    question: "How can bond formation, bond breaking, and inversion be one event?",
    description:
      "A locked camera makes backside attack, the transition state, and stereochemical inversion readable as one molecular motion.",
    video: "/media/sn2-reaction.mp4",
    poster: "/media/sn2-reaction.jpg",
    accent: "violet",
    duration: "30 sec",
    orientation: "Portrait",
    productionPath: "Visual-first",
    capabilities: ["3D molecular world", "Identity-preserving morphs", "Synchronized energy", "Fixed reference view"],
    sourcePath: "projects/sn2_reaction/scenes.py",
    sourceUrl: "https://github.com/fargonee/math/blob/main/projects/sn2_reaction/scenes.py",
    sourceExcerpt: `b.add_element_morph(
    WORLD_ID,
    world_target(
        0.22,
        cue="concerted",
        show_reference_plane=True,
    ),
    run_time=1.25,
)
b.add_element_morph(
    WORLD_ID,
    world_target(0.50, cue="concerted", show_reference_plane=True),
    run_time=1.65,
)`,
    featured: true,
  },
];

export function subjectById(id: SubjectId): SubjectArea {
  return SUBJECT_AREAS.find((subject) => subject.id === id) ?? SUBJECT_AREAS[0];
}

export function projectBySlug(slug: string): ShowcaseProject | undefined {
  return SHOWCASE_PROJECTS.find((project) => project.slug === slug);
}
