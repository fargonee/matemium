import { useEffect, useRef, useState } from "react";
import type { ChatMessage, CodeEdit, Conversation } from "../api/types";

interface ChatPanelProps {
  messages: ChatMessage[];
  pendingEdit: CodeEdit | null;
  input: string;
  busy: boolean;
  progressStep?: "idle" | "preparing" | "retrieving" | "thinking" | "processing" | "refreshing";
  contextMatches?: Array<{ file: string; score?: number }>;
  validationErrors?: Array<{ line: number; message: string }>;
  onFixErrors?: () => void;
  onInputChange: (value: string) => void;
  onSend: () => void;
  onApplyEdit: () => void;
  // LLM status from profile (for credits / mode visibility)
  llmStatus?: string;
  onGenerateAudio?: () => void;
  disabled?: boolean;
  onUploadFile?: (file: File) => void;
  uploadedReferences?: string[];
  onDeleteReference?: (fileName: string) => void;
  // Local/External model configurations
  useLocalLlm?: boolean;
  onToggleLocalLlm?: (val: boolean) => void;
  localLlmModel?: string;
  onLocalLlmModelChange?: (val: string) => void;
  externalLlmModel?: string;
  onExternalLlmModelChange?: (val: string) => void;
  reasoningLevel?: string;
  onReasoningLevelChange?: (val: string) => void;
  downloadedModels?: Record<string, boolean>;
  // Conversation management
  conversations?: Conversation[];
  activeConversationId?: string | null;
  onSelectConversation?: (id: string) => void;
  onNewConversation?: () => void;
  onDeleteConversation?: (id: string) => void;
}

export function ChatPanel({
  messages,
  pendingEdit,
  input,
  busy,
  progressStep,
  contextMatches,
  validationErrors,
  onFixErrors,
  onInputChange,
  onSend,
  onApplyEdit,
  llmStatus,
  onGenerateAudio,
  disabled = false,
  onUploadFile,
  uploadedReferences = [],
  onDeleteReference,
  useLocalLlm = false,
  onToggleLocalLlm,
  localLlmModel = "llm-qwen-coder-3b-q4",
  onLocalLlmModelChange,
  externalLlmModel = "gpt-4o-mini",
  onExternalLlmModelChange,
  reasoningLevel = "low",
  onReasoningLevelChange,
  downloadedModels = {},
  conversations = [],
  activeConversationId = null,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
}: ChatPanelProps) {
  const stepsOrder = ["preparing", "retrieving", "thinking", "processing", "refreshing"] as const;

  const [popoverOpen, setPopoverOpen] = useState(false);

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    // Reset height to let scrollHeight recalculate correctly for shrinking
    textarea.style.height = "auto";
    
    // Calculate content height
    const scrollHeight = textarea.scrollHeight;
    
    // If scrollHeight is less than 160px, hide scrollbar. Otherwise, show it.
    if (scrollHeight > 160) {
      textarea.style.height = "160px";
      textarea.style.overflowY = "auto";
    } else {
      textarea.style.height = `${scrollHeight}px`;
      textarea.style.overflowY = "hidden";
    }
  }, [input]);

  function getStepStatus(
    step: typeof stepsOrder[number],
    current: typeof stepsOrder[number] | "idle" | undefined
  ) {
    if (!current || current === "idle") return "pending";
    const stepIdx = stepsOrder.indexOf(step);
    const currentIdx = stepsOrder.indexOf(current);
    if (stepIdx < currentIdx) return "completed";
    if (stepIdx === currentIdx) return "active";
    return "pending";
  }

  interface ToolCallData {
    name: string;
    args: string;
  }

  function parseResponseBlocks(content: string): { 
    thought: string | null; 
    toolCall: ToolCallData | null;
    toolOutput: string | null;
    cleanContent: string;
  } {
    let thought: string | null = null;
    let toolCall: ToolCallData | null = null;
    let toolOutput: string | null = null;
    let cleanContent = content;

    const thoughtRegex = /<(?:thought|reasoning)>([\s\S]*?)<\/(?:thought|reasoning)>/gi;
    const thoughtMatch = thoughtRegex.exec(content);
    if (thoughtMatch) {
      thought = thoughtMatch[1].trim();
      cleanContent = cleanContent.replace(thoughtRegex, "");
    }

    const toolCallRegex = /<tool_call\s+name=["']([^"']+)["']\s*>([\s\S]*?)<\/tool_call>/gi;
    const toolCallMatch = toolCallRegex.exec(content);
    if (toolCallMatch) {
      toolCall = {
        name: toolCallMatch[1].trim(),
        args: toolCallMatch[2].trim(),
      };
      cleanContent = cleanContent.replace(toolCallRegex, "");
    }

    const toolOutputRegex = /<tool_output>([\s\S]*?)<\/tool_output>/gi;
    const toolOutputMatch = toolOutputRegex.exec(content);
    if (toolOutputMatch) {
      toolOutput = toolOutputMatch[1].trim();
      cleanContent = cleanContent.replace(toolOutputRegex, "");
    }

    return { 
      thought, 
      toolCall, 
      toolOutput,
      cleanContent: cleanContent.trim() 
    };
  }

  const activeConversation = conversations.find((c) => c.id === activeConversationId);
  const activeTitle = activeConversation ? activeConversation.title : "AI Assistant";

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "var(--bg-base)" }}>
      {/* Dynamic Styled Header Toggle & Conversation Switcher */}
      <h2 className="panel-title" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%", flexShrink: 0, position: "relative" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer", textTransform: "none", letterSpacing: "normal" }} onClick={() => setPopoverOpen(!popoverOpen)}>
          <span style={{ fontWeight: 600, fontSize: "0.72rem", color: "var(--text-primary)" }}>💬 {activeTitle}</span>
          {llmStatus && <span className="llm-sub" style={{ fontSize: "0.6rem", opacity: 0.6, fontWeight: 400 }}>({llmStatus})</span>}
          <span style={{ fontSize: "0.55rem", opacity: 0.7, color: "var(--text-tertiary)" }}>▼</span>
        </div>
        
        {popoverOpen && (
          <div
            style={{
              position: "absolute",
              top: "100%",
              left: "12px",
              right: "12px",
              background: "var(--bg-elevated)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "8px",
              boxShadow: "var(--shadow-lg)",
              zIndex: 10,
              padding: "8px",
              display: "flex",
              flexDirection: "column",
              gap: "6px",
              maxHeight: "260px",
              textTransform: "none",
              letterSpacing: "normal",
            }}
          >
            {/* New Conversation Button */}
            <button
              type="button"
              onClick={() => {
                onNewConversation?.();
                setPopoverOpen(false);
              }}
              style={{
                background: "var(--accent-subtle)",
                border: "1px solid var(--accent-border)",
                color: "var(--text-primary)",
                padding: "6px",
                borderRadius: "6px",
                fontSize: "0.75rem",
                fontWeight: 600,
                cursor: "pointer",
                width: "100%",
                transition: "all 0.12s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "var(--accent)";
                e.currentTarget.style.color = "white";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "var(--accent-subtle)";
                e.currentTarget.style.color = "var(--text-primary)";
              }}
            >
              ＋ New Conversation
            </button>

            {/* List of Conversations */}
            <div style={{ overflowY: "auto", display: "flex", flexDirection: "column", gap: "4px" }}>
              {conversations.map((c) => (
                <div
                  key={c.id}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "6px 8px",
                    borderRadius: "6px",
                    background: c.id === activeConversationId ? "rgba(255, 255, 255, 0.05)" : "transparent",
                    cursor: "pointer",
                    transition: "background 0.12s ease",
                  }}
                  onClick={() => {
                    onSelectConversation?.(c.id);
                    setPopoverOpen(false);
                  }}
                  onMouseEnter={(e) => {
                    if (c.id !== activeConversationId) {
                      e.currentTarget.style.background = "rgba(255, 255, 255, 0.02)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (c.id !== activeConversationId) {
                      e.currentTarget.style.background = "transparent";
                    }
                  }}
                >
                  <span
                    style={{
                      fontSize: "0.75rem",
                      color: c.id === activeConversationId ? "var(--text-primary)" : "var(--text-secondary)",
                      fontWeight: c.id === activeConversationId ? 600 : 400,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      maxWidth: "140px",
                    }}
                    title={c.title}
                  >
                    {c.title}
                  </span>
                  
                  {/* Delete Conversation Button */}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation(); // Prevent switching to deleted conversation
                      onDeleteConversation?.(c.id);
                    }}
                    style={{
                      background: "none",
                      border: "none",
                      color: "var(--text-muted)",
                      cursor: "pointer",
                      fontSize: "0.85rem",
                      padding: "2px 4px",
                      borderRadius: "4px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      transition: "color 0.12s ease",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.color = "var(--error)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.color = "var(--text-muted)";
                    }}
                    title="Delete Conversation"
                  >
                    🗑️
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {onToggleLocalLlm && (
          <div style={{ display: "flex", gap: "2px", background: "var(--bg-elevated)", padding: "2px", borderRadius: "6px", border: "1px solid var(--border-subtle)", textTransform: "none" }}>
            <button
              type="button"
              onClick={() => onToggleLocalLlm(true)}
              style={{
                padding: "2px 8px",
                fontSize: "0.65rem",
                borderRadius: "4px",
                border: "none",
                cursor: "pointer",
                fontWeight: useLocalLlm ? 600 : 400,
                background: useLocalLlm ? "var(--accent)" : "transparent",
                color: useLocalLlm ? "white" : "var(--text-secondary)",
                transition: "all 0.12s ease",
              }}
              title="Run offline models fully on your own device"
            >
              Local
            </button>
            <button
              type="button"
              onClick={() => onToggleLocalLlm(false)}
              style={{
                padding: "2px 8px",
                fontSize: "0.65rem",
                borderRadius: "4px",
                border: "none",
                cursor: "pointer",
                fontWeight: !useLocalLlm ? 600 : 400,
                background: !useLocalLlm ? "var(--accent)" : "transparent",
                color: !useLocalLlm ? "white" : "var(--text-secondary)",
                transition: "all 0.12s ease",
              }}
              title="Use high-fidelity external/cloud models"
            >
              Cloud
            </button>
          </div>
        )}
      </h2>

      {/* Main Scrollable History */}
      <div className="chat-history" style={{ flex: 1, overflowY: "auto", paddingBottom: "12px" }}>
        {messages.length === 0 ? (
          <div style={{ color: "#7c8595", fontSize: "0.8rem" }}>
            Ask the assistant to refine or extend the scene...
          </div>
        ) : (
          messages.map((message, index) => {
            if (message.role === "assistant") {
              const { thought, toolCall, toolOutput, cleanContent } = parseResponseBlocks(message.content);
              return (
                <div
                  key={`${message.role}-${index}`}
                  className={`chat-bubble ${message.role}`}
                >
                  {thought && (
                    <details className="cognitive-reasoning" open={false}>
                      <summary className="reasoning-summary">
                        <span>🧠 Cognitive Reasoning</span>
                      </summary>
                      <div className="reasoning-content">
                        {thought}
                      </div>
                    </details>
                  )}
                  {toolCall && (
                    <div style={{
                      margin: "8px 0",
                      background: "rgba(6, 182, 212, 0.04)",
                      border: "1px solid rgba(6, 182, 212, 0.15)",
                      borderRadius: "6px",
                      padding: "10px",
                      fontFamily: "monospace",
                      fontSize: "0.75rem",
                    }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px", fontWeight: "bold", color: "var(--accent-color, #06b6d4)", marginBottom: "4px" }}>
                        <span>🛠️ Calling Tool:</span>
                        <code style={{ background: "rgba(6, 182, 212, 0.15)", padding: "2px 4px", borderRadius: "4px" }}>{toolCall.name}</code>
                      </div>
                      <pre style={{ margin: 0, overflowX: "auto", color: "var(--text-muted)", whiteSpace: "pre-wrap" }}>{toolCall.args}</pre>
                    </div>
                  )}
                  {toolOutput && (
                    <details style={{
                      margin: "8px 0",
                      background: "rgba(255, 255, 255, 0.02)",
                      border: "1px solid rgba(255, 255, 255, 0.05)",
                      borderRadius: "6px",
                    }}>
                      <summary style={{
                        padding: "6px 10px",
                        cursor: "pointer",
                        fontSize: "0.7rem",
                        fontWeight: 600,
                        color: "var(--text-muted)",
                        userSelect: "none"
                      }}>
                        👀 Tool Observation Output
                      </summary>
                      <pre style={{
                        margin: 0,
                        padding: "10px",
                        overflowX: "auto",
                        fontFamily: "monospace",
                        fontSize: "0.7rem",
                        background: "rgba(0, 0, 0, 0.15)",
                        borderTop: "1px solid rgba(255, 255, 255, 0.05)",
                        color: "var(--fg-dim, #9ca3af)",
                        maxHeight: "200px",
                        overflowY: "auto",
                        whiteSpace: "pre-wrap"
                      }}>{toolOutput}</pre>
                    </details>
                  )}
                  {cleanContent && <div className="assistant-clean-text">{cleanContent}</div>}
                </div>
              );
            }

            return (
              <div
                key={`${message.role}-${index}`}
                className={`chat-bubble ${message.role}`}
              >
                <div>{message.content}</div>
                {message.references && message.references.length > 0 && (
                  <div className="message-attachments-container" style={{ marginTop: "8px", display: "flex", flexWrap: "wrap", gap: "6px" }}>
                    {message.references.map((ref) => (
                      <span
                        key={ref}
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          backgroundColor: "rgba(255,255,255,0.08)",
                          border: "1px solid rgba(255,255,255,0.15)",
                          borderRadius: "10px",
                          padding: "2px 8px",
                          fontSize: "0.7rem",
                          gap: "4px",
                          color: "#ccc",
                        }}
                      >
                        📎 {ref}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            );
          })
        )}

        {busy && progressStep && progressStep !== "idle" && (
          <div className="operation-progress-ledger">
            <p className="ledger-title">⚙️ AI Orchestration Progress</p>
            <ul className="ledger-steps">
              <li className={`ledger-step ${getStepStatus("preparing", progressStep)}`}>
                <span className="step-icon"></span>
                <span className="step-text">Assembling local workspace context</span>
              </li>
              <li className={`ledger-step ${getStepStatus("retrieving", progressStep)}`}>
                <span className="step-icon"></span>
                <span className="step-text">Executing sidecar vector retrieval (RAG)</span>
              </li>
              <li className={`ledger-step ${getStepStatus("thinking", progressStep)}`}>
                <span className="step-icon"></span>
                <span className="step-text">Formulating AI model response (Inference)</span>
              </li>
              <li className={`ledger-step ${getStepStatus("processing", progressStep)}`}>
                <span className="step-icon"></span>
                <span className="step-text">Synthesizing search-and-replace blocks</span>
              </li>
              <li className={`ledger-step ${getStepStatus("refreshing", progressStep)}`}>
                <span className="step-icon"></span>
                <span className="step-text">Synchronizing user platform credits</span>
              </li>
            </ul>
          </div>
        )}

        {contextMatches && contextMatches.length > 0 && (
          <div className="context-reference-audit">
            <details className="context-details" open={false}>
              <summary className="context-summary">
                <span>🔍 Context Reference Audit ({contextMatches.length} references)</span>
              </summary>
              <div className="context-content">
                <p className="context-intro">The following codebase files and sections were referenced to answer your request:</p>
                <ul className="context-list">
                  {contextMatches.map((m, idx) => (
                    <li key={`${m.file}-${idx}`} className="context-item">
                      <span className="file-icon">📄</span>
                      <span className="file-path">{m.file}</span>
                      {m.score !== undefined && (
                        <span className="match-score">{(m.score * 100).toFixed(0)}% match</span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            </details>
          </div>
        )}

        {pendingEdit ? (
          <div className="code-edit-card">
            <p className="edit-card-title">✏️ Proposed Code Change</p>
            <p className="edit-card-desc">{pendingEdit.description}</p>
            
            {(pendingEdit.search || pendingEdit.replace) && (
              <div className="diff-view">
                {pendingEdit.search && pendingEdit.search.split("\n").map((line, idx) => (
                  <div key={`rem-${idx}`} className="diff-line removed">
                    <span className="diff-indicator">-</span>
                    <code className="diff-code">{line || " "}</code>
                  </div>
                ))}
                {pendingEdit.replace && pendingEdit.replace.split("\n").map((line, idx) => (
                  <div key={`add-${idx}`} className="diff-line added">
                    <span className="diff-indicator">+</span>
                    <code className="diff-code">{line || " "}</code>
                  </div>
                ))}
              </div>
            )}

            <button type="button" className="btn btn-primary" onClick={onApplyEdit}>
              Apply to editor
            </button>
          </div>
        ) : null}

        {validationErrors && validationErrors.length > 0 && (
          <div className="validation-error-card">
            <p className="validation-card-title">⚠️ Applied Edit Introduced Errors</p>
            <ul className="validation-errors-list">
              {validationErrors.map((err, idx) => (
                <li key={idx} className="validation-error-item">
                  <span className="error-badge">Line {err.line}</span>
                  <span className="error-text">{err.message}</span>
                </li>
              ))}
            </ul>
            {onFixErrors && (
              <button type="button" className="btn btn-warning" onClick={onFixErrors} style={{ marginTop: 8 }}>
                🔧 Auto-Fix with AI
              </button>
            )}
          </div>
        )}
      </div>

      {/* Floating Modern Unified Composer Container */}
      <div style={{ padding: "12px", background: "var(--bg-base)", borderTop: "1px solid var(--border-subtle)", flexShrink: 0 }}>
        <div
          className="chat-composer-container"
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "12px",
            display: "flex",
            flexDirection: "column",
            padding: "8px 12px",
            gap: "8px",
            boxShadow: "var(--shadow-sm)",
            transition: "border-color 0.16s ease, box-shadow 0.16s ease",
          }}
          onFocusCapture={(e) => {
            e.currentTarget.style.borderColor = "var(--accent)";
            e.currentTarget.style.boxShadow = "0 0 0 2px rgba(92, 108, 240, 0.15)";
          }}
          onBlurCapture={(e) => {
            e.currentTarget.style.borderColor = "var(--border-subtle)";
            e.currentTarget.style.boxShadow = "none";
          }}
        >
          {/* 1. Textarea */}
          <textarea
            ref={textareaRef}
            value={input}
            placeholder={disabled ? "Waiting for engine readiness..." : "Describe changes or ask for help..."}
            onChange={(e) => onInputChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                onSend();
              }
            }}
            disabled={disabled}
            className={disabled ? "disabled" : ""}
            style={{
              width: "100%",
              background: "transparent",
              border: "none",
              outline: "none",
              color: "var(--text-primary)",
              fontSize: "0.88rem",
              lineHeight: "1.45",
              resize: "none",
              padding: "4px 0",
              minHeight: "36px",
            }}
          />

          {/* 2. Reference Chips (Inline inside the composer) */}
          {uploadedReferences.length > 0 && (
            <div className="uploaded-references-chips-container" style={{ display: "flex", flexWrap: "wrap", gap: "6px", margin: "4px 0" }}>
              {uploadedReferences.map((ref) => (
                <span
                  key={ref}
                  className="reference-chip"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    backgroundColor: "rgba(255,255,255,0.06)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    color: "var(--text-secondary)",
                    fontSize: "0.72rem",
                    padding: "3px 8px",
                    borderRadius: "8px",
                    gap: "6px",
                  }}
                >
                  📄 {ref}
                  {onDeleteReference && (
                    <button
                      type="button"
                      onClick={() => onDeleteReference(ref)}
                      style={{
                        background: "none",
                        border: "none",
                        color: "var(--text-tertiary)",
                        cursor: "pointer",
                        padding: 0,
                        fontSize: "0.9rem",
                        fontWeight: "bold",
                        lineHeight: "1",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                      title="Remove reference file"
                    >
                      &times;
                    </button>
                  )}
                </span>
              ))}
            </div>
          )}

          {/* 3. Controls & Action Row */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: "4px", borderTop: "1px solid rgba(255, 255, 255, 0.03)" }}>
            {/* Left Controls: Selectors + Paperclip */}
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              {/* Attachment Button */}
              {onUploadFile && (
                <>
                  <input
                    type="file"
                    id="chat-reference-upload"
                    style={{ display: "none" }}
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) {
                        onUploadFile(file);
                        e.target.value = "";
                      }
                    }}
                  />
                  <button
                    type="button"
                    title="Upload reference document"
                    onClick={() => document.getElementById("chat-reference-upload")?.click()}
                    style={{
                      background: "none",
                      border: "none",
                      color: "var(--text-secondary)",
                      fontSize: "1.05rem",
                      cursor: "pointer",
                      padding: "4px",
                      borderRadius: "6px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      transition: "background 0.12s ease, color 0.12s ease",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = "rgba(255, 255, 255, 0.05)";
                      e.currentTarget.style.color = "var(--text-primary)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = "none";
                      e.currentTarget.style.color = "var(--text-secondary)";
                    }}
                    disabled={disabled || busy}
                  >
                    📎
                  </button>
                </>
              )}

              {/* Model Dropdown Pill */}
              {useLocalLlm ? (
                <select
                  value={localLlmModel}
                  onChange={(e) => onLocalLlmModelChange?.(e.target.value)}
                  style={{
                    background: "rgba(255, 255, 255, 0.04)",
                    border: "1px solid rgba(255, 255, 255, 0.06)",
                    borderRadius: "6px",
                    color: "var(--text-secondary)",
                    padding: "3px 6px",
                    fontSize: "0.7rem",
                    outline: "none",
                    cursor: "pointer",
                    maxWidth: "140px",
                    textOverflow: "ellipsis",
                  }}
                >
                  <option value="llm-qwen-coder-3b-q4" disabled={!downloadedModels["llm-qwen-coder-3b-q4"]} style={{ color: downloadedModels["llm-qwen-coder-3b-q4"] ? "var(--text-primary)" : "#5f697a" }}>
                    Qwen 3B {downloadedModels["llm-qwen-coder-3b-q4"] ? "✓" : "(Not Downloaded)"}
                  </option>
                  <option value="llm-qwen-coder-7b-q4" disabled={!downloadedModels["llm-qwen-coder-7b-q4"]} style={{ color: downloadedModels["llm-qwen-coder-7b-q4"] ? "var(--text-primary)" : "#5f697a" }}>
                    Qwen 7B {downloadedModels["llm-qwen-coder-7b-q4"] ? "✓" : "(Not Downloaded)"}
                  </option>
                  <option value="llm-llama-8b-q4" disabled={!downloadedModels["llm-llama-8b-q4"]} style={{ color: downloadedModels["llm-llama-8b-q4"] ? "var(--text-primary)" : "#5f697a" }}>
                    Llama 8B {downloadedModels["llm-llama-8b-q4"] ? "✓" : "(Not Downloaded)"}
                  </option>
                </select>
              ) : (
                <select
                  value={externalLlmModel}
                  onChange={(e) => onExternalLlmModelChange?.(e.target.value)}
                  style={{
                    background: "rgba(255, 255, 255, 0.04)",
                    border: "1px solid rgba(255, 255, 255, 0.06)",
                    borderRadius: "6px",
                    color: "var(--text-secondary)",
                    padding: "3px 6px",
                    fontSize: "0.7rem",
                    outline: "none",
                    cursor: "pointer",
                    maxWidth: "140px",
                  }}
                >
                  <option value="gpt-4o-mini">GPT-4o mini</option>
                  <option value="gpt-4o">GPT-4o</option>
                  <option value="claude-3-5-sonnet">Claude 3.5</option>
                  <option value="deepseek-r1" disabled style={{ color: "#5f697a" }}>
                    DeepSeek-R1 (N/A)
                  </option>
                </select>
              )}

              {/* Reasoning Dropdown Pill */}
              <select
                value={reasoningLevel}
                onChange={(e) => onReasoningLevelChange?.(e.target.value)}
                style={{
                  background: "rgba(255, 255, 255, 0.04)",
                  border: "1px solid rgba(255, 255, 255, 0.06)",
                  borderRadius: "6px",
                  color: "var(--text-secondary)",
                  padding: "3px 6px",
                  fontSize: "0.7rem",
                  outline: "none",
                  cursor: "pointer",
                  width: "90px",
                }}
              >
                <option value="low">Reason: Low</option>
                <option value="medium">Reason: Med</option>
                <option value="high">Reason: High</option>
              </select>
            </div>

            {/* Right Controls: Audio + Send */}
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              {onGenerateAudio && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={onGenerateAudio}
                  title="Generate Audio (TTS)"
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--text-secondary)",
                    fontSize: "1rem",
                    cursor: "pointer",
                    padding: "4px",
                    borderRadius: "6px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    transition: "background 0.12s ease, color 0.12s ease",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = "rgba(255, 255, 255, 0.05)";
                    e.currentTarget.style.color = "var(--text-primary)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "none";
                    e.currentTarget.style.color = "var(--text-secondary)";
                  }}
                >
                  🔊
                </button>
              )}

              <button
                type="button"
                disabled={busy || disabled || !input.trim()}
                onClick={onSend}
                style={{
                  background: input.trim() ? "var(--accent)" : "rgba(255, 255, 255, 0.04)",
                  border: "none",
                  color: input.trim() ? "white" : "var(--text-muted)",
                  padding: "6px 14px",
                  borderRadius: "8px",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  cursor: input.trim() ? "pointer" : "default",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  transition: "all 0.12s ease",
                }}
                onMouseEnter={(e) => {
                  if (input.trim() && !disabled && !busy) {
                    e.currentTarget.style.background = "var(--accent-hover)";
                  }
                }}
                onMouseLeave={(e) => {
                  if (input.trim() && !disabled && !busy) {
                    e.currentTarget.style.background = "var(--accent)";
                  }
                }}
              >
                Send
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}