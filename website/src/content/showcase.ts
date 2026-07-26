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
    status: "in-production",
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
    status: "in-production",
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
    status: "in-production",
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
    slug: "quadratic-graphs",
    title: "Quadratic graphs",
    subject: "mathematics",
    question: "How does each coefficient reshape a parabola?",
    description:
      "Compare parabolas side by side and watch each coefficient change the graph in a predictable way.",
    video: "/media/quadratic-graphs.mp4",
    poster: "/media/quadratic-graphs.jpg",
    accent: "violet",
    duration: "28 sec",
    orientation: "Portrait",
    productionPath: "Visual-first",
    capabilities: ["Plot comparison", "Trace animation", "Camera focus", "Multiple tapes"],
    sourcePath: "projects/quadratic_graphs/scenes.py",
    sourceUrl: "https://github.com/fargonee/math/blob/main/projects/quadratic_graphs/scenes.py",
    sourceExcerpt: `builder = CanvasBuilder(title="Quadratic Graphs")
tape = builder.add_tape("main")

tape.add_heading("Graphs of quadratics")
tape.add_math(r"ax^2 + bx + c = 0")

positive, negative = add_compare_row(
    tape,
    builder,
    (1, -2, 1),
    (-1, 2, 1),
)

add_plot_trace(builder, positive, x_from=-0.5, x_to=2.5)
builder.add_camera_focus(positive, zoom=2.1)`,
    featured: true,
  },
  {
    slug: "quadratic-factoring",
    title: "Quadratic factoring",
    subject: "mathematics",
    question: "How does a trinomial reveal its roots?",
    description:
      "A continuous derivation that keeps earlier reasoning visible as the camera moves through the solution.",
    video: "/media/quadratic-factoring.mp4",
    poster: "/media/quadratic-factoring.jpg",
    accent: "cyan",
    duration: "62 sec",
    orientation: "Portrait",
    productionPath: "Visual-first",
    capabilities: ["Typeset equations", "Flex layout", "Continuous tape", "Structured reveal"],
    sourcePath: "projects/quadratic_factoring/scenes.py",
    sourceUrl: "https://github.com/fargonee/math/blob/main/projects/quadratic_factoring/scenes.py",
    sourceExcerpt: `builder = CanvasBuilder(title="Quadratic Factoring")
tape = builder.add_tape("main")

tape.add_heading("Factor a quadratic")
tape.add_math(r"x^2 - 5x + 6 = 0")

tape.add_flex_row([
    tape.text_spec("multiply to"),
    tape.math_spec(r"+6"),
    tape.text_spec("and add to"),
    tape.math_spec(r"-5"),
])

tape.add_math(r"x^2 - 5x + 6 = (x - 2)(x - 3)")`,
  },
  {
    slug: "electromagnetic-waves",
    title: "Electromagnetic waves",
    subject: "physics",
    question: "How do changing fields sustain a wave?",
    description:
      "A multi-section physics lesson combining notation, explanation, spatial motion, and a mathematical surface.",
    video: "/media/em-waves.mp4",
    poster: "/media/em-waves.jpg",
    accent: "cyan",
    duration: "87 sec",
    orientation: "Portrait",
    productionPath: "Visual-first",
    capabilities: ["Physics notation", "3D surface", "Sectioned lesson", "Spatial camera"],
    sourcePath: "projects/em_waves/scenes.py",
    sourceUrl: "https://github.com/fargonee/math/blob/main/projects/em_waves/scenes.py",
    sourceExcerpt: `builder = CanvasBuilder(title="Electromagnetic Waves")
tape = builder.add_tape("main")

tape.add_heading("Maxwell's equations (vacuum)")
tape.add_math(r"\\nabla \\cdot \\vec{E} = 0")
tape.add_math(r"\\nabla \\cdot \\vec{B} = 0")
tape.add_math(
    r"\\nabla \\times \\vec{E}"
    r" = -\\frac{\\partial \\vec{B}}{\\partial t}"
)

builder.add_3d(r"z = \\sin(x)\\cos(y)", pitch=50)`,
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
];

export function subjectById(id: SubjectId): SubjectArea {
  return SUBJECT_AREAS.find((subject) => subject.id === id) ?? SUBJECT_AREAS[0];
}

export function projectBySlug(slug: string): ShowcaseProject | undefined {
  return SHOWCASE_PROJECTS.find((project) => project.slug === slug);
}
