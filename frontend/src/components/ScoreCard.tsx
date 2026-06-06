import { useState } from "react";
import type { JobResult } from "../types/api";

interface ScoreCardProps {
  job: JobResult | null;
  isRunning?: boolean;
}

/* ── Circular SVG gauge ──────────────────────────────────────────────────── */

function Gauge({ value, size = 44 }: { value: number; size?: number }) {
  const stroke = 5;
  const r      = (size - stroke) / 2;
  const c      = 2 * Math.PI * r;
  const offset = c - (value / 100) * c;
  const color  = value >= 88 ? "var(--ok)" : value >= 60 ? "#b8730a" : "var(--accent)";

  return (
    <div style={{ position: "relative", width: size, height: size, flexShrink: 0 }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)", display: "block" }}>
        <circle cx={size / 2} cy={size / 2} r={r} stroke="var(--bg-elevated)" strokeWidth={stroke} fill="none" />
        <circle
          cx={size / 2} cy={size / 2} r={r}
          stroke={color} strokeWidth={stroke} fill="none"
          strokeDasharray={c} strokeDashoffset={offset} strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 600ms cubic-bezier(0.4,0,0.2,1), stroke 300ms" }}
        />
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
        <span style={{
          fontFamily: "var(--font-mono)", fontVariantNumeric: "tabular-nums",
          fontSize: size >= 80 ? 20 : 11, fontWeight: 700, color, lineHeight: 1,
          letterSpacing: size >= 80 ? "-0.02em" : 0,
        }}>
          {value.toFixed(size >= 80 ? 1 : 0)}
        </span>
        {size < 80 && (
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 7, color: "var(--text-muted)", lineHeight: 1, marginTop: 1 }}>%</span>
        )}
      </div>
    </div>
  );
}

/* ── Metric column ───────────────────────────────────────────────────────── */

function MetricCol({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 3, minWidth: 0 }}>
      <span style={{
        fontFamily: "var(--font-mono)", fontSize: 9, fontWeight: 600,
        letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--text-muted)",
        display: "block", whiteSpace: "nowrap",
      }}>
        {label}
      </span>
      <span style={{
        fontFamily: "var(--font-mono)", fontVariantNumeric: "tabular-nums",
        fontSize: 17, fontWeight: 700,
        color: accent ?? "var(--text-primary)", lineHeight: 1,
      }}>
        {value}
      </span>
    </div>
  );
}

/* ── Vertical divider ────────────────────────────────────────────────────── */

function VBar({ h = 28 }: { h?: number }) {
  return <div style={{ width: 1, height: h, background: "var(--border-subtle)", flexShrink: 0 }} />;
}

/* ── Details table ───────────────────────────────────────────────────────── */

function DetailsCol({ title, rows }: { title: string; rows: [string, string][] }) {
  return (
    <div>
      <div style={{
        fontFamily: "var(--font-mono)", fontSize: 9, fontWeight: 600,
        letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--text-muted)",
        marginBottom: 10,
      }}>
        {title}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
        {rows.map(([label, val]) => (
          <div key={label} style={{
            display: "flex", justifyContent: "space-between", gap: 12,
            paddingBottom: 4, borderBottom: "1px solid var(--border-subtle)",
          }}>
            <span style={{ fontFamily: "var(--font-ui)", fontSize: 11, color: "var(--text-secondary)" }}>{label}</span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 600, color: "var(--text-primary)" }}>{val}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Tier badge ──────────────────────────────────────────────────────────── */

function TierBadge({ score }: { score: number }) {
  const tier  = score > 0.8 ? "ok" : score > 0.5 ? "warn" : "err";
  const label = score > 0.8 ? "Óptimo" : score > 0.5 ? "Parcial" : "Bajo";
  return <span className={`ref-badge badge-dot badge-${tier}`}>{label}</span>;
}

/* ── Running state ───────────────────────────────────────────────────────── */

function RunningState() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, flex: 1 }}>
      <span className="spinner spinner-sm" />
      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <span style={{
          fontFamily: "var(--font-mono)", fontSize: 9, fontWeight: 600,
          letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--text-muted)",
        }}>
          Solver activo
        </span>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--warn)", fontWeight: 600 }}>
          Procesando…
        </span>
      </div>
    </div>
  );
}

/* ── Main component ──────────────────────────────────────────────────────── */

export default function ScoreCard({ job, isRunning = false }: ScoreCardProps) {
  const [open, setOpen] = useState(false);

  const score   = job?.score ?? null;
  const pctFull = score !== null ? score * 100 : null;

  if (isRunning) {
    return (
      <div className="ref-card" style={{ padding: "12px 16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{
            width: 44, height: 44, borderRadius: "50%",
            border: "5px solid var(--bg-elevated)",
            flexShrink: 0, display: "grid", placeItems: "center",
          }}>
            <span className="spinner spinner-sm" />
          </div>
          <RunningState />
        </div>
        <div style={{ marginTop: 12, height: 3, background: "var(--bg-elevated)", borderRadius: 2, overflow: "hidden" }}>
          <div style={{
            height: "100%", width: "60%", background: "var(--warn)", borderRadius: 2,
            animation: "indeterminate-bar 1.5s ease-in-out infinite",
          }} />
        </div>
        <style>{`
          @keyframes indeterminate-bar {
            0%   { width: 10%; margin-left: 0; }
            50%  { width: 60%; margin-left: 20%; }
            100% { width: 10%; margin-left: 90%; }
          }
        `}</style>
      </div>
    );
  }

  if (!job || score === null) {
    return (
      <div className="ref-card" style={{ padding: "12px 16px", display: "flex", alignItems: "center", gap: 16 }}>
        <div style={{
          width: 44, height: 44, borderRadius: "50%",
          border: "5px solid var(--bg-elevated)",
          display: "grid", placeItems: "center", flexShrink: 0,
        }}>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 700, color: "var(--text-disabled)" }}>—</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <span style={{
            fontFamily: "var(--font-mono)", fontSize: 9, fontWeight: 600,
            letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--text-muted)",
          }}>
            Resultado
          </span>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--text-disabled)" }}>
            Sin resultados aún
          </span>
        </div>
      </div>
    );
  }

  const noColocados = job.no_colocados ?? 0;

  return (
    <div className="ref-card" style={{ overflow: "hidden" }}>

      {/* ── Compact row ── */}
      <div
        style={{ display: "flex", alignItems: "center", gap: 16, padding: "12px 16px", cursor: "pointer" }}
        onClick={() => setOpen((v) => !v)}
      >
        <Gauge value={pctFull!} size={44} />

        {/* Score label — Z-star / Z-H */}
        <div style={{ display: "flex", flexDirection: "column", gap: 2, minWidth: 100 }}>
          <span style={{
            fontFamily: "var(--font-mono)", fontSize: 9, fontWeight: 600,
            letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--text-muted)",
          }}>
            Score Z*/Z^H
          </span>
          <div style={{ display: "flex", alignItems: "baseline", gap: 5 }}>
            <span style={{
              fontFamily: "var(--font-mono)", fontSize: 17, fontWeight: 700,
              color: "var(--text-primary)", lineHeight: 1, letterSpacing: "-0.01em",
            }}>
              {pctFull!.toFixed(1)}%
            </span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--text-muted)" }}>
              similitud
            </span>
          </div>
        </div>

        <VBar />
        <MetricCol label="Total SKUs" value={String(job.total_productos ?? "—")} />
        <VBar />
        <MetricCol
          label="Sin colocar"
          value={String(noColocados)}
          accent={noColocados > 0 ? "var(--err)" : undefined}
        />
        <VBar />
        <MetricCol label="Colocados" value={String(job.colocados ?? "—")} />
        <VBar />
        <MetricCol
          label="Ocupación"
          value={job.ocupacion_media_pct != null ? `${job.ocupacion_media_pct.toFixed(1)}%` : "—"}
        />

        <div style={{ flex: 1 }} />

        <TierBadge score={score} />

        <button
          onClick={(e) => { e.stopPropagation(); setOpen((v) => !v); }}
          style={{
            background: "none", border: "none", cursor: "pointer",
            fontFamily: "var(--font-mono)", fontSize: 9, fontWeight: 600,
            color: "var(--text-muted)", padding: "4px 8px",
            borderRadius: "var(--r-sm)", flexShrink: 0,
            letterSpacing: "0.08em", textTransform: "uppercase",
            display: "flex", alignItems: "center", gap: 4,
            transition: "color 100ms", outline: "none",
          }}
          onMouseOver={(e) => { e.currentTarget.style.color = "var(--text-primary)"; }}
          onMouseOut={(e)  => { e.currentTarget.style.color = "var(--text-muted)"; }}
        >
          {open ? "Ocultar ∧" : "Detalles ∨"}
        </button>
      </div>

      {/* ── Progress sliver ── */}
      <div style={{ height: 3, background: "var(--bg-elevated)", overflow: "hidden" }}>
        <div style={{
          width: `${pctFull}%`, height: "100%",
          background: `linear-gradient(90deg, var(--accent) 0%, #b8730a 55%, var(--ok) 100%)`,
          transition: "width 600ms cubic-bezier(0.4,0,0.2,1)",
        }} />
      </div>

      {/* ── Expandable details ── */}
      {open && (
        <div style={{
          borderTop: "1px solid var(--border-subtle)",
          background: "var(--bg-elevated)",
          padding: "16px 16px",
        }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 32px" }}>
            <DetailsCol title="Algoritmo" rows={[
              ["Estrategia",  "Heurístico imitación"],
              ["Solver ID",   job.solver ?? "—"],
              ["Fase 1",      "Construcción inicial (histórico)"],
              ["Fase 2",      "Reparación (exceso ancho)"],
              ["Fase 3–4",    "Llenado + mejora local"],
            ]} />
            <DetailsCol title="Factibilidad" rows={[
              ["Score Z*",              job.score_z  != null ? String(job.score_z)  : "—"],
              ["Score Z^H",             job.score_zh != null ? String(job.score_zh) : "—"],
              ["Charolas exceden ancho",job.charolas_exceden_ancho != null ? String(job.charolas_exceden_ancho) : "—"],
              ["Posiciones duplicadas", job.posiciones_duplicadas  != null ? String(job.posiciones_duplicadas)  : "—"],
              ["Ocupación media",       job.ocupacion_media_pct    != null ? `${job.ocupacion_media_pct.toFixed(1)}%` : "—"],
            ]} />
          </div>
        </div>
      )}
    </div>
  );
}
