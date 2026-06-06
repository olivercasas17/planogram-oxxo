import { useCallback, useRef, useState } from "react";
import axios from "axios";
import { uploadCsv } from "../api/client";
import type { UploadResponse } from "../types/api";

/* ── Types ─────────────────────────────────────────────────────────────── */

type UploadState =
  | { phase: "idle" }
  | { phase: "loading" }
  | { phase: "error"; message: string };

interface UploaderProps {
  onSuccess: (data: UploadResponse) => void;
}

/* ── Helpers ─────────────────────────────────────────────────────────────── */

function extractError(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const d = err.response?.data?.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return d.map((x: { msg?: string }) => x.msg ?? x).join("; ");
  }
  return err instanceof Error ? err.message : "Error desconocido al subir el archivo.";
}

function isAccepted(file: File) {
  return file.name.endsWith(".csv") || file.name.endsWith(".xlsx");
}

/* ── Upload icon ─────────────────────────────────────────────────────────── */

function UploadIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  );
}

/* ── Main component ──────────────────────────────────────────────────────── */

export default function Uploader({ onSuccess }: UploaderProps) {
  const [state,    setState]    = useState<UploadState>({ phase: "idle" });
  const [dragging, setDragging] = useState(false);
  const inputRef                = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    async (file: File) => {
      if (!isAccepted(file)) {
        setState({ phase: "error", message: "Solo se aceptan archivos CSV o XLSX." });
        return;
      }
      setState({ phase: "loading" });
      try {
        const data = await uploadCsv(file);
        onSuccess(data);
      } catch (err) {
        setState({ phase: "error", message: extractError(err) });
      }
    },
    [onSuccess]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
      e.target.value = "";
    },
    [handleFile]
  );

  const handleLoadSample = useCallback(async () => {
    setState({ phase: "loading" });
    try {
      const res = await fetch("/sample.csv");
      if (!res.ok) throw new Error("No se encontró /sample.csv en la carpeta public/");
      const blob = await res.blob();
      const file = new File([blob], "ejemplo_planograma.csv", { type: "text/csv" });
      handleFile(file);
    } catch (err) {
      setState({
        phase: "error",
        message: err instanceof Error ? err.message : "No se pudo cargar el dataset de ejemplo.",
      });
    }
  }, [handleFile]);

  const loading = state.phase === "loading";

  return (
    <div style={{ width: "100%", display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>

      {/* Drop zone */}
      <div
        role="button"
        tabIndex={0}
        aria-label="Zona de carga. Arrastra un CSV o XLSX, o presiona Enter para abrir el selector."
        className={`drop-zone${dragging ? " dragging" : ""}`}
        onClick={() => !loading && inputRef.current?.click()}
        onKeyDown={(e) => { if ((e.key === "Enter" || e.key === " ") && !loading) inputRef.current?.click(); }}
        onDragOver={(e) => { e.preventDefault(); if (!loading) setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={loading ? undefined : handleDrop}
        style={{
          width: "100%",
          padding: "48px 28px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 14,
          cursor: loading ? "default" : "pointer",
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx"
          onChange={handleChange}
          style={{ display: "none" }}
          tabIndex={-1}
        />

        {/* Icon circle */}
        <div style={{
          width: 48, height: 48,
          borderRadius: "50%",
          background: "var(--accent-muted)",
          color: "var(--accent)",
          display: "grid", placeItems: "center",
          flexShrink: 0,
          transition: "background 150ms",
        }}>
          {loading
            ? <span className="spinner spinner-md" />
            : <UploadIcon />
          }
        </div>

        {/* Text */}
        <div style={{ textAlign: "center", display: "flex", flexDirection: "column", gap: 5 }}>
          <span style={{
            fontSize: 14, fontWeight: 500,
            color: loading ? "var(--text-muted)" : dragging ? "var(--accent)" : "var(--text-primary)",
            transition: "color 150ms",
          }}>
            {loading ? "Procesando archivo…" : dragging ? "Suelta para cargar" : "Suelta tu CSV o haz clic"}
          </span>
          <span style={{
            fontFamily: "var(--font-mono)", fontSize: 10,
            color: "var(--text-muted)", letterSpacing: "0.04em",
          }}>
            {loading ? "Detectando configuraciones" : "ejemplo_planograma.csv · max 50 MB"}
          </span>
        </div>

        {/* Select button */}
        {!loading && (
          <button
            onClick={(e) => { e.stopPropagation(); inputRef.current?.click(); }}
            style={{
              height: 32, padding: "0 16px",
              border: "1px solid var(--border-strong)",
              borderRadius: "var(--r-md)",
              background: "#fff",
              color: "var(--text-primary)",
              fontFamily: "var(--font-ui)",
              fontSize: 12, fontWeight: 500,
              letterSpacing: "0.04em",
              cursor: "pointer",
              transition: "background 100ms",
              outline: "none",
            }}
            onMouseOver={(e) => { e.currentTarget.style.background = "var(--bg-elevated)"; }}
            onMouseOut={(e)  => { e.currentTarget.style.background = "#fff"; }}
          >
            Seleccionar archivo
          </button>
        )}
      </div>

      {/* Error */}
      {state.phase === "error" && (
        <div
          role="alert"
          style={{
            width: "100%",
            display: "flex", alignItems: "flex-start", gap: 10,
            padding: "10px 14px",
            background: "var(--err-bg)",
            border: "1px solid var(--err-border)",
            borderRadius: "var(--r-lg)",
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--err)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, marginTop: 1 }}>
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--err)", flex: 1 }}>
            {state.message}
          </span>
          <button
            onClick={() => setState({ phase: "idle" })}
            style={{
              background: "none", border: "none", cursor: "pointer",
              color: "var(--text-muted)", padding: 0, lineHeight: 1,
              flexShrink: 0, fontSize: 16,
            }}
          >
            ×
          </button>
        </div>
      )}

      {/* Sample link */}
      {!loading && (
        <button
          onClick={handleLoadSample}
          style={{
            background: "none", border: "none", cursor: "pointer",
            fontFamily: "var(--font-mono)", fontSize: 11,
            color: "var(--text-muted)", letterSpacing: "0.04em",
            padding: "4px 8px", borderRadius: "var(--r-sm)",
            transition: "color 100ms",
            outline: "none",
          }}
          onMouseOver={(e) => { e.currentTarget.style.color = "var(--accent)"; }}
          onMouseOut={(e)  => { e.currentTarget.style.color = "var(--text-muted)"; }}
        >
          o cargar dataset de ejemplo →
        </button>
      )}
    </div>
  );
}
