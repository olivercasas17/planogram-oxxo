from fastapi import APIRouter, UploadFile, File

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/")
async def upload_file(file: UploadFile = File(...)):
    # TODO: parse and store uploaded planogram data
    raise NotImplementedError
