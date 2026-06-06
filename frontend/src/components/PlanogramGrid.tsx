import { useState } from "react";
import type { ProductoResult } from "../types/api";

/* ── Types ─────────────────────────────────────────────────────────────────── */

interface PlanogramGridProps {
  results: ProductoResult[];
  disenoReferencia?: string;
  totalWidth?: number;
  shelvesPerDoor?: number;
  isLoading?: boolean;
}

interface TooltipState {
  item: ProductoResult;
  x: number;
  y: number;
}

/* ── Height scale ───────────────────────────────────────────────────────────── */

const ALTO_MAX = 37.5;
const PX_MIN   = 55;
const PX_MAX   = 115;

function getShelfPx(altoCm: number): number {
  const ratio = Math.min(altoCm / ALTO_MAX, 1);
  return PX_MIN + (PX_MAX - PX_MIN) * ratio;
}

/* ── Color helpers ──────────────────────────────────────────────────────────── */

function hashName(name: string): number {
  return name.split("").reduce((a, c) => a + c.charCodeAt(0), 0);
}

function getColor(name: string): string {
  return `hsl(${hashName(name) % 360}, 55%, 45%)`;
}

/* ── Tooltip ────────────────────────────────────────────────────────────────── */

function Tooltip({ tip }: { tip: TooltipState }) {
  const item  = tip.item;
  const label = item.item_desc ?? item.planogrupo;
  const W     = 240;
  const left  = tip.x + W + 14 > window.innerWidth ? tip.x - W - 8 : tip.x + 14;

  return (
    <div style={{
      position: "fixed", top: tip.y - 10, left,
      transform: "translateY(-100%)", zIndex: 9999,
      background: "#1a1a1a", border: "1px solid #333",
      borderRadius: 6, padding: "8px 12px",
      fontFamily: "JetBrains Mono, var(--font-mono)", fontSize: 11,
      color: "#e0e0e0", boxShadow: "0 4px 16px rgba(0,0,0,0.5)",
      pointerEvents: "none", width: W, lineHeight: 1.65,
    }}>
      <div style={{ fontWeight: 700, marginBottom: 3, wordBreak: "break-word" }}>{label}</div>
      {item.item     && <div style={{ color: "#888" }}>ITEM: {item.item}</div>}
      {item.upc_cve  && <div style={{ color: "#666" }}>UPC: {item.upc_cve}</div>}
      <div style={{ color: "#888" }}>
        Charola {item.charola} · Pos {item.ubicacion_bandeja}
      </div>
      <div style={{ color: "#888" }}>
        {item.ancho_ocupado_cm} cm ancho
        {item.alto_cm > 0 ? ` · ${item.alto_cm} cm alto` : ""}
        {item.num_frentes > 1 ? ` · ${item.num_frentes} frentes` : ""}
      </div>
      {item.x_inicio_cm != null && item.x_fin_cm != null && (
        <div style={{ color: "#666", fontSize: 10 }}>
          x: {item.x_inicio_cm}–{item.x_fin_cm} cm
        </div>
      )}
    </div>
  );
}

/* ── Product cell ───────────────────────────────────────────────────────────── */

function ProductCell({
  item, totalWidth, shelfAltoCm, onHover, onLeave,
}: {
  item: ProductoResult;
  totalWidth: number;
  shelfAltoCm: number;
  onHover: (item: ProductoResult, e: React.MouseEvent) => void;
  onLeave: () => void;
}) {
  const [hovered, setHovered] = useState(false);

  const label         = item.item_desc ?? item.planogrupo;
  const bg            = getColor(label);
  const widthPct      = Math.min((item.ancho_ocupado_cm / totalWidth) * 100, 100);
  const altoCm        = item.alto_cm ?? 0;
  const productHPct   = shelfAltoCm > 0 && altoCm > 0
    ? Math.min((altoCm / shelfAltoCm) * 100, 100)
    : 100;

  const estPx    = (item.ancho_ocupado_cm / totalWidth) * 200;
  const fontSize = estPx < 20 ? 0 : estPx < 35 ? 8 : 10;
  const isVert   = estPx < 40;

  return (
    <div
      style={{
        width: `${widthPct}%`, minWidth: 12, height: "100%",
        display: "flex", alignItems: "flex-end",
        flexShrink: 1, cursor: "pointer", position: "relative",
      }}
      onMouseEnter={(e) => { setHovered(true); onHover(item, e); }}
      onMouseLeave={() => { setHovered(false); onLeave(); }}
      onMouseMove={(e) => { if (hovered) onHover(item, e); }}
    >
      <div style={{
        height: `${productHPct}%`, width: "100%",
        background: bg, borderRight: "1px solid rgba(0,0,0,0.4)",
        display: "flex", alignItems: "center", justifyContent: "center",
        overflow: "hidden",
        transition: "filter 0.15s",
        filter: hovered ? "brightness(0.85)" : "brightness(1)",
      }}>
        {fontSize > 0 && (
          <span style={{
            color: "#fff",
            fontFamily: "JetBrains Mono, var(--font-mono)",
            fontSize,
            writingMode: isVert ? "vertical-rl" : "horizontal-tb",
            textOverflow: "ellipsis", overflow: "hidden",
            padding: 2, maxHeight: "100%", maxWidth: "100%",
            whiteSpace: "nowrap", userSelect: "none",
          }}>
            {label}
          </span>
        )}
      </div>
    </div>
  );
}

/* ── Shelf ──────────────────────────────────────────────────────────────────── */

function Shelf({
  charolaNum, items, totalWidth, shelfHeightPx, shelfAltoCm, isLast, onHover, onLeave,
}: {
  charolaNum: number;
  items: ProductoResult[];
  totalWidth: number;
  shelfHeightPx: number;
  shelfAltoCm: number;
  isLast: boolean;
  onHover: (item: ProductoResult, e: React.MouseEvent) => void;
  onLeave: () => void;
}) {
  const usedWidth = items.reduce((s, r) => s + r.ancho_ocupado_cm, 0);
  const hasFree   = usedWidth < totalWidth;

  return (
    <div style={{
      height: shelfHeightPx,
      borderBottom: isLast ? "none" : "1px solid #d4cfc8",
      display: "flex", flexDirection: "row", alignItems: "stretch",
      position: "relative", background: "#e8e4de", overflow: "hidden",
    }}>
      <div style={{
        position: "absolute", left: 4, top: 3,
        fontFamily: "JetBrains Mono, var(--font-mono)",
        fontSize: 9, color: "#b0aa9f", zIndex: 1, pointerEvents: "none",
      }}>
        {"C" + String(charolaNum).padStart(2, "0")}
      </div>

      {items.map((item, idx) => (
        <ProductCell
          key={`${item.upc_cve ?? item.item ?? item.planogrupo}-${idx}`}
          item={item}
          totalWidth={totalWidth}
          shelfAltoCm={shelfAltoCm}
          onHover={onHover}
          onLeave={onLeave}
        />
      ))}

      {hasFree && (
        <div style={{
          flex: 1, background: "#e0dbd4",
          borderLeft: items.length > 0 ? "1px dashed #c8c3bc" : "none",
        }} />
      )}
    </div>
  );
}

/* ── Loading skeleton ───────────────────────────────────────────────────────── */

const SKELETON_WIDTHS = [
  [28, 18, 22, 14],
  [20, 25, 12, 18],
  [14, 22, 20, 16],
  [26, 16, 14, 22],
  [18, 20, 24, 12],
  [22, 14, 18, 26],
];

function SkeletonDoor({ shelvesPerDoor }: { shelvesPerDoor: number }) {
  return (
    <div style={{
      display: "flex", flexDirection: "column", flex: 1,
      minWidth: 180, maxWidth: 280, borderRight: "1.5px solid #b8b3ac",
    }}>
      <div style={{ height: 28, background: "#dedad4", borderBottom: "1px solid #d4cfc8", flexShrink: 0 }} />
      {Array.from({ length: shelvesPerDoor }).map((_, i) => (
        <div key={i} style={{
          height: 88, borderBottom: i < shelvesPerDoor - 1 ? "1px solid #d4cfc8" : "none",
          background: "#e8e4de", display: "flex", alignItems: "flex-end",
          gap: 3, padding: "0 8px",
        }}>
          {SKELETON_WIDTHS[i % SKELETON_WIDTHS.length].map((w, j) => (
            <div key={j} style={{
              width: `${w}%`, height: `${55 + j * 8}%`,
              borderRadius: 2, background: "#cdc8c0",
              animation: "pulse 1.6s ease-in-out infinite",
              animationDelay: `${j * 0.12}s`,
            }} />
          ))}
        </div>
      ))}
    </div>
  );
}

/* ── Main component ─────────────────────────────────────────────────────────── */

export default function PlanogramGrid({
  results = [],
  disenoReferencia,
  totalWidth = 55,
  shelvesPerDoor,
  isLoading = false,
}: PlanogramGridProps) {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);

  const SHELVES_PER_DOOR = shelvesPerDoor ?? 6;

  const assigned   = results.filter((r) => !r.flag_no_colocado && r.charola != null && r.charola > 0);
  const unassigned = results.filter((r) => r.flag_no_colocado);
  const maxCharola = assigned.length > 0 ? Math.max(...assigned.map((r) => r.charola!)) : 0;
  const numDoors   = maxCharola > 0 ? Math.ceil(maxCharola / SHELVES_PER_DOOR) : 0;

  // Build door → shelf → items structure
  const doors: Record<number, Record<number, ProductoResult[]>> = {};
  for (let door = 1; door <= numDoors; door++) {
    doors[door] = {};
    for (let shelf = 1; shelf <= SHELVES_PER_DOOR; shelf++) {
      const charolaNum = (door - 1) * SHELVES_PER_DOOR + shelf;
      doors[door][charolaNum] = assigned
        .filter((r) => r.charola === charolaNum)
        .sort((a, b) => (a.ubicacion_bandeja ?? 0) - (b.ubicacion_bandeja ?? 0));
    }
  }

  // Compute shelf heights from alto_cm of items on each shelf
  const shelfAltoCmMap: Record<number, number> = {};
  for (const item of assigned) {
    const c = item.charola!;
    shelfAltoCmMap[c] = Math.max(shelfAltoCmMap[c] ?? 0, item.alto_cm ?? 0);
  }

  const doorLabel = (door: number) => {
    const isPartial = door === numDoors && maxCharola % SHELVES_PER_DOOR !== 0;
    return `P${door}${isPartial ? "½" : ""}`;
  };

  const handleHover = (item: ProductoResult, e: React.MouseEvent) =>
    setTooltip({ item, x: e.clientX, y: e.clientY });
  const handleLeave = () => setTooltip(null);

  /* Loading state */
  if (isLoading) {
    return (
      <div style={{ background: "#f0ede8", overflow: "hidden" }}>
        <div style={{
          height: 40, background: "#dedad4", borderBottom: "1px solid #c8c3bc",
          display: "flex", alignItems: "center", padding: "0 16px",
        }}>
          <span style={{
            fontFamily: "JetBrains Mono, var(--font-mono)", fontSize: 10,
            color: "#888", marginRight: 12, letterSpacing: "0.08em",
          }}>
            PLANOGRAMA
          </span>
          <div style={{
            width: 140, height: 12, borderRadius: 2, background: "#cdc8c0",
            animation: "pulse 1.6s ease-in-out infinite",
          }} />
        </div>
        <div style={{ display: "flex", flexDirection: "row", background: "#f0ede8", overflowX: "auto" }}>
          {Array.from({ length: 3 }).map((_, i) => (
            <SkeletonDoor key={i} shelvesPerDoor={SHELVES_PER_DOOR} />
          ))}
        </div>
      </div>
    );
  }

  /* Empty state */
  if (results.length === 0) {
    return (
      <div style={{
        padding: "60px 24px", textAlign: "center",
        fontFamily: "JetBrains Mono, var(--font-mono)", fontSize: 12,
        letterSpacing: "0.04em", color: "#888", background: "#f0ede8",
      }}>
        Sin resultados — ejecuta el optimizador para ver el planograma
      </div>
    );
  }

  /* Main render */
  return (
    <div style={{ background: "#f0ede8", userSelect: "none" }}>

      {/* ── Header bar ── */}
      <div style={{
        height: 40, background: "#dedad4", borderBottom: "1px solid #c8c3bc",
        padding: "0 16px", display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <div style={{ display: "flex", alignItems: "center" }}>
          <span style={{
            fontFamily: "JetBrains Mono, var(--font-mono)", fontSize: 10,
            color: "#888", marginRight: 12, letterSpacing: "0.08em",
          }}>
            PLANOGRAMA
          </span>
          {disenoReferencia && (
            <span style={{ fontFamily: "JetBrains Mono, var(--font-mono)", fontSize: 12, color: "#1a1a1a" }}>
              {disenoReferencia}
            </span>
          )}
        </div>
        <span style={{
          background: "#f0ede8", border: "1px solid #c8c3bc", borderRadius: 4,
          padding: "3px 10px", fontFamily: "JetBrains Mono, var(--font-mono)",
          fontSize: 10, color: "#888",
        }}>
          {numDoors} puertas · {maxCharola} charolas
        </span>
      </div>

      {/* ── Doors grid ── */}
      <div style={{
        display: "flex", flexDirection: "row", background: "#f0ede8",
        overflowX: "auto", overflowY: "hidden", minHeight: 0,
      }}>
        {Array.from({ length: numDoors }).map((_, doorIdx) => {
          const door      = doorIdx + 1;
          const shelves   = doors[door];
          const shelfNums = Object.keys(shelves).map(Number);
          const isLastDoor = door === numDoors;

          return (
            <div key={door} style={{
              display: "flex", flexDirection: "column", flex: 1,
              minWidth: 180, maxWidth: 280,
              borderRight: isLastDoor ? "none" : "1.5px solid #b8b3ac",
            }}>
              {/* Door header */}
              <div style={{
                height: 28, background: "#dedad4", borderBottom: "1px solid #d4cfc8",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontFamily: "JetBrains Mono, var(--font-mono)", fontSize: 10,
                color: "#888", flexShrink: 0,
              }}>
                {doorLabel(door)}
              </div>

              {/* Shelves */}
              {shelfNums.map((charolaNum, shelfIdx) => {
                const altoCm       = shelfAltoCmMap[charolaNum] ?? 24.5;
                const shelfHeightPx = getShelfPx(altoCm);
                return (
                  <Shelf
                    key={charolaNum}
                    charolaNum={charolaNum}
                    items={shelves[charolaNum]}
                    totalWidth={totalWidth}
                    shelfHeightPx={shelfHeightPx}
                    shelfAltoCm={altoCm}
                    isLast={shelfIdx === shelfNums.length - 1}
                    onHover={handleHover}
                    onLeave={handleLeave}
                  />
                );
              })}
            </div>
          );
        })}
      </div>

      {/* ── Unassigned ── */}
      {unassigned.length > 0 && (
        <div style={{ background: "#fff5f5", borderTop: "2px solid #E30613", padding: "12px 16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
            <span style={{
              background: "#E30613", color: "#fff",
              fontFamily: "JetBrains Mono, var(--font-mono)",
              fontSize: 10, fontWeight: 700, padding: "2px 8px",
              borderRadius: 4, letterSpacing: "0.06em",
            }}>
              SIN COLOCAR
            </span>
            <span style={{ fontFamily: "JetBrains Mono, var(--font-mono)", fontSize: 11, color: "#666" }}>
              {unassigned.length} productos
            </span>
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            {unassigned.map((item, i) => (
              <div key={i} style={{
                display: "flex", justifyContent: "space-between", padding: "6px 0",
                borderBottom: i < unassigned.length - 1 ? "1px solid #fdd" : "none",
              }}>
                <span style={{ fontFamily: "JetBrains Mono, var(--font-mono)", fontSize: 11, color: "#666" }}>
                  {item.item_desc ?? item.planogrupo}
                </span>
                <span style={{ fontFamily: "JetBrains Mono, var(--font-mono)", fontSize: 11, color: "#999" }}>
                  {item.ancho_ocupado_cm} cm
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {tooltip && <Tooltip tip={tooltip} />}
    </div>
  );
}
