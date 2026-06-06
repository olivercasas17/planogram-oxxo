from __future__ import annotations

import io
import re
from typing import Literal

import pandas as pd
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Columnas requeridas en el CSV de OXXO (algoritmo heurístico)
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS: list[str] = [
    "MUEBLE_ID",
    "PLANOGRUPO",
    "CHAROLA",
    "UBICACION_BANDEJA",
    "ANCHO",
    "ALTO",
    "NUM_FRENTES",
    "TAMANO_POST",
]

# Columnas opcionales reconocidas: SEGMENTO_ID, DIRECCION_LEGO_ID, CONJUNTO_ID,
#   SEPARADOR, PROFUNDO, ITEM, ITEM_DESC, UPC_CVE, Width_charola, MUEBLE_DESC

_UTF8_BOM = b"\xef\xbb\xbf"


# ---------------------------------------------------------------------------
# Normalización de nombres de columnas (elimina BOM y caracteres no-ASCII)
# ---------------------------------------------------------------------------

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [re.sub(r"[^0-9A-Za-z_]", "", c) for c in df.columns]
    df = df.rename(columns={
        "TAMAO_POST":       "TAMANO_POST",
        "DISEO_REFERENCIA": "DISENO_REFERENCIA",
    })
    return df


# ---------------------------------------------------------------------------
# Validación
# ---------------------------------------------------------------------------

class MissingColumnsError(ValueError):
    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(
            f"El archivo CSV no contiene las siguientes columnas requeridas: "
            f"{missing}. Columnas requeridas: {REQUIRED_COLUMNS}"
        )


def validate_csv(content: bytes) -> pd.DataFrame:
    """Lee y valida el CSV de OXXO para el algoritmo heurístico.

    Elimina BOM UTF-8. Intenta encodings utf-8-sig, latin-1, cp1252.
    Lanza MissingColumnsError si faltan columnas requeridas.
    """
    if content.startswith(_UTF8_BOM):
        content = content[len(_UTF8_BOM):]

    df = None
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            df = pd.read_csv(io.BytesIO(content), encoding=enc)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    if df is None:
        df = pd.read_csv(
            io.BytesIO(content), encoding="latin-1", encoding_errors="replace"
        )

    df = _normalize_columns(df)

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise MissingColumnsError(missing)

    return df


# ---------------------------------------------------------------------------
# Modelos Pydantic para la API
# ---------------------------------------------------------------------------

class UploadResponse(BaseModel):
    file_id: str
    filename: str
    total_productos: int
    tiendas: list[str] = []


class OptimizeRequest(BaseModel):
    file_id: str


class OptimizeResponse(BaseModel):
    job_id: str
    status: str


class ProductoResult(BaseModel):
    """Un producto en el planograma resultante."""
    segmento_id: str | None = None
    mueble_id: str
    planogrupo: str
    tamano_post: float | None = None
    direccion: str | None = None
    conjunto_id: str | None = None
    charola: int | None = None          # None = no colocado
    ubicacion_bandeja: int | None = None
    item: str | None = None
    item_desc: str | None = None
    upc_cve: str | None = None
    num_frentes: float
    ancho_cm: float
    alto_cm: float
    ancho_ocupado_cm: float
    x_inicio_cm: float | None = None
    x_fin_cm: float | None = None
    flag_no_colocado: bool


JobStatus = Literal["pending", "running", "done", "error"]


class JobResult(BaseModel):
    job_id: str
    status: JobStatus
    solver: str | None = None
    # Score Z*/Z^H  (similitud con el histórico, 0-1)
    score: float | None = None
    score_z: int | None = None          # Z* = coincidencias exactas con histórico
    score_zh: int | None = None         # Z^H = total productos (denominador)
    total_productos: int | None = None
    colocados: int | None = None
    no_colocados: int | None = None
    # Validación de factibilidad
    charolas_exceden_ancho: int | None = None
    posiciones_duplicadas: int | None = None
    ocupacion_media_pct: float | None = None
    results: list[ProductoResult] | None = None
