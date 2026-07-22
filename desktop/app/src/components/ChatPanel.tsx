import { useEffect, useRef, useState } from "react";
import type { AgentTraceEntry, ChatMessage, CodeEdit, Conversation, ProviderModel } from "../api/types";
import { formatModelMeta, modelDisplayName } from "../modelCatalog";

interface ChatPanelProps {
  messages: ChatMessage[];
  pendingEdit: CodeEdit | null;
  input: string;
  busy: boolean;
  contextMatches?: Array<{ file: string; score?: number }>;
  validationErrors?: Array<{ line: number; message: string }>;
  onFixErrors?: () => void;
  onInputChange: (value: string) => void;
  onSend: () => void;
  onCancel?: () => void;
  canCancel?: boolean;
  onApplyEdit: () => void;
  // LLM status from profile (provider/mode visibility)
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
  externalModelOptions?: ProviderModel[];
  onManageExternalModels?: () => void;
  openRouterFreeDisabledUntil?: string | null;
  reasoningLevel?: string;
  onReasoningLevelChange?: (val: string) => void;
  downloadedModels?: Record<string, boolean>;
  // Conversation management
  conversations?: Conversation[];
  activeConversationId?: string | null;
  onSelectConversation?: (id: string) => void;
  onNewConversation?: () => void;
  onDeleteConversation?: (id: string) => void;
  autonomousEnabled?: boolean;
  onToggleAutonomous?: (enabled: boolean) => void;
  autonomousUnavailableReason?: string;
  configuredRuntime?: string;
  responseMetadata?: {
    runtime: string;
    model: string;
    provider: string;
    billingMode: string;
    requestId: string;
    stub: boolean;
    trace: AgentTraceEntry[];
  };
  liveAgentTrace?: AgentTraceEntry[];
}

export function ChatPanel({
  messages,
  pendingEdit,
  input,
  busy,
  contextMatches,
  validationErrors,
  onFixErrors,
  onInputChange,
  onSend,
  onCancel,
  canCancel = false,
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
  externalLlmModel = "openai/gpt-4o-mini",
  onExternalLlmModelChange,
  externalModelOptions = [],
  onManageExternalModels,
  openRouterFreeDisabledUntil,
  reasoningLevel = "low",
  onReasoningLevelChange,
  downloadedModels = {},
  conversations = [],
  activeConversationId = null,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  autonomousEnabled = false,
  onToggleAutonomous,
  autonomousUnavailableReason,
  configuredRuntime = "aider-v1",
  responseMetadata,
  liveAgentTrace = [],
}: ChatPanelProps) {
  const freeDisabledUntil = openRouterFreeDisabledUntil ? new Date(openRouterFreeDisabledUntil) : null;
  const freeModelDisabled = !!freeDisabledUntil && freeDisabledUntil.getTime() > Date.now();
  const freeModelRenewal = freeModelDisabled && freeDisabledUntil
    ? freeDisabledUntil.toLocaleString()
    : null;
  const [popoverOpen, setPopoverOpen] = useState(false);
  const [completedTraceEvents, setCompletedTraceEvents] = useState<AgentTraceEntry[]>([]);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const historyRef = useRef<HTMLDivElement>(null);
  const wasBusyRef = useRef(false);
  const [timerNow, setTimerNow] = useState(() => Date.now());
  const rawTraceEvents = liveAgentTrace.length ? liveAgentTrace : responseMetadata?.trace ?? [];
  const traceEvents = rawTraceEvents.filter((event) => !isHeartbeatEvent(event));
  const archivedTraceEvents = completedTraceEvents.length
    ? completedTraceEvents
    : (responseMetadata?.trace ?? []).filter((event) => !isHeartbeatEvent(event));
  const visibleExternalModels = externalModelOptions.length
    ? externalModelOptions
    : [{ id: externalLlmModel, name: modelDisplayName(externalLlmModel), provider: "openrouter" }];
  const selectedExternalModel = visibleExternalModels.some((model) => model.id === externalLlmModel)
    ? externalLlmModel
    : visibleExternalModels[0]?.id ?? externalLlmModel;

  useEffect(() => {
    if (!useLocalLlm && selectedExternalModel !== externalLlmModel) {
      onExternalLlmModelChange?.(selectedExternalModel);
    }
  }, [externalLlmModel, onExternalLlmModelChange, selectedExternalModel, useLocalLlm]);

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

  useEffect(() => {
    const history = historyRef.current;
    if (!history) return;

    const frame = window.requestAnimationFrame(() => {
      history.scrollTo({ top: history.scrollHeight, behavior: "smooth" });
    });

    return () => window.cancelAnimationFrame(frame);
  }, [
    messages.length,
    traceEvents.length,
    archivedTraceEvents.length,
    busy,
    pendingEdit,
    contextMatches?.length,
    validationErrors?.length,
  ]);

  useEffect(() => {
    if (busy && !wasBusyRef.current) {
      setCompletedTraceEvents([]);
    }

    if (traceEvents.length > 0) {
      setCompletedTraceEvents(traceEvents);
    }

    wasBusyRef.current = busy;
  }, [busy, traceEvents]);

  useEffect(() => {
    setCompletedTraceEvents([]);
  }, [activeConversationId]);

  useEffect(() => {
    if (!busy) {
      setTimerNow(Date.now());
      return;
    }
    const timer = window.setInterval(() => setTimerNow(Date.now()), 250);
    return () => window.clearInterval(timer);
  }, [busy]);

  interface ToolCallData {
    name: string;
    args: string;
  }

  function parseResponseBlocks(content: string): { 
    toolCall: ToolCallData | null;
    toolOutput: string | null;
    cleanContent: string;
  } {
    let toolCall: ToolCallData | null = null;
    let toolOutput: string | null = null;
    let cleanContent = content;

    const thoughtRegex = /<(?:thought|reasoning)>([\s\S]*?)<\/(?:thought|reasoning)>/gi;
    const thoughtMatch = thoughtRegex.exec(content);
    if (thoughtMatch) {
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
      toolCall, 
      toolOutput,
      cleanContent: cleanContent.trim() 
    };
  }

  function safeDiagnostic(value: string): string {
    const redacted = value
      .replace(/(authorization\s*[:=]\s*bearer\s+)[^\s]+/gi, "$1[REDACTED]")
      .replace(/((?:api[_-]?key|token|secret|password)\s*[:=]\s*)[^\s,;}]+/gi, "$1[REDACTED]");
    return redacted.length > 4096 ? `${redacted.slice(0, 4096)}\n… output truncated` : redacted;
  }

  function traceTone(event: AgentTraceEntry): "ok" | "warn" | "error" | "info" {
    const type = event.type.toLowerCase();
    const details = JSON.stringify(event.details ?? {}).toLowerCase();
    if (type.includes("approval") || type.includes("blocked") || type.includes("budget")) return "warn";
    if (type.includes("fail") || type.includes("error") || details.includes("failed")) return "error";
    if (type.includes("complete") || type.includes("verify") || details.includes("passed")) return "ok";
    return "info";
  }

  function isHeartbeatEvent(event: AgentTraceEntry): boolean {
    return event.type === "agent_waiting";
  }

  function traceLabel(type: string): string {
    return type.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  function eventTimestamp(event: AgentTraceEntry): number | null {
    return typeof event.timestamp_ms === "number" ? event.timestamp_ms : null;
  }

  function formatTraceDuration(ms: number | null): string | null {
    if (ms === null || !Number.isFinite(ms) || ms < 0) return null;
    if (ms < 1000) return `${Math.max(1, Math.round(ms))}ms`;
    const seconds = ms / 1000;
    if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 1 : 0)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainder = Math.round(seconds % 60);
    return `${minutes}m ${remainder.toString().padStart(2, "0")}s`;
  }

  function toolName(event: AgentTraceEntry): string {
    const detailsTool = event.details?.tool;
    return typeof detailsTool === "string" && detailsTool.trim() ? detailsTool : "workspace";
  }

  function traceDurationMs(events: AgentTraceEntry[], event: AgentTraceEntry, index: number): number | null {
    const start = eventTimestamp(event);
    if (start === null) return null;

    if (event.type === "model_request_started") {
      const next = events.slice(index + 1).find((candidate) =>
        candidate.type === "model_request_completed" || candidate.type === "model_request_failed"
      );
      return (next ? eventTimestamp(next) ?? timerNow : timerNow) - start;
    }

    if (event.type === "action_started") {
      const name = toolName(event);
      const next = events.slice(index + 1).find((candidate) =>
        (candidate.type === "action_completed" || candidate.type === "action_failed") && toolName(candidate) === name
      );
      return (next ? eventTimestamp(next) ?? timerNow : timerNow) - start;
    }

    const previousStarted = [...events.slice(0, index)].reverse().find((candidate) => {
      if (event.type === "model_request_completed" || event.type === "model_request_failed") {
        return candidate.type === "model_request_started";
      }
      if (event.type === "action_completed" || event.type === "action_failed") {
        return candidate.type === "action_started" && toolName(candidate) === toolName(event);
      }
      return false;
    });
    const previousStart = previousStarted ? eventTimestamp(previousStarted) : null;
    return previousStart === null ? null : start - previousStart;
  }

  function traceTimingSummary(events: AgentTraceEntry[]): {
    total: string | null;
    model: string | null;
    tools: string | null;
    count: number;
  } {
    const stamped = events.filter((event) => eventTimestamp(event) !== null);
    if (stamped.length === 0) return { total: null, model: null, tools: null, count: events.length };

    const first = eventTimestamp(stamped[0]) ?? timerNow;
    const terminal = [...stamped].reverse().find((event) => event.type === "terminal");
    const last = eventTimestamp(terminal ?? stamped[stamped.length - 1]) ?? timerNow;
    let modelMs = 0;
    let toolMs = 0;
    events.forEach((event, index) => {
      const duration = traceDurationMs(events, event, index);
      if (duration === null) return;
      if (event.type === "model_request_started") modelMs += duration;
      if (event.type === "action_started") toolMs += duration;
    });

    return {
      total: formatTraceDuration((busy ? timerNow : last) - first),
      model: modelMs > 0 ? formatTraceDuration(modelMs) : null,
      tools: toolMs > 0 ? formatTraceDuration(toolMs) : null,
      count: events.length,
    };
  }

  function compactPrompt(value: string): string {
    const cleaned = value
      .replace(/^### Active Reference Attachments:[\s\S]*### User Question:/i, "")
      .replace(/\s+/g, " ")
      .trim();
    return cleaned.length > 140 ? `${cleaned.slice(0, 137)}...` : cleaned;
  }

  function latestUserPrompt(): string | null {
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const message = messages[index];
      if (message.role === "user" && message.content.trim()) {
        return compactPrompt(message.content);
      }
    }
    return null;
  }

  function hasAssistantResponseAfterLatestUser(): boolean {
    let sawAssistant = false;
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const message = messages[index];
      if (message.role === "assistant") sawAssistant = true;
      if (message.role === "user") return sawAssistant;
    }
    return false;
  }

  function fallbackCompletionTrace(): AgentTraceEntry[] {
    if (busy || !hasAssistantResponseAfterLatestUser()) return [];

    const fallback: AgentTraceEntry[] = [
      {
        type: "request_understood",
        summary: latestUserPrompt()
          ? `User request captured: ${latestUserPrompt()}`
          : "User request captured.",
        sequence: 1,
      },
    ];

    if (contextMatches && contextMatches.length > 0) {
      fallback.push({
        type: "context_referenced",
        summary: `Referenced ${contextMatches.length} workspace item${contextMatches.length === 1 ? "" : "s"}.`,
        details: { files: contextMatches.map((match) => match.file) },
        sequence: fallback.length + 1,
      });
    }

    if (pendingEdit) {
      fallback.push({
        type: "code_edit_prepared",
        summary: pendingEdit.description || "Prepared a code edit for review.",
        sequence: fallback.length + 1,
      });
    }

    if (responseMetadata) {
      fallback.push({
        type: "response_completed",
        summary: `Completed with ${responseMetadata.model} using ${responseMetadata.billingMode} mode.`,
        details: {
          runtime: responseMetadata.runtime,
          provider: responseMetadata.provider,
          request_id: responseMetadata.requestId,
          stub: responseMetadata.stub,
        },
        sequence: fallback.length + 1,
      });
    } else {
      fallback.push({
        type: "response_completed",
        summary: "Assistant response completed.",
        sequence: fallback.length + 1,
      });
    }

    return fallback;
  }

  function workingNote(): string | null {
    const prompt = latestUserPrompt();
    if (!prompt) return null;

    const latestTrace = traceEvents[traceEvents.length - 1];
    if (busy && latestTrace) {
      return `User asked: ${prompt}. I am now ${traceLabel(latestTrace.type).toLowerCase()}${latestTrace.summary ? `: ${latestTrace.summary}` : "."}`;
    }

    if (busy) {
      return `User asked: ${prompt}. I need to understand the request, gather the relevant project context, make the change, and verify the result.`;
    }

    if (archivedTraceEvents.length > 0) {
      const terminal = [...archivedTraceEvents].reverse().find((event) => event.type === "terminal");
      const outcome = typeof terminal?.details?.outcome === "string" ? terminal.details.outcome : null;
      if (outcome === "finished" || outcome === "completed") {
        return `User asked: ${prompt}. Aider finished the run and kept the action trace available below.`;
      }
      return `User asked: ${prompt}. Aider stopped with status ${outcome ?? "unknown"}; review the action trace below.`;
    }

    return null;
  }

  const activeConversation = conversations.find((c) => c.id === activeConversationId);
  const activeTitle = activeConversation ? activeConversation.title : "AI Assistant";
  const visibleWorkingNote = workingNote();
  const completionTraceEvents = archivedTraceEvents.length ? archivedTraceEvents : fallbackCompletionTrace();
  const liveTiming = traceTimingSummary(traceEvents);
  const completionTiming = traceTimingSummary(completionTraceEvents);

  return (
    <div className="chat-panel-shell">
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

        <div style={{ display: "flex", gap: "4px", alignItems: "center", textTransform: "none" }}>
          {onToggleAutonomous && (
            <div style={{ display: "flex", gap: 2, padding: 2, border: "1px solid var(--border-subtle)", borderRadius: 6 }} aria-label="Assistant execution mode">
              <button type="button" aria-pressed={autonomousEnabled} onClick={() => onToggleAutonomous(true)} style={{ padding: "2px 6px", fontSize: "0.62rem", border: 0, borderRadius: 4, cursor: "pointer", color: autonomousEnabled ? "white" : "var(--text-secondary)", background: autonomousEnabled ? "var(--accent)" : "transparent" }}>Agent</button>
              <button type="button" aria-pressed={!autonomousEnabled} onClick={() => onToggleAutonomous(false)} style={{ padding: "2px 6px", fontSize: "0.62rem", border: 0, borderRadius: 4, cursor: "pointer", color: !autonomousEnabled ? "white" : "var(--text-secondary)", background: !autonomousEnabled ? "var(--accent)" : "transparent" }}>Ask</button>
            </div>
          )}
        {onToggleLocalLlm && (
          <div style={{ display: "flex", gap: "2px", background: "var(--bg-elevated)", padding: "2px", borderRadius: "6px", border: "1px solid var(--border-subtle)" }}>
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
        </div>
      </h2>

      <div role="status" style={{ padding: "7px 12px", borderBottom: "1px solid var(--border-subtle)", background: autonomousEnabled ? "rgba(234, 179, 8, 0.07)" : "rgba(59, 130, 246, 0.05)", fontSize: "0.67rem", color: "var(--text-secondary)", lineHeight: 1.4 }}>
        <strong style={{ color: "var(--text-primary)" }}>{autonomousEnabled ? "Autonomous agent" : "Single-turn assistant"}</strong>
        {autonomousUnavailableReason && <> · {autonomousUnavailableReason}</>}
        {autonomousEnabled && <> · runtime <code>{configuredRuntime}</code> · Aider workspace agent</>}
        {responseMetadata && (
          <details style={{ marginTop: 3 }}>
            <summary style={{ cursor: "pointer" }}>Last response: {responseMetadata.model} · {responseMetadata.billingMode}{responseMetadata.stub ? " · stub" : ""}</summary>
            <div>Runtime: <code>{responseMetadata.runtime}</code></div>
            <div>Provider: {responseMetadata.provider}</div>
            <div>Request: <code>{responseMetadata.requestId}</code></div>
            <div>{responseMetadata.billingMode === "local" ? "Runs locally." : "Uses your connected provider account."}</div>
          </details>
        )}
      </div>

      {/* Main Scrollable History */}
      <div className="chat-history" ref={historyRef}>
        {messages.length === 0 ? (
          <div style={{ color: "#7c8595", fontSize: "0.8rem" }}>
            Ask the assistant to refine or extend the scene...
          </div>
        ) : (
          messages.map((message, index) => {
            if (message.role === "assistant") {
              const { toolCall, toolOutput, cleanContent } = parseResponseBlocks(message.content);
              return (
                <div
                  key={`${message.role}-${index}`}
                  className={`chat-bubble ${message.role}`}
                >
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
                      <pre style={{ margin: 0, overflowX: "auto", color: "var(--text-muted)", whiteSpace: "pre-wrap" }}>{safeDiagnostic(toolCall.args)}</pre>
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
                      }}>{safeDiagnostic(toolOutput)}</pre>
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

        {busy && traceEvents.length === 0 && (
          <div className="chat-bubble assistant assistant-thinking" role="status" aria-live="polite">
            <span className="agent-progress-spinner" aria-hidden="true" />
            <span>Thinking...</span>
          </div>
        )}

        {visibleWorkingNote && (
          <div className={`agent-working-note ${busy ? "active" : ""}`} role="status" aria-live="polite">
            {busy && <span className="agent-progress-spinner" aria-hidden="true" />}
            <div>
              <strong>Working note</strong>
              <p>{visibleWorkingNote}</p>
            </div>
          </div>
        )}

        {traceEvents.length > 0 && busy && (
          <div className="agent-inline-activity-list" aria-label="Live agent activity">
            <div className="agent-timing-strip" aria-label="Agent timing summary">
              {liveTiming.total && <span>Total <strong>{liveTiming.total}</strong></span>}
              {liveTiming.model && <span>Thinking <strong>{liveTiming.model}</strong></span>}
              {liveTiming.tools && <span>Tools <strong>{liveTiming.tools}</strong></span>}
            </div>
            {traceEvents.map((event, index) => {
              const active = index === traceEvents.length - 1;
              const elapsed = formatTraceDuration(traceDurationMs(traceEvents, event, index));
              return (
                <div key={`${event.sequence ?? index}-${event.type}`} className={`agent-inline-activity ${traceTone(event)} ${active ? "active" : ""}`}>
                  <span className={active ? "agent-progress-spinner" : "agent-inline-dot"} aria-hidden="true" />
                  <div className="agent-inline-copy">
                    <code>{traceLabel(event.type)}</code>
                    <span>{event.summary || "Event recorded"}</span>
                    {elapsed && <span className="agent-duration-pill">{elapsed}</span>}
                  </div>
                  {event.details && Object.keys(event.details).length > 0 && (
                    <details className="agent-activity-details">
                      <summary>Details</summary>
                      <pre>{safeDiagnostic(JSON.stringify(event.details, null, 2))}</pre>
                    </details>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {completionTraceEvents.length > 0 && !busy && (
          <details aria-label="Completed agent activity" className="agent-activity-complete-card">
            <summary className="agent-activity-complete-summary">
              <span className="agent-activity-complete-title">
                <span className="agent-live-dot" />
                <span>
                  <strong>Show action trace</strong>
                  <small>Task complete. Expand to inspect what happened.</small>
                </span>
              </span>
              <span>{completionTiming.total ? `${completionTiming.total} · ` : ""}{completionTraceEvents.length} events</span>
            </summary>
            {(completionTiming.total || completionTiming.model || completionTiming.tools) && (
              <div className="agent-timing-strip complete" aria-label="Completed agent timing summary">
                {completionTiming.total && <span>Total <strong>{completionTiming.total}</strong></span>}
                {completionTiming.model && <span>Thinking <strong>{completionTiming.model}</strong></span>}
                {completionTiming.tools && <span>Tools <strong>{completionTiming.tools}</strong></span>}
              </div>
            )}
            <ol className="agent-activity-list">
              {completionTraceEvents.map((event, index) => {
                const elapsed = formatTraceDuration(traceDurationMs(completionTraceEvents, event, index));
                return (
                  <li key={`${event.sequence ?? index}-${event.type}`} className={`agent-activity-item ${traceTone(event)}`}>
                    <div className="agent-activity-copy">
                      <code>{traceLabel(event.type)}</code>
                      <span>{event.summary || "Event recorded"}</span>
                      {elapsed && <span className="agent-duration-pill">{elapsed}</span>}
                    </div>
                    {event.details && Object.keys(event.details).length > 0 && (
                      <details className="agent-activity-details">
                        <summary>Details</summary>
                        <pre>{safeDiagnostic(JSON.stringify(event.details, null, 2))}</pre>
                      </details>
                    )}
                  </li>
                );
              })}
            </ol>
          </details>
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
                  value={selectedExternalModel}
                  onChange={(e) => {
                    const next = e.target.value;
                    if (next === "__manage_models__") {
                      onManageExternalModels?.();
                      return;
                    }
                    onExternalLlmModelChange?.(next);
                  }}
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
                  {visibleExternalModels.map((model) => {
                    const isFreeModel = model.id === "openrouter/free" || model.id.endsWith(":free");
                    const disabledByQuota = isFreeModel && freeModelDisabled;
                    const meta = formatModelMeta(model);
                    return (
                      <option key={model.id} value={model.id} disabled={disabledByQuota}>
                        {disabledByQuota
                          ? `${model.name} (renews ${freeModelRenewal})`
                          : `${model.name}${meta ? ` · ${meta}` : ""}`}
                      </option>
                    );
                  })}
                  {onManageExternalModels && <option value="__manage_models__">Manage models...</option>}
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

              {busy && canCancel && onCancel ? (
                <button
                  type="button"
                  onClick={onCancel}
                  title="Stop the current chat task"
                  style={{
                    background: "var(--error-subtle)",
                    border: "1px solid var(--error)",
                    color: "var(--error)",
                    padding: "6px 12px",
                    borderRadius: "8px",
                    fontSize: "0.75rem",
                    fontWeight: 700,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    transition: "all 0.12s ease",
                  }}
                >
                  Stop
                </button>
              ) : (
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
                  {busy ? (
                    <>
                      <span className="send-button-spinner" aria-hidden="true" />
                      <span>Sending</span>
                    </>
                  ) : (
                    "Send"
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
