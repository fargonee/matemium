import type { ChatMessage } from "../api/types";

export interface ProjectQuestionOption {
  id: string;
  label: string;
  description: string;
  recommended?: boolean;
}

export interface ProjectQuestion {
  id: string;
  passport_field: string;
  question: string;
  rationale?: string;
  type: "single" | "multi";
  required?: boolean;
  allow_custom?: boolean;
  options: ProjectQuestionOption[];
}

export interface ProjectPreferenceAnswer {
  question_id: string;
  passport_field: string;
  question: string;
  option_ids: string[];
  values: string[];
}

const QUESTIONS_BLOCK = /```project_questions\s*([\s\S]*?)```/i;
const PREFERENCE_BLOCK = /\[PROJECT_PREFERENCE_RESPONSE\]\s*([\s\S]*?)\s*\[\/PROJECT_PREFERENCE_RESPONSE\]/i;
const SAFE_ID = /^[a-z0-9][a-z0-9_-]{0,79}$/i;

function validOption(value: unknown): value is ProjectQuestionOption {
  if (!value || typeof value !== "object") return false;
  const option = value as Partial<ProjectQuestionOption>;
  return typeof option.id === "string" && SAFE_ID.test(option.id)
    && typeof option.label === "string" && option.label.trim().length > 0 && option.label.length <= 80
    && typeof option.description === "string" && option.description.length <= 240;
}

function validQuestion(value: unknown): value is ProjectQuestion {
  if (!value || typeof value !== "object") return false;
  const question = value as Partial<ProjectQuestion>;
  if (typeof question.id !== "string" || !SAFE_ID.test(question.id)) return false;
  if (typeof question.passport_field !== "string" || !SAFE_ID.test(question.passport_field.replaceAll(".", "_"))) return false;
  if (typeof question.question !== "string" || question.question.trim().length === 0 || question.question.length > 300) return false;
  if (question.type !== "single" && question.type !== "multi") return false;
  if (!Array.isArray(question.options) || question.options.length < 2 || question.options.length > 5) return false;
  if (!question.options.every(validOption)) return false;
  return new Set(question.options.map((option) => option.id)).size === question.options.length
    && question.options.filter((option) => option.recommended).length <= 1;
}

export function extractProjectQuestions(content: string): { cleanContent: string; questions: ProjectQuestion[] } {
  const match = QUESTIONS_BLOCK.exec(content);
  if (!match) return { cleanContent: content, questions: [] };
  try {
    const payload = JSON.parse(match[1]) as { questions?: unknown[] };
    if (!Array.isArray(payload.questions) || payload.questions.length < 1 || payload.questions.length > 3) {
      return { cleanContent: content, questions: [] };
    }
    if (!payload.questions.every(validQuestion)) return { cleanContent: content, questions: [] };
    return {
      cleanContent: content.replace(QUESTIONS_BLOCK, "").trim(),
      questions: payload.questions,
    };
  } catch {
    return { cleanContent: content, questions: [] };
  }
}

export function encodeProjectPreferenceResponse(answers: ProjectPreferenceAnswer[]): string {
  return `[PROJECT_PREFERENCE_RESPONSE]\n${JSON.stringify({ answers })}\n[/PROJECT_PREFERENCE_RESPONSE]`;
}

export function parseProjectPreferenceResponse(content: string): ProjectPreferenceAnswer[] | null {
  const match = PREFERENCE_BLOCK.exec(content);
  if (!match) return null;
  try {
    const payload = JSON.parse(match[1]) as { answers?: ProjectPreferenceAnswer[] };
    return Array.isArray(payload.answers) ? payload.answers : null;
  } catch {
    return null;
  }
}

export function answeredProjectQuestionIds(messages: ChatMessage[], afterIndex: number): Set<string> {
  const ids = new Set<string>();
  for (const message of messages.slice(afterIndex + 1)) {
    if (message.role !== "user") continue;
    for (const answer of parseProjectPreferenceResponse(message.content) ?? []) {
      if (typeof answer.question_id === "string") ids.add(answer.question_id);
    }
  }
  return ids;
}
