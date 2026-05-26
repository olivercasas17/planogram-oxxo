"""
Integration tests for the Planogram OXXO API.

TestClient runs FastAPI BackgroundTasks synchronously, so the job result
is available immediately after POST /api/optimize returns.
"""

import pathlib

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

_CSV_PATH = pathlib.Path(__file__).parents[2] / "data" / "samples" / "ejemplo_planograma.csv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _upload_csv() -> dict:
    """POST the real CSV and return the parsed JSON response."""
    with _CSV_PATH.open("rb") as f:
        resp = client.post("/api/upload", files={"file": ("ejemplo_planograma.csv", f, "text/csv")})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _optimize(file_id: str, seg: str = "BCO", mue: str = "CF",
              tam: float = 4.0, dir_: str = "ID") -> dict:
    """POST /api/optimize and return the parsed JSON response."""
    resp = client.post("/api/optimize", json={
        "file_id": file_id,
        "segmento_id": seg,
        "mueble_id": mue,
        "tamaño": tam,
        "direccion": dir_,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def upload_response():
    assert _CSV_PATH.exists(), f"CSV de muestra no encontrado: {_CSV_PATH}"
    return _upload_csv()


@pytest.fixture(scope="module")
def optimize_response(upload_response):
    return _optimize(upload_response["file_id"])


@pytest.fixture(scope="module")
def job_result(optimize_response):
    job_id = optimize_response["job_id"]
    resp = client.get(f"/api/optimize/result/{job_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# POST /api/upload
# ---------------------------------------------------------------------------

class TestUpload:

    def test_status_200(self, upload_response):
        # fixture already asserts 200; just confirm it reached here
        assert upload_response is not None

    def test_devuelve_file_id(self, upload_response):
        assert "file_id" in upload_response
        assert isinstance(upload_response["file_id"], str)
        assert len(upload_response["file_id"]) > 0

    def test_devuelve_filename(self, upload_response):
        assert upload_response["filename"] == "ejemplo_planograma.csv"

    def test_devuelve_configuraciones(self, upload_response):
        assert "configuraciones" in upload_response
        assert isinstance(upload_response["configuraciones"], list)
        assert len(upload_response["configuraciones"]) > 0

    def test_configuracion_tiene_campos_requeridos(self, upload_response):
        for cfg in upload_response["configuraciones"]:
            assert "segmento_id" in cfg
            assert "mueble_id" in cfg
            assert "tamaño_post" in cfg
            assert "direccion_lego_id" in cfg

    def test_configuraciones_contiene_combinacion_esperada(self, upload_response):
        combos = {
            (c["segmento_id"], c["mueble_id"], c["tamaño_post"], c["direccion_lego_id"])
            for c in upload_response["configuraciones"]
        }
        assert ("BCO", "CF", 4.0, "ID") in combos

    def test_csv_invalido_devuelve_422(self):
        """Un archivo sin las columnas requeridas debe retornar 422."""
        bad_csv = b"col_a,col_b\n1,2\n"
        resp = client.post(
            "/api/upload",
            files={"file": ("bad.csv", bad_csv, "text/csv")},
        )
        assert resp.status_code == 422

    def test_archivo_vacio_devuelve_400(self):
        resp = client.post(
            "/api/upload",
            files={"file": ("empty.csv", b"", "text/csv")},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /api/optimize
# ---------------------------------------------------------------------------

class TestOptimize:

    def test_status_200(self, optimize_response):
        assert optimize_response is not None

    def test_devuelve_job_id(self, optimize_response):
        assert "job_id" in optimize_response
        assert isinstance(optimize_response["job_id"], str)
        assert len(optimize_response["job_id"]) > 0

    def test_status_inicial_pending(self, optimize_response):
        # The response from POST is always "pending"
        assert optimize_response["status"] == "pending"

    def test_file_id_invalido_no_bloquea_respuesta(self, upload_response):
        """POST with an unknown file_id still returns 200 (job is async)."""
        resp = client.post("/api/optimize", json={
            "file_id": "no-existe",
            "segmento_id": "BCO",
            "mueble_id": "CF",
            "tamaño": 4.0,
            "direccion": "ID",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending"

    def test_jobs_distintos_tienen_job_ids_distintos(self, upload_response):
        r1 = _optimize(upload_response["file_id"])
        r2 = _optimize(upload_response["file_id"])
        assert r1["job_id"] != r2["job_id"]


# ---------------------------------------------------------------------------
# GET /api/optimize/result/{job_id}
# ---------------------------------------------------------------------------

class TestJobResult:

    def test_status_200(self, job_result):
        assert job_result is not None

    def test_status_done(self, job_result):
        # BackgroundTasks run synchronously inside TestClient
        assert job_result["status"] == "done"

    def test_tiene_job_id(self, job_result):
        assert "job_id" in job_result
        assert isinstance(job_result["job_id"], str)

    def test_tiene_solver(self, job_result):
        assert job_result.get("solver") == "toy_greedy_v1"

    def test_score_entre_0_y_1(self, job_result):
        score = job_result.get("score")
        assert score is not None
        assert 0.0 <= score <= 1.0

    def test_tiene_results(self, job_result):
        assert "results" in job_result
        assert isinstance(job_result["results"], list)

    def test_totales_presentes(self, job_result):
        assert "total_planogrupos" in job_result
        assert "asignados" in job_result
        assert "sin_asignar" in job_result

    def test_totales_consistentes(self, job_result):
        total = job_result["total_planogrupos"]
        asig = job_result["asignados"]
        sin = job_result["sin_asignar"]
        assert asig + sin == total
        assert total == len(job_result["results"])

    def test_cada_result_tiene_campos_requeridos(self, job_result):
        for item in job_result["results"]:
            assert "planogrupo" in item
            assert "charola" in item
            assert "ubicacion_bandeja" in item
            assert "ancho_usado_cm" in item

    def test_charola_es_int(self, job_result):
        for item in job_result["results"]:
            assert isinstance(item["charola"], int)

    def test_ubicacion_bandeja_es_int(self, job_result):
        for item in job_result["results"]:
            assert isinstance(item["ubicacion_bandeja"], int)

    def test_job_invalido_devuelve_error_done(self):
        """A job launched with a bad file_id should end in 'error' status."""
        resp = client.post("/api/optimize", json={
            "file_id": "no-existe",
            "segmento_id": "BCO",
            "mueble_id": "CF",
            "tamaño": 4.0,
            "direccion": "ID",
        })
        bad_job_id = resp.json()["job_id"]
        result = client.get(f"/api/optimize/result/{bad_job_id}")
        assert result.status_code == 200
        assert result.json()["status"] == "error"


# ---------------------------------------------------------------------------
# 404 — job_id que no existe
# ---------------------------------------------------------------------------

class TestNotFound:

    def test_job_id_inexistente_devuelve_404(self):
        resp = client.get("/api/optimize/result/id-que-no-existe")
        assert resp.status_code == 404

    def test_404_devuelve_detail(self):
        resp = client.get("/api/optimize/result/id-que-no-existe")
        assert "detail" in resp.json()

    def test_404_mensaje_menciona_job_id(self):
        resp = client.get("/api/optimize/result/id-que-no-existe")
        assert "id-que-no-existe" in resp.json()["detail"]
