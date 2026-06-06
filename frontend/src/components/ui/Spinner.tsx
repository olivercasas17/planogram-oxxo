export type SpinnerSize = "sm" | "md" | "lg";

interface SpinnerProps {
  size?: SpinnerSize;
  className?: string;
  label?: string;
}

export function Spinner({ size = "md", className = "", label = "Cargando…" }: SpinnerProps) {
  return (
    <span className={`spinner spinner-${size} ${className}`} role="status" aria-label={label} />
  );
}
