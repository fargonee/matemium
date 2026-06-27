import type { HTMLAttributes } from "react";

export function Spinner({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={["inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent", className].join(" ")}
      {...props}
    />
  );
}
