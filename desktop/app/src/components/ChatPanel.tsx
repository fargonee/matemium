import type { ChatMessage, CodeEdit } from "../api/types";

interface ChatPanelProps {
  messages: ChatMessage[];
  pendingEdit: CodeEdit | null;
  input: string;
  busy: boolean;
  onInputChange: (value: string) => void;
  onSend: () => void;
  onApplyEdit: () => void;
  // LLM status from profile (for credits / mode visibility)
  llmStatus?: string;
  onGenerateAudio?: () => void;
  disabled?: boolean;
}

export function ChatPanel({
  messages,
  pendingEdit,
  input,
  busy,
  onInputChange,
  onSend,
  onApplyEdit,
  llmStatus,
  onGenerateAudio,
  disabled = false,
}: ChatPanelProps) {
  return (
    <>
      <h2 className="panel-title">AI Assistant {llmStatus && <span className="llm-sub">({llmStatus})</span>}</h2>
      <div className="chat-history">
        {messages.length === 0 ? (
          <div style={{ color: "#7c8595", fontSize: "0.8rem" }}>
            Ask the assistant to refine or extend the scene...
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={`chat-bubble ${message.role}`}
            >
              {message.content}
            </div>
          ))
        )}
        {pendingEdit ? (
          <div className="code-edit-card">
            <p>{pendingEdit.description}</p>
            <button type="button" className="btn btn-primary" onClick={onApplyEdit}>
              Apply to editor
            </button>
          </div>
        ) : null}
      </div>
      <div className="chat-input-row">
        <textarea
          value={input}
          placeholder={disabled ? "Waiting for engine readiness..." : "Describe changes or ask for help..."}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) onSend();
          }}
          disabled={disabled}
          className={disabled ? "disabled" : ""}
        />
        <button type="button" className="btn btn-primary" disabled={busy || disabled} onClick={onSend}>
          Send
        </button>
        {onGenerateAudio && (
          <button
            type="button"
            className="btn"
            disabled={busy}
            onClick={onGenerateAudio}
            title="Generate audio (TTS) from input or last message using current LLM mode"
          >
            🔊
          </button>
        )}
      </div>
    </>
  );
}