import uuid
import math
from fastapi import APIRouter, BackgroundTasks, HTTPException

from routers.upload import get_dataframe
from solver.algoritmo import planogramar_heuristico, validar
from solver.schemas import (
    JobResult,
    OptimizeRequest,
    OptimizeResponse,
    ProductoResult,
)

router = APIRouter(prefix="/optimize", tags=["optimize"])

# In-memory job store: job_id -> JobResult
_jobs: dict[str, JobResult] = {}


def _safe_int(val) -> int | None:
    try:
        v = float(val)
        return None if math.isnan(v) else int(v)
    except (TypeError, ValueError):
        return None


def _safe_float(val) -> float | None:
    try:
        v = float(val)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None


def _safe_str(val) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    return None if s in ("nan", "", "None") else s


def _run_solver(job_id: str, file_id: str) -> None:
    """Background task: run heurístico and update job status."""
    _jobs[job_id] = JobResult(job_id=job_id, status="running")

    try:
        df = get_dataframe(file_id)
        resultado = planogramar_heuristico(df)

        score = resultado.attrs.get("Score")
        z_star = resultado.attrs.get("Z")
        z_h = resultado.attrs.get("Z_H")

        val = validar(resultado)

        total = len(resultado)
        no_colocados = int(resultado["FLAG_NO_COLOCADO"].sum())
        colocados = total - no_colocados

        productos: list[ProductoResult] = []
        for _, row in resultado.iterrows():
            no_col = bool(row.get("FLAG_NO_COLOCADO", False))
            productos.append(ProductoResult(
                segmento_id=       _safe_str(row.get("SEGMENTO_ID")),
                mueble_id=         str(row.get("MUEBLE_ID", "")),
                planogrupo=        str(row.get("PLANOGRUPO", "")),
                tamano_post=       _safe_float(row.get("TAMANO_POST")),
                direccion=         _safe_str(row.get("DIRECCION_LEGO_ID")),
                conjunto_id=       _safe_str(row.get("CONJUNTO_ID")),
                charola=           _safe_int(row.get("CHAROLA")),
                ubicacion_bandeja= _safe_int(row.get("UBICACION_BANDEJA")),
                item=              _safe_str(row.get("ITEM")),
                item_desc=         _safe_str(row.get("ITEM_DESC")),
                upc_cve=           _safe_str(row.get("UPC_CVE")),
                num_frentes=       float(row.get("NUM_FRENTES", 0)),
                ancho_cm=          float(row.get("ANCHO", 0)),
                alto_cm=           float(row.get("ALTO", 0)),
                ancho_ocupado_cm=  float(row.get("ANCHO_OCUPADO_CM", 0)),
                x_inicio_cm=       _safe_float(row.get("X_INICIO_CM")),
                x_fin_cm=          _safe_float(row.get("X_FIN_CM")),
                flag_no_colocado=  no_col,
            ))

        _jobs[job_id] = JobResult(
            job_id=job_id,
            status="done",
            solver="heuristico_v1",
            score=           _safe_float(score),
            score_z=         _safe_int(z_star),
            score_zh=        _safe_int(z_h),
            total_productos= total,
            colocados=       colocados,
            no_colocados=    no_colocados,
            charolas_exceden_ancho= val.get("charolas_que_exceden_ancho"),
            posiciones_duplicadas=  val.get("posiciones_duplicadas"),
            ocupacion_media_pct=    val.get("ocupacion_media_%"),
            results=         productos,
        )

    except Exception as exc:  # noqa: BLE001
        _jobs[job_id] = JobResult(job_id=job_id, status="error", solver=str(exc))


@router.post("", response_model=OptimizeResponse)
async def optimize(payload: OptimizeRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    _jobs[job_id] = JobResult(job_id=job_id, status="pending")

    background_tasks.add_task(
        _run_solver,
        job_id,
        payload.file_id,
    )

    return OptimizeResponse(job_id=job_id, status="pending")


@router.get("/result/{job_id}", response_model=JobResult)
async def get_result(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"job_id '{job_id}' no encontrado")
    return job
