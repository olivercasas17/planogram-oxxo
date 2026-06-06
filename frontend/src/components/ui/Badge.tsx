import type { ReactNode } from "react";

export type BadgeVariant = "success" | "warning" | "error" | "info" | "demo";

interface BadgeProps {
  variant: BadgeVariant;
  children: ReactNode;
  className?: string;
}

const LABELS: Record<BadgeVariant, string> = {
  success: "success",
  warning: "warning",
  error: "error",
  info: "info",
  demo: "demo mode — toy solver",
};

export function Badge({ variant, children, className = "" }: BadgeProps) {
  return (
    <span
      className={`badge badge-${variant} ${className}`}
      title={variant === "demo" ? LABELS.demo : undefined}
    >
      {children}
    </span>
  );
}
