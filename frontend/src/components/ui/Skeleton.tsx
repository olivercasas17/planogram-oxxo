import type { HTMLAttributes } from "react";

interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  width?: string | number;
  height?: string | number;
}

export function Skeleton({ width, height, className = "", style, ...props }: SkeletonProps) {
  return (
    <div
      className={`skeleton ${className}`}
      style={{
        width: typeof width === "number" ? `${width}px` : width,
        height: typeof height === "number" ? `${height}px` : height,
        ...style,
      }}
      aria-busy="true"
      aria-label="Cargando…"
      {...props}
    />
  );
}

/** Preset: single line of text */
Skeleton.Line = function SkeletonLine({
  width = "100%",
  className = "",
}: {
  width?: string | number;
  className?: string;
}) {
  return <Skeleton width={width} height={14} className={className} />;
};

/** Preset: full block (card, table row, etc.) */
Skeleton.Block = function SkeletonBlock({
  rows = 3,
  className = "",
}: {
  rows?: number;
  className?: string;
}) {
  return (
    <div className={`flex flex-col gap-3 ${className}`}>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} height={14} width={i === rows - 1 ? "60%" : "100%"} />
      ))}
    </div>
  );
};
