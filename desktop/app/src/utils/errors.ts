export function formatError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === "string") {
    return error;
  }
  return JSON.stringify(error);
}

export function tailLines(text: string, count = 50): string {
  const lines = text.trim().split("\n");
  if (lines.length <= count) {
    return lines.join("\n");
  }
  return lines.slice(-count).join("\n");
}