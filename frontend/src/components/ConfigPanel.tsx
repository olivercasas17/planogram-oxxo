import { useCallback, useMemo } from "react";
import { startOptimize } from "../api/client";
import type { JobResult } from "../types/api";

interface ConfigPanelProps {
  fileId: string;
  filename: string;
  totalProductos: number;
  tiendas: string[];
  tipoTienda: string;
  onChangeTienda: (v: string) => void;
  onReset: () => void;
  onJobStart: (jobId: string) => void;
  isRunning: boolean;
  job: JobResult | null;
}

function scoreTier(score: number): { label: string; bg: string; color: string } {
  if (score > 0.8) return { label: "● ÓPTIMO",  bg: "#e8f5e9", color: "#2e7d32" };
  if (score > 0.5) return { label: "● PARCIAL", bg: "#fff3e0", color: "#e65100" };
  return                   { label: "● BAJO",    bg: "#ffeaea", color: "#E30613" };
}

function fmt(n: number): string {
  return n.toLocaleString("es-MX");
}

export default function ConfigPanel({
  fileId, filename, totalProductos,
  tiendas, tipoTienda, onChangeTienda,
  onReset, onJobStart, isRunning, job,
}: ConfigPanelProps) {
  const charolasUsadas = useMemo(() => {
    if (!job?.results) return 0;
    return new Set(job.results.filter((r) => !r.flag_no_colocado && r.charola != null).map((r) => r.charola)).size;
  }, [job]);

  const handleExecute = useCallback(async () => {
    if (isRunning) return;
    try {
      const res = await startOptimize({ file_id: fileId });
      onJobStart(res.job_id);
    } catch {
      // Home maneja el estado de error vía polling
    }
  }, [fileId, isRunning, onJobStart]);

  const tier = job?.score != null ? scoreTier(job.score) : null;

  return (
    <div style={{
      width: "100%",
      background: "#fff",
      borderRight: "1px solid #e8e8e4",
      padding: 20,
      display: "flex",
      flexDirection: "column",
      gap: 16,
      minHeight: "calc(100vh - 104px)",
    }}>

      {/* ── SECCIÓN 1: ARCHIVO ─────────────────────────────────────────── */}
      <div style={{
        background: "#faf9f5",
        border: "1px solid #e8e8e4",
        borderRadius: 10,
        padding: "14px 16px",
      }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
            <span style={{
              flexShrink: 0,
              background: "#ffeaea",
              color: "#E30613",
              fontFamily: "var(--font-mono)",
              fontSize: 10,
              fontWeight: 700,
              padding: "2px 8px",
              borderRadius: 20,
              letterSpacing: "0.04em",
            }}>
              CSV
            </span>
            <span style={{
              fontSize: 13,
              fontWeight: 500,
              color: "#1a1a1a",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}>
              {filename}
            </span>
          </div>
          <button
            onClick={onReset}
            style={{
              flexShrink: 0,
              background: "none",
              border: "none",
              cursor: "pointer",
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              fontWeight: 600,
              color: "#E30613",
              padding: "2px 0",
              letterSpacing: "0.06em",
              outline: "none",
            }}
          >
            CAMBIAR
          </button>
        </div>
        <p style={{
          margin: "4px 0 0",
          fontFamily: "var(--font-mono)",
          fontSize: 11,
          color: "var(--text-muted)",
        }}>
          {fmt(totalProductos)} productos
        </p>
      </div>

      {/* ── SECCIÓN: TIPO DE TIENDA ────────────────────────────────────── */}
      {tiendas.length > 0 && (
        <div>
          <p style={{
            margin: "0 0 6px",
            fontFamily: "var(--font-mono)",
            fontSize: 10,
            fontWeight: 600,
            color: "var(--text-muted)",
            textTransform: "uppercase",
            letterSpacing: "0.10em",
          }}>
            TIPO DE TIENDA
          </p>
          <div style={{ position: "relative" }}>
            <select
              value={tipoTienda}
              onChange={(e) => onChangeTienda(e.target.value)}
              style={{
                width: "100%",
                border: "1px solid #e8e8e4",
                borderRadius: 6,
                padding: "8px 32px 8px 10px",
                fontFamily: "var(--font-mono)",
                fontSize: 12,
                color: "#1a1a1a",
                background: "#fff",
                appearance: "none",
                WebkitAppearance: "none",
                outline: "none",
                cursor: "pointer",
              }}
            >
              {tiendas.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
            <svg
              width="12" height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#999"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{
                position: "absolute",
                right: 10,
                top: "50%",
                transform: "translateY(-50%)",
                pointerEvents: "none",
              }}
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </div>
        </div>
      )}

      {/* ── SECCIÓN 3: RESULTADO ───────────────────────────────────────── */}
      {job && tier && (
        <div
          key={job.job_id}
          className="result-card-fadein"
          style={{
            border: "1px solid #e8e8e4",
            borderRadius: 10,
            overflow: "hidden",
          }}
        >
          {/* Cabecera */}
          <div style={{
            padding: "12px 16px",
            borderBottom: "1px solid #e8e8e4",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}>
            <span style={{
              fontFamily: "var(--font-mono)",
              fontSize: 10,
              fontWeight: 600,
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              color: "var(--text-muted)",
            }}>
              RESULTADO
            </span>
            <span style={{
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              fontWeight: 600,
              background: tier.bg,
              color: tier.color,
              padding: "3px 9px",
              borderRadius: 20,
              letterSpacing: "0.04em",
            }}>
              {tier.label}
            </span>
          </div>

          {/* Score principal */}
          <div style={{
            padding: 16,
            borderBottom: "1px solid #e8e8e4",
          }}>
            <div style={{
              fontFamily: "var(--font-mono)",
              fontSize: 42,
              fontWeight: 700,
              lineHeight: 1,
              color: tier.color,
            }}>
              {((job.score ?? 0) * 100).toFixed(1)}
            </div>
            <p style={{
              margin: "6px 0 0",
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              color: "var(--text-muted)",
            }}>
              Score Z*/Z^H (similitud histórico)
            </p>
          </div>

          {/* Métricas 2×2 */}
          <div style={{
            padding: "12px 16px",
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 12,
          }}>
            {([
              { label: "Colocados",       value: fmt(job.colocados ?? 0),       color: undefined                                                   },
              { label: "Sin colocar",     value: fmt(job.no_colocados ?? 0),    color: (job.no_colocados ?? 0) > 0 ? "#E30613" : undefined         },
              { label: "Total SKUs",      value: fmt(job.total_productos ?? 0), color: undefined                                                   },
              { label: "Charolas usadas", value: fmt(charolasUsadas),           color: undefined                                                   },
            ] as const).map(({ label, value, color }) => (
              <div key={label}>
                <div style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 10,
                  fontWeight: 600,
                  letterSpacing: "0.10em",
                  textTransform: "uppercase",
                  color: "var(--text-muted)",
                  marginBottom: 4,
                }}>
                  {label}
                </div>
                <div style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 16,
                  fontWeight: 700,
                  color: color ?? "#1a1a1a",
                }}>
                  {value}
                </div>
              </div>
            ))}
          </div>

        </div>
      )}

      {/* ── SECCIÓN 2: EJECUTAR (pegado al fondo) ─────────────────────── */}
      <button
        onClick={handleExecute}
        disabled={isRunning}
        style={{
          marginTop: "auto",
          width: "100%",
          height: 44,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 8,
          background: isRunning ? "#ccc" : "#E30613",
          color: "#fff",
          border: "none",
          borderRadius: 6,
          fontFamily: "var(--font-ui)",
          fontSize: 13,
          fontWeight: 600,
          letterSpacing: "0.06em",
          textTransform: "uppercase",
          cursor: isRunning ? "not-allowed" : "pointer",
          transition: "background 120ms",
          outline: "none",
        }}
        onMouseOver={(e) => { if (!isRunning) e.currentTarget.style.background = "#c8000f"; }}
        onMouseOut={(e) => { if (!isRunning) e.currentTarget.style.background = isRunning ? "#ccc" : "#E30613"; }}
      >
        {isRunning ? (
          <>
            <span className="spinner spinner-sm" />
            PROCESANDO...
          </>
        ) : (
          <>▶ EJECUTAR OPTIMIZADOR</>
        )}
      </button>
    </div>
  );
}
