from fastapi import APIRouter
from solver.schemas import OptimizeRequest, OptimizeResponse

router = APIRouter(prefix="/optimize", tags=["optimize"])


@router.post("/", response_model=OptimizeResponse)
async def optimize(payload: OptimizeRequest):
    # TODO: call solver
    raise NotImplementedError
