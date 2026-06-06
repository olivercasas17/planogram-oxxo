import { useEffect, useMemo, useRef, useState } from "react";
import type { JobResult, ProductoResult, UploadResponse } from "../types/api";
import { useJobPolling } from "../hooks/useJobPolling";
import Uploader from "../components/Uploader";
import ConfigPanel from "../components/ConfigPanel";
import PlanogramGrid from "../components/PlanogramGrid";

/* ── App state machine ───────────────────────────────────────────────────── */

type AppState =
  | { phase: "idle" }
  | { phase: "uploaded";  upload: UploadResponse }
  | { phase: "running";   upload: UploadResponse; jobId: string }
  | { phase: "done";      upload: UploadResponse; job: JobResult }
  | { phase: "error";     upload: UploadResponse; message: string };

/* ── Header ──────────────────────────────────────────────────────────────── */

function Header({ onReset }: { onReset: () => void }) {
  return (
    <header style={{
      position: "sticky",
      top: 0,
      zIndex: 100,
      background: "#fff",
      borderBottom: "1px solid var(--border-default)",
      height: 56,
      display: "flex",
      alignItems: "center",
      padding: "0 24px",
      gap: 16,
      flexShrink: 0,
    }}>
      <button
        onClick={onReset}
        style={{
          display: "flex", alignItems: "center", gap: 10,
          background: "none", border: "none", cursor: "pointer", padding: 0,
          flexShrink: 0,
        }}
      >
        <img
          src="/logo_oxxo.png"
          alt="OXXO"
          style={{ height: 28, width: "auto", objectFit: "contain", display: "block", flexShrink: 0 }}
        />
        <div style={{ width: 1, height: 18, background: "var(--border-default)", flexShrink: 0 }} />
        <span style={{
          fontFamily: "var(--font-ui)", fontSize: 13, fontWeight: 500,
          color: "var(--text-secondary)", whiteSpace: "nowrap",
        }}>
          Optimizador de Planograma
        </span>
      </button>
    </header>
  );
}

/* ── Error banner ────────────────────────────────────────────────────────── */

function ErrorBanner({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div role="alert" style={{
      background: "var(--err-bg)",
      borderBottom: "1px solid var(--err-border)",
      padding: "10px 24px",
      display: "flex", alignItems: "center", gap: 12, flexShrink: 0,
    }}>
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--err)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
      <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--err)", flex: 1 }}>{message}</span>
      <button
        onClick={onRetry}
        style={{
          background: "#fff", border: "1px solid var(--err-border)", borderRadius: "var(--r-md)",
          cursor: "pointer", fontFamily: "var(--font-ui)", fontSize: 11, fontWeight: 600,
          color: "var(--err)", padding: "4px 12px", letterSpacing: "0.04em",
          textTransform: "uppercase", flexShrink: 0,
        }}
      >
        Reintentar
      </button>
    </div>
  );
}

/* ── Export helpers ──────────────────────────────────────────────────────── */

function exportCsv(results: ProductoResult[], filename = "planograma_resultado.csv") {
  const header = "mueble_id,planogrupo,item,item_desc,upc_cve,charola,ubicacion_bandeja,ancho_ocupado_cm,alto_cm,flag_no_colocado\n";
  const rows   = results.map(
    (r) => [
      `"${r.mueble_id}"`,
      `"${r.planogrupo}"`,
      `"${r.item ?? ""}"`,
      `"${r.item_desc ?? ""}"`,
      `"${r.upc_cve ?? ""}"`,
      r.charola ?? "",
      r.ubicacion_bandeja ?? "",
      r.ancho_ocupado_cm,
      r.alto_cm,
      r.flag_no_colocado,
    ].join(",")
  ).join("\n");
  const blob = new Blob([header + rows], { type: "text/csv;charset=utf-8;" });
  const url  = URL.createObjectURL(blob);
  const a    = Object.assign(document.createElement("a"), { href: url, download: filename });
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

async function exportPng(element: HTMLElement) {
  const { default: html2canvas } = await import("html2canvas");
  const canvas = await html2canvas(element, { backgroundColor: "#050505", scale: 2 });
  const url = canvas.toDataURL("image/png");
  const a   = Object.assign(document.createElement("a"), { href: url, download: "planograma.png" });
  a.click();
}

/* ── Export button ───────────────────────────────────────────────────────── */

function ExportBtn({
  label, icon, disabled, onClick,
}: { label: string; icon: React.ReactNode; disabled: boolean; onClick: () => void }) {
  return (
    <button
      disabled={disabled}
      onClick={onClick}
      style={{
        display: "inline-flex", alignItems: "center", gap: 6,
        height: 28, padding: "0 10px",
        border: "1px solid var(--border-strong)",
        borderRadius: "var(--r-md)",
        background: "#fff",
        fontFamily: "var(--font-ui)", fontSize: 11, fontWeight: 500,
        color: disabled ? "var(--text-disabled)" : "var(--text-secondary)",
        cursor: disabled ? "not-allowed" : "pointer",
        transition: "background 100ms, color 100ms",
        outline: "none", letterSpacing: "0.04em",
        textTransform: "uppercase",
        whiteSpace: "nowrap",
      }}
      onMouseOver={(e) => { if (!disabled) { e.currentTarget.style.background = "var(--bg-elevated)"; e.currentTarget.style.color = "var(--text-primary)"; } }}
      onMouseOut={(e)  => { e.currentTarget.style.background = "#fff"; e.currentTarget.style.color = disabled ? "var(--text-disabled)" : "var(--text-secondary)"; }}
    >
      {icon}
      {label}
    </button>
  );
}

const DownloadIcon = (
  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="7 10 12 15 17 10" />
    <line x1="12" y1="15" x2="12" y2="3" />
  </svg>
);
const ImageIcon = (
  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
    <circle cx="8.5" cy="8.5" r="1.5" />
    <polyline points="21 15 16 10 5 21" />
  </svg>
);

/* ── Viewer toolbar ──────────────────────────────────────────────────────── */

const ChevronDown = (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#999" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ pointerEvents: "none" }}>
    <polyline points="6 9 12 15 18 9" />
  </svg>
);

function ViewerToolbar({
  disenors,
  selectedDiseno,
  onChangeDiseno,
  exportCsvDisabled,
  exportPngDisabled,
  onExportCsv,
  onExportPng,
  pngLoading,
}: {
  disenors: string[];
  selectedDiseno: string;
  onChangeDiseno: (v: string) => void;
  exportCsvDisabled: boolean;
  exportPngDisabled: boolean;
  onExportCsv: () => void;
  onExportPng: () => void;
  pngLoading: boolean;
}) {
  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      gap: 12,
      padding: "10px 16px",
      borderBottom: "1px solid var(--border-subtle)",
    }}>
      {/* Left: planogram selector */}
      <div style={{ display: "flex", alignItems: "center", flex: 1, minWidth: 0 }}>
        <span style={{
          fontFamily: "var(--font-mono)",
          fontSize: 10,
          color: "var(--text-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          marginRight: 10,
          whiteSpace: "nowrap",
          flexShrink: 0,
        }}>
          PLANOGRAMA
        </span>

        {disenors.length > 0 ? (
          <div style={{ position: "relative", flexShrink: 0 }}>
            <select
              value={selectedDiseno}
              onChange={(e) => onChangeDiseno(e.target.value)}
              style={{
                fontFamily: "JetBrains Mono, var(--font-mono)",
                fontSize: 12,
                color: "#1a1a1a",
                background: "#fff",
                border: "1px solid #d0cfc8",
                borderRadius: 6,
                padding: "5px 32px 5px 10px",
                cursor: "pointer",
                minWidth: 280,
                appearance: "none",
                WebkitAppearance: "none",
                outline: "none",
              }}
            >
              {disenors.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
            <div style={{
              position: "absolute",
              right: 10,
              top: "50%",
              transform: "translateY(-50%)",
              pointerEvents: "none",
              display: "flex",
              alignItems: "center",
            }}>
              {ChevronDown}
            </div>
          </div>
        ) : (
          <span style={{
            fontFamily: "JetBrains Mono, var(--font-mono)",
            fontSize: 11,
            color: "var(--text-disabled)",
          }}>
            —
          </span>
        )}
      </div>

      {/* Right: export buttons */}
      <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
        <ExportBtn icon={DownloadIcon} label="CSV" disabled={exportCsvDisabled} onClick={onExportCsv} />
        <ExportBtn icon={ImageIcon} label={pngLoading ? "…" : "PNG"} disabled={exportPngDisabled} onClick={onExportPng} />
      </div>
    </div>
  );
}

/* ── Empty hint (uploaded, not yet run) ──────────────────────────────────── */

function EmptyHint() {
  return (
    <div style={{
      padding: "72px 24px",
      textAlign: "center",
      display: "flex", flexDirection: "column", alignItems: "center", gap: 16,
      border: "1px dashed var(--border-default)",
      borderRadius: "var(--r-lg)",
      background: "var(--bg-surface)",
      minHeight: 320,
      justifyContent: "center",
    }}>
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--text-disabled)" strokeWidth="0.8" strokeLinecap="round">
        <rect x="3" y="3" width="18" height="18" rx="1" />
        <line x1="3" y1="9" x2="21" y2="9" />
        <line x1="3" y1="15" x2="21" y2="15" />
        <line x1="9" y1="9" x2="9" y2="21" />
      </svg>
      <div>
        <p style={{ margin: 0, fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-secondary)", letterSpacing: "0.04em" }}>
          Selecciona el tipo de tienda y ejecuta el optimizador
        </p>
        <p style={{ margin: "8px 0 0", fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--text-disabled)", letterSpacing: "0.03em" }}>
          El visor mostrará el acomodo generado por el solver
        </p>
      </div>
    </div>
  );
}

/* ── Main page ───────────────────────────────────────────────────────────── */

export default function Home() {
  const [state,          setState]          = useState<AppState>({ phase: "idle" });
  const [pngLoading,     setPngLoading]     = useState(false);
  const [selectedDiseno, setSelectedDiseno] = useState<string>("");
  const [tipoTienda,     setTipoTienda]     = useState<string>("");
  const planogramRef = useRef<HTMLDivElement>(null);

  const jobId = state.phase === "running" ? state.jobId : null;
  const { result, error: pollError } = useJobPolling(jobId, 1000);

  useEffect(() => {
    if (state.phase !== "running") return;
    if (pollError) {
      setState({ phase: "error", upload: state.upload, message: pollError });
      return;
    }
    if (result?.status === "done") {
      setState({ phase: "done", upload: state.upload, job: result });
    } else if (result?.status === "error") {
      setState({ phase: "error", upload: state.upload, message: "El solver encontró un error al procesar el planograma." });
    }
  }, [result, pollError]); // eslint-disable-line react-hooks/exhaustive-deps

  const upload    = state.phase !== "idle" ? state.upload : null;
  const isRunning = state.phase === "running";
  const job       = state.phase === "done" ? state.job : null;
  const results   = job?.results ?? [];

  // Clave única por diseño: incluye segmento_id para que el filtrado sea exacto
  const makeKey = (r: ProductoResult) =>
    [r.segmento_id ?? "—", r.mueble_id, r.planogrupo, r.tamano_post ?? "?", r.direccion ?? "?"].join(" / ");

  // Todas las claves únicas de diseño presentes en los resultados
  const disenors = useMemo(() => {
    if (!results.length) return [];
    return [...new Set(results.map(makeKey))].sort();
  }, [results]); // eslint-disable-line react-hooks/exhaustive-deps

  // Filtradas por el segmento seleccionado en el sidebar
  const filteredDisenors = useMemo(() => {
    if (!tipoTienda || !disenors.length) return disenors;
    const matching = disenors.filter((d) => d.startsWith(`${tipoTienda} /`));
    const result = matching.length > 0 ? matching : disenors;
    console.log(`[tipoTienda="${tipoTienda}"] opciones de diseño filtradas:`, result);
    return result;
  }, [disenors, tipoTienda]);

  // Auto-seleccionar primera opción cuando cambia el filtro
  useEffect(() => {
    if (!filteredDisenors.length) return;
    if (!filteredDisenors.includes(selectedDiseno)) {
      setSelectedDiseno(filteredDisenors[0]);
    }
  }, [filteredDisenors]); // eslint-disable-line react-hooks/exhaustive-deps

  // Results para el diseño seleccionado en el dropdown del visor
  const filteredResults = useMemo(() => {
    if (!selectedDiseno) return results;
    const filtered = results.filter((r) => makeKey(r) === selectedDiseno);
    console.log(`[selectedDiseno="${selectedDiseno}"] results al grid:`, filtered.length);
    return filtered;
  }, [results, selectedDiseno]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleUploadSuccess = (upload: UploadResponse) => {
    console.log("[upload] segmentos detectados:", upload.tiendas);
    setTipoTienda(upload.tiendas[0] ?? "");
    setState({ phase: "uploaded", upload });
  };

  const handleJobStart = (jobId: string) => {
    if (state.phase === "idle") return;
    setSelectedDiseno("");
    setState({ phase: "running", upload: state.upload, jobId });
  };

  const handleRetry = () => {
    if (state.phase === "error") setState({ phase: "uploaded", upload: state.upload });
  };

  const handleReset = () => {
    setSelectedDiseno("");
    setTipoTienda("");
    setState({ phase: "idle" });
  };

  const handleExportPng = async () => {
    if (!planogramRef.current) return;
    setPngLoading(true);
    try { await exportPng(planogramRef.current); }
    finally { setPngLoading(false); }
  };

  /* ── Upload screen (idle) ── */
  if (state.phase === "idle") {
    return (
      <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: "var(--bg-canvas)" }}>
        <Header onReset={handleReset} />
        <main style={{
          flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
          padding: "48px 24px", minHeight: "calc(100vh - 56px)",
        }}>
          <div style={{ width: "100%", maxWidth: 380, display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
            <Uploader onSuccess={handleUploadSuccess} />
          </div>
        </main>
      </div>
    );
  }

  /* ── Result screen ── */
  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: "var(--bg-canvas)" }}>
      <Header onReset={handleReset} />

      {state.phase === "error" && (
        <ErrorBanner message={state.message} onRetry={handleRetry} />
      )}

      <main style={{
        flex: 1,
        padding: "24px",
        display: "grid",
        gridTemplateColumns: "272px 1fr",
        gap: "20px",
        alignItems: "start",
        maxWidth: 1380,
        width: "100%",
        margin: "0 auto",
      }}>

        {/* ── Left sidebar ── */}
        <div style={{ position: "sticky", top: 80, alignSelf: "start" }}>
          <ConfigPanel
            fileId={upload!.file_id}
            filename={upload!.filename}
            totalProductos={upload!.total_productos}
            tiendas={upload!.tiendas}
            tipoTienda={tipoTienda}
            onChangeTienda={setTipoTienda}
            onReset={handleReset}
            onJobStart={handleJobStart}
            isRunning={isRunning}
            job={job}
          />
        </div>

        {/* ── Center content ── */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16, minWidth: 0 }}>

          {/* Viewer card */}
          <div className="ref-card" style={{ overflowX: "auto", overflowY: "visible" }}>
            <ViewerToolbar
              disenors={filteredDisenors}
              selectedDiseno={selectedDiseno}
              onChangeDiseno={setSelectedDiseno}
              exportCsvDisabled={filteredResults.length === 0}
              exportPngDisabled={filteredResults.length === 0 || pngLoading}
              onExportCsv={() => exportCsv(filteredResults)}
              onExportPng={handleExportPng}
              pngLoading={pngLoading}
            />
            {state.phase === "uploaded" && !isRunning && results.length === 0 ? (
              <div style={{ padding: 20 }}>
                <EmptyHint />
              </div>
            ) : (
              <div ref={planogramRef}>
                <PlanogramGrid
                  results={filteredResults}
                  disenoReferencia={selectedDiseno || undefined}
                  isLoading={isRunning}
                />
              </div>
            )}
          </div>

        </div>
      </main>
    </div>
  );
}
