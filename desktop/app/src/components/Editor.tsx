import Editor, { type OnMount } from "@monaco-editor/react";
import type { editor } from "monaco-editor";
import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";

import type { LintDiagnostic } from "../api/types";

export interface CodeEditorHandle {
  jumpToLine: (line: number) => void;
}

interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  diagnostics: LintDiagnostic[];
  language?: "python" | "markdown" | "json";
  readOnly?: boolean;
}

export const CodeEditor = forwardRef<CodeEditorHandle, CodeEditorProps>(
  function CodeEditor({ value, onChange, diagnostics, language = "python", readOnly = false }, ref) {
    const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
    const monacoRef = useRef<typeof import("monaco-editor") | null>(null);

    useImperativeHandle(ref, () => ({
      jumpToLine(line: number) {
        const instance = editorRef.current;
        if (!instance) return;
        instance.revealLineInCenter(line);
        instance.setPosition({ lineNumber: line, column: 1 });
        instance.focus();
      },
    }));

    useEffect(() => {
      const monaco = monacoRef.current;
      const instance = editorRef.current;
      const model = instance?.getModel();
      if (!monaco || !model) return;

      const markers: editor.IMarkerData[] = diagnostics.map((d) => ({
        startLineNumber: Math.max(1, d.line),
        startColumn: Math.max(1, d.col),
        endLineNumber: Math.max(1, d.line),
        endColumn: Math.max(1, d.col + 1),
        message: d.message,
        severity:
          d.severity === "error"
            ? monaco.MarkerSeverity.Error
            : monaco.MarkerSeverity.Warning,
      }));
      monaco.editor.setModelMarkers(model, "matemium-lint", markers);
    }, [diagnostics]);

    const handleMount: OnMount = (instance, monaco) => {
      editorRef.current = instance;
      monacoRef.current = monaco;
    };

    return (
      <div className="editor-wrap">
        <Editor
          height="100%"
          language={language}
          theme="vs-dark"
          value={value}
          onChange={(next) => onChange(next ?? "")}
          onMount={handleMount}
          options={{
            minimap: { enabled: false },
            fontSize: 13,
            lineNumbers: "on",
            scrollBeyondLastLine: false,
            automaticLayout: true,
            padding: { top: 8 },
            readOnly,
          }}
        />
      </div>
    );
  },
);
