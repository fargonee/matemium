import { useCallback, useEffect, useRef, useState } from "react";

interface TerminalOutputProps {
  text: string;
}

function readTerminalSelection(root: HTMLElement): string | null {
  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0 || selection.isCollapsed) return null;

  const anchor = selection.anchorNode;
  const focus = selection.focusNode;
  if (!anchor || !focus || !root.contains(anchor) || !root.contains(focus)) return null;

  const value = selection.toString();
  return value.trim() ? value : null;
}

async function writeClipboard(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text);
    return;
  } catch {
    // Fall back for environments where async clipboard is blocked.
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  textarea.style.top = "0";
  document.body.appendChild(textarea);
  textarea.select();
  try {
    document.execCommand("copy");
  } finally {
    document.body.removeChild(textarea);
  }
}

export function TerminalOutput({ text }: TerminalOutputProps) {
  const rootRef = useRef<HTMLDivElement>(null);

  const [copied, setCopied] = useState(false);
  const copiedTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const lastToast = useRef("");

  const showCopied = useCallback((value: string) => {
    if (value === lastToast.current) return;
    lastToast.current = value;
    setCopied(true);
    if (copiedTimer.current) clearTimeout(copiedTimer.current);
    copiedTimer.current = setTimeout(() => {
      setCopied(false);
      lastToast.current = "";
    }, 1500);
  }, []);

  const handleSelection = useCallback(async () => {
    const root = rootRef.current;
    if (!root) return;

    const value = readTerminalSelection(root);
    if (!value) return;

    try {
      await writeClipboard(value);
    } catch {
      // Still show feedback when text was selected even if clipboard is unavailable.
    }

    showCopied(value);
  }, [showCopied]);

  useEffect(() => {
    return () => {
      if (copiedTimer.current) clearTimeout(copiedTimer.current);
    };
  }, []);

  const scheduleSelectionCheck = useCallback(() => {
    window.requestAnimationFrame(() => {
      window.setTimeout(() => {
        void handleSelection();
      }, 0);
    });
  }, [handleSelection]);

  return (
    <div className="terminal-output" ref={rootRef}>
      <pre
        className="output-log"
        onMouseUp={scheduleSelectionCheck}
        onKeyUp={scheduleSelectionCheck}
      >
        {text || "No output yet"}
      </pre>
      {copied ? (
        <div className="terminal-copied" role="status" aria-live="polite">
          Copied
        </div>
      ) : null}
    </div>
  );
}