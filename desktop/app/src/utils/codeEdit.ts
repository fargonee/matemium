import type { CodeEdit } from "../api/types";

export function applyCodeEdit(content: string, edit: CodeEdit): string {
  if (edit.full_file) {
    return edit.full_file;
  }
  if (edit.search != null && edit.replace != null) {
    if (!content.includes(edit.search)) {
      throw new Error("Suggested search block was not found in the current file.");
    }
    return content.replace(edit.search, edit.replace);
  }
  throw new Error("Code edit has no applicable full_file or search/replace.");
}