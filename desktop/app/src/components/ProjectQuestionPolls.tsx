import { useMemo, useState } from "react";

import type { ProjectPreferenceAnswer, ProjectQuestion } from "../utils/projectQuestions";

interface ProjectQuestionPollsProps {
  questions: ProjectQuestion[];
  answeredIds: Set<string>;
  disabled?: boolean;
  onSubmit: (answers: ProjectPreferenceAnswer[]) => void;
}

const AI_DECIDES = "__ai_decide__";
const CUSTOM = "__custom__";
const SKIPPED = "__skipped__";

export function ProjectQuestionPolls({ questions, answeredIds, disabled = false, onSubmit }: ProjectQuestionPollsProps) {
  const activeQuestions = useMemo(
    () => questions.filter((question) => !answeredIds.has(question.id)),
    [answeredIds, questions],
  );
  const [selections, setSelections] = useState<Record<string, string[]>>({});
  const [customValues, setCustomValues] = useState<Record<string, string>>({});

  if (activeQuestions.length === 0) {
    return <div className="project-poll-complete"><span>Preferences recorded</span><strong>The project manager is applying these decisions.</strong></div>;
  }

  const select = (question: ProjectQuestion, optionId: string) => {
    setSelections((current) => {
      const selected = current[question.id] ?? [];
      if (question.type === "single" || optionId === AI_DECIDES || optionId === SKIPPED) {
        return { ...current, [question.id]: [optionId] };
      }
      const withoutDelegation = selected.filter((id) => id !== AI_DECIDES && id !== SKIPPED);
      return {
        ...current,
        [question.id]: withoutDelegation.includes(optionId)
          ? withoutDelegation.filter((id) => id !== optionId)
          : [...withoutDelegation, optionId],
      };
    });
  };

  const canSubmit = activeQuestions.every((question) => {
    const selected = selections[question.id] ?? [];
    if (selected.length === 0) return false;
    return !selected.includes(CUSTOM) || Boolean(customValues[question.id]?.trim());
  });

  const submit = () => {
    if (!canSubmit || disabled) return;
    const answers = activeQuestions
      .filter((question) => (selections[question.id] ?? []).length > 0)
      .map((question): ProjectPreferenceAnswer => {
        const optionIds = selections[question.id] ?? [];
        const values = optionIds.map((optionId) => {
          if (optionId === AI_DECIDES) return "Decide for me";
          if (optionId === SKIPPED) return "Skipped";
          if (optionId === CUSTOM) return customValues[question.id].trim();
          return question.options.find((option) => option.id === optionId)?.label ?? optionId;
        });
        return {
          question_id: question.id,
          passport_field: question.passport_field,
          question: question.question,
          option_ids: optionIds,
          values,
        };
      });
    onSubmit(answers);
  };

  return <div className="project-polls">
    {activeQuestions.map((question, questionIndex) => {
      const selected = selections[question.id] ?? [];
      return <fieldset className="project-poll" key={question.id} disabled={disabled}>
        <legend><span>{String(questionIndex + 1).padStart(2, "0")}</span>{question.question}</legend>
        {question.rationale ? <p className="project-poll-rationale">{question.rationale}</p> : null}
        <div className="project-poll-options">
          {question.options.map((option) => <button key={option.id} type="button" className={`project-poll-option ${selected.includes(option.id) ? "selected" : ""}`} aria-pressed={selected.includes(option.id)} onClick={() => select(question, option.id)}>
            <span className="project-poll-selector" aria-hidden>{question.type === "multi" ? (selected.includes(option.id) ? "✓" : "") : (selected.includes(option.id) ? "●" : "")}</span>
            <span className="project-poll-option-copy"><strong>{option.label}</strong><small>{option.description}</small></span>
            {option.recommended ? <span className="project-poll-recommended">Recommended</span> : null}
          </button>)}
          {question.allow_custom ? <div className={`project-poll-option project-poll-custom ${selected.includes(CUSTOM) ? "selected" : ""}`}>
            <button type="button" className="project-poll-custom-select" aria-pressed={selected.includes(CUSTOM)} onClick={() => select(question, CUSTOM)}><span className="project-poll-selector" aria-hidden>{selected.includes(CUSTOM) ? (question.type === "multi" ? "✓" : "●") : ""}</span><strong>Something else</strong></button>
            <input value={customValues[question.id] ?? ""} onFocus={() => { if (!selected.includes(CUSTOM)) select(question, CUSTOM); }} onChange={(event) => setCustomValues((current) => ({ ...current, [question.id]: event.target.value }))} placeholder="Your preference" aria-label={`Custom answer for ${question.question}`} />
          </div> : null}
          <button type="button" className={`project-poll-option project-poll-delegate ${selected.includes(AI_DECIDES) ? "selected" : ""}`} aria-pressed={selected.includes(AI_DECIDES)} onClick={() => select(question, AI_DECIDES)}>
            <span className="project-poll-selector" aria-hidden>{selected.includes(AI_DECIDES) ? "●" : ""}</span>
            <span className="project-poll-option-copy"><strong>Decide for me</strong><small>Let the project manager choose the strongest direction.</small></span>
          </button>
          {!question.required ? <button type="button" className={`project-poll-option project-poll-skip ${selected.includes(SKIPPED) ? "selected" : ""}`} aria-pressed={selected.includes(SKIPPED)} onClick={() => select(question, SKIPPED)}>
            <span className="project-poll-selector" aria-hidden>{selected.includes(SKIPPED) ? "●" : ""}</span>
            <span className="project-poll-option-copy"><strong>Skip</strong><small>Leave this preference unresolved for now.</small></span>
          </button> : null}
        </div>
      </fieldset>;
    })}
    <button type="button" className="project-poll-submit" disabled={disabled || !canSubmit} onClick={submit}>Submit preferences</button>
  </div>;
}
