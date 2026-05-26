import uuid
from fastapi import APIRouter, BackgroundTasks, HTTPException

from routers.upload import get_dataframe
from solver.toy_solver import toy_solve
from solver.schemas import (
    JobResult,
    OptimizeRequest,
    OptimizeResponse,
    PlanogrupoResult,
)

router = APIRouter(prefix="/optimize", tags=["optimize"])

# In-memory job store: job_id -> JobResult
_jobs: dict[str, JobResult] = {}


def _run_solver(job_id: str, file_id: str, segmento_id: str,
                mueble_id: str, tamaño: float, direccion: str) -> None:
    """Background task: run toy_solve and update job status."""
    _jobs[job_id] = JobResult(job_id=job_id, status="running")

    try:
        df = get_dataframe(file_id)
        raw = toy_solve(df, segmento_id, mueble_id, tamaño, direccion)

        if "error" in raw:
            _jobs[job_id] = JobResult(
                job_id=job_id,
                status="error",
                solver=raw.get("solver", "toy_greedy_v1"),
            )
            return

        _jobs[job_id] = JobResult(
            job_id=job_id,
            status="done",
            solver=raw["solver"],
            score=raw["score"],
            total_planogrupos=raw["total_planogrupos"],
            asignados=raw["asignados"],
            sin_asignar=raw["sin_asignar"],
            results=[
                PlanogrupoResult(
                    planogrupo=r["planogrupo"],
                    charola=r["charola"],
                    ubicacion_bandeja=r["ubicacion_bandeja"],
                    ancho_usado_cm=r["ancho_usado_cm"],
                )
                for r in raw["results"]
            ],
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
        payload.segmento_id,
        payload.mueble_id,
        payload.tamaño,
        payload.direccion,
    )

    return OptimizeResponse(job_id=job_id, status="pending")


@router.get("/result/{job_id}", response_model=JobResult)
async def get_result(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"job_id '{job_id}' no encontrado")
    return job
