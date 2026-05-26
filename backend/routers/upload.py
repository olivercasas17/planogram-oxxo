import uuid
import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile

from solver.schemas import Configuracion, MissingColumnsError, UploadResponse, validate_csv

router = APIRouter(prefix="/upload", tags=["upload"])

# In-memory store: file_id -> DataFrame
# Replaced by a real cache/DB in production.
_file_store: dict[str, tuple[str, pd.DataFrame]] = {}  # file_id -> (filename, df)


def get_dataframe(file_id: str) -> pd.DataFrame:
    """Retrieve a stored DataFrame, raising 404 if not found."""
    entry = _file_store.get(file_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"file_id '{file_id}' no encontrado")
    return entry[1]


@router.post("", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()

    try:
        df = validate_csv(content)
    except MissingColumnsError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Detect unique filter combinations
    combo_cols = ["SEGMENTO_ID", "MUEBLE_ID", "TAMAÑO_POST", "DIRECCION_LEGO_ID"]
    combos = (
        df[combo_cols]
        .drop_duplicates()
        .sort_values(combo_cols)
        .reset_index(drop=True)
    )

    configuraciones = [
        Configuracion(
            segmento_id=str(row["SEGMENTO_ID"]).strip(),
            mueble_id=str(row["MUEBLE_ID"]).strip(),
            tamaño_post=float(row["TAMAÑO_POST"]),
            direccion_lego_id=str(row["DIRECCION_LEGO_ID"]).strip(),
        )
        for _, row in combos.iterrows()
    ]

    file_id = str(uuid.uuid4())
    _file_store[file_id] = (file.filename or "unknown.csv", df)

    return UploadResponse(
        file_id=file_id,
        filename=file.filename or "unknown.csv",
        configuraciones=configuraciones,
    )
