import uuid
import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile

from solver.schemas import MissingColumnsError, UploadResponse, validate_csv

router = APIRouter(prefix="/upload", tags=["upload"])

# In-memory store: file_id -> DataFrame
_file_store: dict[str, tuple[str, pd.DataFrame]] = {}


def get_dataframe(file_id: str) -> pd.DataFrame:
    """Retrieve a stored DataFrame, raising 404 if not found."""
    entry = _file_store.get(file_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"file_id '{file_id}' no encontrado")
    return entry[1]


def _extract_tiendas(df: pd.DataFrame) -> list[str]:
    """Extract unique store-type codes from SEGMENTO_ID."""
    if "SEGMENTO_ID" not in df.columns:
        return []
    vals = df["SEGMENTO_ID"].dropna().astype(str).str.strip()
    return sorted({v for v in vals if v and v.lower() != "nan"})


@router.post("", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()

    try:
        df = validate_csv(content)
    except MissingColumnsError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Usar la columna identificadora disponible (en orden de preferencia)
    id_col = next((c for c in ("UPC_CVE", "ITEM", "PLANOGRUPO") if c in df.columns), None)
    total_productos = int(df[id_col].nunique()) if id_col else len(df)
    tiendas = _extract_tiendas(df)
    file_id = str(uuid.uuid4())
    _file_store[file_id] = (file.filename or "unknown.csv", df)

    return UploadResponse(
        file_id=file_id,
        filename=file.filename or "unknown.csv",
        total_productos=total_productos,
        tiendas=tiendas,
    )
