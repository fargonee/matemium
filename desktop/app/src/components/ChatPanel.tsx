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
}: ChatPanelProps) {
  return (
    <>
      <h2 className="panel-title">AI Chat {llmStatus && <span style={{ fontSize: "0.7rem", color: "#7c8595" }}>({llmStatus})</span>}</h2>
      <div className="chat-history">
        {messages.length === 0 ? (
          <div style={{ color: "#7c8595", fontSize: "0.8rem" }}>
            Ask for help editing scenes.py
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
          placeholder="Ask Matemium to improve your scene..."
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) onSend();
          }}
        />
        <button type="button" className="btn btn-primary" disabled={busy} onClick={onSend}>
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