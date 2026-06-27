import type { ReactNode } from "react";

interface ErrorAlertProps {
  children: ReactNode;
  onRetry?: () => void;
}

export function ErrorAlert({ children, onRetry }: ErrorAlertProps) {
  return (
    <div className="rounded-lg border border-red-500/40 bg-red-500/5 p-4 text-sm text-red-300">
      <p>{children}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 text-xs underline hover:no-underline"
        >
          Try again
        </button>
      ) : null}
    </div>
  );
}
