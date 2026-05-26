from __future__ import annotations

import io
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Columnas requeridas en el CSV de OXXO
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS: list[str] = [
    "SEGMENTO_ID",
    "MUEBLE_ID",
    "PLANOGRUPO",
    "TAMAÑO_POST",
    "DIRECCION_LEGO_ID",
    "CHAROLA",
    "UBICACION_BANDEJA",
    "ANCHO",
    "ALTO",
    "Width",
    "Height",
]

CSV_ENCODING = "latin1"

# Los archivos exportados desde el sistema de OXXO llevan BOM UTF-8.
# Tiras el BOM y decodificas con UTF-8 (reemplazando bytes inválidos)
# para que columnas como "TAMAÑO_POST" salgan con el nombre correcto.
_UTF8_BOM = b"\xef\xbb\xbf"


# ---------------------------------------------------------------------------
# Validación
# ---------------------------------------------------------------------------

class MissingColumnsError(ValueError):
    """Se lanza cuando el CSV no contiene todas las columnas requeridas."""

    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(
            f"El archivo CSV no contiene las siguientes columnas requeridas: "
            f"{missing}. "
            f"Columnas requeridas: {REQUIRED_COLUMNS}"
        )


def validate_csv(content: bytes) -> pd.DataFrame:
    """
    Lee y valida el CSV de OXXO.

    Parámetros
    ----------
    content : bytes
        Contenido crudo del archivo.  El archivo puede llevar BOM UTF-8;
        si es así se elimina antes de parsear.  Bytes no decodificables
        se reemplazan con el carácter de reemplazo Unicode (U+FFFD).

    Retorna
    -------
    pd.DataFrame con todas las columnas requeridas presentes.

    Lanza
    -----
    MissingColumnsError  si faltan columnas.
    ValueError           si el archivo no puede parsearse como CSV.
    """
    if content.startswith(_UTF8_BOM):
        content = content[len(_UTF8_BOM):]

    try:
        df = pd.read_csv(
            io.BytesIO(content),
            encoding="utf-8",
            encoding_errors="replace",
        )
    except Exception as exc:
        raise ValueError(f"No se pudo leer el archivo como CSV: {exc}") from exc

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise MissingColumnsError(missing)

    return df


# ---------------------------------------------------------------------------
# Modelos Pydantic para la API
# ---------------------------------------------------------------------------

class Configuracion(BaseModel):
    """Una combinación única de filtros detectada en el CSV subido."""
    segmento_id: str
    mueble_id: str
    tamaño_post: float
    direccion_lego_id: str


class UploadResponse(BaseModel):
    file_id: str
    filename: str
    configuraciones: list[Configuracion]


class OptimizeRequest(BaseModel):
    file_id: str
    segmento_id: str
    mueble_id: str
    tamaño: float
    direccion: str


class OptimizeResponse(BaseModel):
    job_id: str
    status: str


class PlanogrupoResult(BaseModel):
    planogrupo: str
    charola: int
    ubicacion_bandeja: int
    ancho_usado_cm: float


JobStatus = Literal["pending", "running", "done", "error"]


class JobResult(BaseModel):
    job_id: str
    status: JobStatus
    solver: str | None = None
    score: float | None = None
    total_planogrupos: int | None = None
    asignados: int | None = None
    sin_asignar: int | None = None
    results: list[PlanogrupoResult] | None = None
