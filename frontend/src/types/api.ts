// Types mirroring backend/solver/schemas.py Pydantic models

export interface UploadResponse {
  file_id: string;
  filename: string;
  total_productos: number;
  tiendas: string[];
}

export interface OptimizeRequest {
  file_id: string;
}

export interface OptimizeResponse {
  job_id: string;
  status: string;
}

/** Un producto en el planograma resultante del algoritmo heurístico. */
export interface ProductoResult {
  segmento_id?: string | null;
  mueble_id: string;
  planogrupo: string;
  tamano_post?: number | null;
  direccion?: string | null;
  conjunto_id?: string | null;
  charola?: number | null;          // null = no colocado
  ubicacion_bandeja?: number | null;
  item?: string | null;
  item_desc?: string | null;
  upc_cve?: string | null;
  num_frentes: number;
  ancho_cm: number;
  alto_cm: number;
  ancho_ocupado_cm: number;
  x_inicio_cm?: number | null;
  x_fin_cm?: number | null;
  flag_no_colocado: boolean;
}

export type JobStatus = "pending" | "running" | "done" | "error";

export interface JobResult {
  job_id: string;
  status: JobStatus;
  solver?: string;
  // Score Z* / Z^H — similitud con el histórico (0–1)
  score?: number;
  score_z?: number;           // coincidencias exactas con histórico
  score_zh?: number;          // total productos (denominador)
  total_productos?: number;
  colocados?: number;
  no_colocados?: number;
  charolas_exceden_ancho?: number;
  posiciones_duplicadas?: number;
  ocupacion_media_pct?: number;
  results?: ProductoResult[];
}

/** Alias para compatibilidad con componentes que usaban PlanogrupoResult */
export type PlanogrupoResult = ProductoResult;
