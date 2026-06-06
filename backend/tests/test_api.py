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
    with _CSV_PATH.open("rb") as f:
        resp = client.post("/api/upload", files={"file": ("ejemplo_planograma.csv", f, "text/csv")})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _optimize(file_id: str) -> dict:
    resp = client.post("/api/optimize", json={"file_id": file_id})
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
        assert upload_response is not None

    def test_devuelve_file_id(self, upload_response):
        assert "file_id" in upload_response
        assert isinstance(upload_response["file_id"], str)
        assert len(upload_response["file_id"]) > 0

    def test_devuelve_filename(self, upload_response):
        assert upload_response["filename"] == "ejemplo_planograma.csv"

    def test_devuelve_total_productos(self, upload_response):
        assert "total_productos" in upload_response
        assert isinstance(upload_response["total_productos"], int)
        assert upload_response["total_productos"] > 0

    def test_devuelve_tiendas_de_segmento_id(self, upload_response):
        """tiendas debe contener valores de SEGMENTO_ID (BCO, CLA, HRN…), no CONJUNTO_ID."""
        assert "tiendas" in upload_response
        tiendas = upload_response["tiendas"]
        assert isinstance(tiendas, list)
        assert len(tiendas) > 0
        assert all(isinstance(t, str) for t in tiendas)
        # El CSV real tiene BCO, CLA, HRN — ningún valor de CONJUNTO_ID como 10MON
        for t in tiendas:
            assert t not in ("10MON", "RYX"), \
                f"tiendas contiene CONJUNTO_ID '{t}' en lugar de SEGMENTO_ID"

    def test_tiendas_ordenadas_alfabeticamente(self, upload_response):
        tiendas = upload_response["tiendas"]
        assert tiendas == sorted(tiendas)

    def test_csv_invalido_devuelve_422(self):
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
        assert optimize_response["status"] == "pending"

    def test_file_id_invalido_no_bloquea_respuesta(self):
        resp = client.post("/api/optimize", json={"file_id": "no-existe"})
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

    def test_status_done(self, job_result):
        assert job_result["status"] == "done"

    def test_tiene_job_id(self, job_result):
        assert "job_id" in job_result
        assert isinstance(job_result["job_id"], str)

    def test_tiene_solver(self, job_result):
        assert job_result.get("solver") == "heuristico_v1"

    def test_score_entre_0_y_1(self, job_result):
        score = job_result.get("score")
        assert score is not None
        assert 0.0 <= score <= 1.0

    def test_score_alto_en_modo_imitacion(self, job_result):
        """En modo imitación (factor_ancho=1.0) el score debe ser ≥ 0.95."""
        assert job_result["score"] >= 0.95

    def test_tiene_results(self, job_result):
        assert "results" in job_result
        assert isinstance(job_result["results"], list)
        assert len(job_result["results"]) > 0

    def test_totales_presentes(self, job_result):
        assert "total_productos" in job_result
        assert "colocados" in job_result
        assert "no_colocados" in job_result

    def test_totales_consistentes(self, job_result):
        total    = job_result["total_productos"]
        colocados = job_result["colocados"]
        no_col   = job_result["no_colocados"]
        assert colocados + no_col == total
        assert total == len(job_result["results"])

    def test_cada_result_tiene_campos_requeridos(self, job_result):
        for item in job_result["results"]:
            for campo in ("mueble_id", "planogrupo", "num_frentes",
                          "ancho_cm", "alto_cm", "ancho_ocupado_cm",
                          "flag_no_colocado"):
                assert campo in item, f"Falta campo '{campo}' en ProductoResult"

    def test_segmento_id_presente_en_results(self, job_result):
        """segmento_id debe venir en cada ProductoResult para el filtro del frontend."""
        for item in job_result["results"]:
            assert "segmento_id" in item

    def test_direccion_presente_en_results(self, job_result):
        """direccion debe venir en cada ProductoResult para el makeKey del dropdown."""
        for item in job_result["results"]:
            assert "direccion" in item

    def test_charola_int_o_none(self, job_result):
        for item in job_result["results"]:
            assert item["charola"] is None or isinstance(item["charola"], int)

    def test_ubicacion_bandeja_int_o_none(self, job_result):
        for item in job_result["results"]:
            assert item["ubicacion_bandeja"] is None or isinstance(item["ubicacion_bandeja"], int)

    def test_ninguna_charola_excede_ancho(self, job_result):
        """Restricción crítica: ninguna charola debe exceder 55 cm."""
        assert job_result.get("charolas_exceden_ancho") == 0, \
            f"charolas_exceden_ancho={job_result.get('charolas_exceden_ancho')}"

    def test_sin_posiciones_duplicadas(self, job_result):
        """No debe haber dos productos en la misma (charola, ubicacion_bandeja)."""
        assert job_result.get("posiciones_duplicadas") == 0, \
            f"posiciones_duplicadas={job_result.get('posiciones_duplicadas')}"

    def test_job_invalido_termina_en_error(self):
        resp = client.post("/api/optimize", json={"file_id": "no-existe"})
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
