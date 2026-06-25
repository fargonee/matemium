import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  highlighted?: boolean;
}

export function Card({ children, className = "", highlighted }: CardProps) {
  return (
    <div
      className={[
        "rounded-[18px] border bg-bg-card p-6",
        highlighted ? "border-accent shadow-[0_0_0_1px_rgba(45,91,255,0.2)]" : "border-border",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {children}
    </div>
  );
}