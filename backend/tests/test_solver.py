import io
import pathlib
import pandas as pd
import pytest
from solver.toy_solver import toy_solve
from solver.schemas import (
    REQUIRED_COLUMNS,
    MissingColumnsError,
    validate_csv,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_df(rows: list[dict]) -> pd.DataFrame:
    """Construye un DataFrame con las columnas que espera toy_solve."""
    return pd.DataFrame(rows)


@pytest.fixture
def df_basico():
    """Dos planogrupos que caben holgadamente en una sola charola."""
    return _make_df([
        {
            "SEGMENTO_ID": "SEG1", "MUEBLE_ID": "MUE1",
            "TAMAÑO_POST": 1.0, "DIRECCION_LEGO_ID": "IZQ",
            "CHAROLA": 1, "Width": 200.0, "Height": 50.0,
            "PLANOGRUPO": "PG-A", "ANCHO": 30.0, "ALTO": 20.0,
        },
        {
            "SEGMENTO_ID": "SEG1", "MUEBLE_ID": "MUE1",
            "TAMAÑO_POST": 1.0, "DIRECCION_LEGO_ID": "IZQ",
            "CHAROLA": 1, "Width": 200.0, "Height": 50.0,
            "PLANOGRUPO": "PG-B", "ANCHO": 40.0, "ALTO": 15.0,
        },
    ])


@pytest.fixture
def df_sin_espacio():
    """Planogrupo cuyo ancho supera la capacidad de todas las charolas."""
    return _make_df([
        {
            "SEGMENTO_ID": "SEG1", "MUEBLE_ID": "MUE1",
            "TAMAÑO_POST": 1.0, "DIRECCION_LEGO_ID": "IZQ",
            "CHAROLA": 1, "Width": 10.0, "Height": 50.0,
            "PLANOGRUPO": "PG-GRANDE", "ANCHO": 999.0, "ALTO": 20.0,
        },
    ])


@pytest.fixture
def df_altura_incompatible():
    """Planogrupo más alto que la charola disponible."""
    return _make_df([
        {
            "SEGMENTO_ID": "SEG1", "MUEBLE_ID": "MUE1",
            "TAMAÑO_POST": 1.0, "DIRECCION_LEGO_ID": "IZQ",
            "CHAROLA": 1, "Width": 200.0, "Height": 10.0,
            "PLANOGRUPO": "PG-ALTO", "ANCHO": 30.0, "ALTO": 50.0,
        },
    ])


# ---------------------------------------------------------------------------
# Contrato de la respuesta
# ---------------------------------------------------------------------------

class TestContrato:
    """El dict devuelto siempre debe tener las claves del contrato."""

    def test_claves_top_level(self, df_basico):
        out = toy_solve(df_basico, "SEG1", "MUE1", 1.0, "IZQ")
        assert "solver" in out
        assert "score" in out
        assert "results" in out

    def test_solver_flag(self, df_basico):
        out = toy_solve(df_basico, "SEG1", "MUE1", 1.0, "IZQ")
        assert out["solver"] == "toy_greedy_v1"

    def test_score_rango(self, df_basico):
        out = toy_solve(df_basico, "SEG1", "MUE1", 1.0, "IZQ")
        assert 0.0 <= out["score"] <= 1.0

    def test_results_es_lista(self, df_basico):
        out = toy_solve(df_basico, "SEG1", "MUE1", 1.0, "IZQ")
        assert isinstance(out["results"], list)

    def test_items_tienen_claves_requeridas(self, df_basico):
        out = toy_solve(df_basico, "SEG1", "MUE1", 1.0, "IZQ")
        for item in out["results"]:
            assert "planogrupo" in item
            assert "charola" in item
            assert "ubicacion_bandeja" in item
            assert "ancho_usado_cm" in item


# ---------------------------------------------------------------------------
# Casos funcionales
# ---------------------------------------------------------------------------

class TestCasosFuncionales:

    def test_asigna_todos_cuando_hay_espacio(self, df_basico):
        out = toy_solve(df_basico, "SEG1", "MUE1", 1.0, "IZQ")
        assert out["asignados"] == 2
        assert out["sin_asignar"] == 0
        assert out["score"] == 1.0

    def test_sin_asignar_cuando_no_hay_espacio(self, df_sin_espacio):
        out = toy_solve(df_sin_espacio, "SEG1", "MUE1", 1.0, "IZQ")
        assert out["sin_asignar"] >= 1
        sin_asignar = [r for r in out["results"] if r["charola"] == -1]
        assert len(sin_asignar) >= 1

    def test_sin_asignar_por_altura(self, df_altura_incompatible):
        out = toy_solve(df_altura_incompatible, "SEG1", "MUE1", 1.0, "IZQ")
        assert out["sin_asignar"] == 1

    def test_total_planogrupos_coincide_con_results(self, df_basico):
        out = toy_solve(df_basico, "SEG1", "MUE1", 1.0, "IZQ")
        assert out["total_planogrupos"] == len(out["results"])

    def test_asignados_mas_sin_asignar_igual_total(self, df_basico):
        out = toy_solve(df_basico, "SEG1", "MUE1", 1.0, "IZQ")
        assert out["asignados"] + out["sin_asignar"] == out["total_planogrupos"]


# ---------------------------------------------------------------------------
# Combinación sin datos
# ---------------------------------------------------------------------------

class TestSinDatos:

    def test_combinacion_inexistente_devuelve_error(self, df_basico):
        out = toy_solve(df_basico, "NOSEG", "NOMUE", 9.9, "DER")
        assert "error" in out
        assert out["results"] == []


# ---------------------------------------------------------------------------
# validate_csv
# ---------------------------------------------------------------------------

def _csv_bytes(df: pd.DataFrame) -> bytes:
    """Serializa el DataFrame a bytes UTF-8 (sin BOM), que es lo que validate_csv espera."""
    return df.to_csv(index=False).encode("utf-8")


def _full_row(**overrides) -> dict:
    """Fila con todas las columnas requeridas; sobreescribe con kwargs."""
    base = {
        "SEGMENTO_ID": "SEG1", "MUEBLE_ID": "MUE1", "PLANOGRUPO": "PG-A",
        "TAMAÑO_POST": 1.0, "DIRECCION_LEGO_ID": "IZQ",
        "CHAROLA": 1, "UBICACION_BANDEJA": 1,
        "ANCHO": 30.0, "ALTO": 20.0,
        "Width": 200.0, "Height": 50.0,
    }
    base.update(overrides)
    return base


class TestValidateCsv:

    def test_csv_valido_retorna_dataframe(self):
        df = pd.DataFrame([_full_row()])
        result = validate_csv(_csv_bytes(df))
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

    def test_todas_las_columnas_requeridas_presentes(self):
        df = pd.DataFrame([_full_row()])
        result = validate_csv(_csv_bytes(df))
        for col in REQUIRED_COLUMNS:
            assert col in result.columns

    def test_columnas_extra_permitidas(self):
        df = pd.DataFrame([_full_row(EXTRA_COL="valor")])
        result = validate_csv(_csv_bytes(df))
        assert "EXTRA_COL" in result.columns

    def test_falta_una_columna_lanza_error(self):
        df = pd.DataFrame([_full_row()])
        df = df.drop(columns=["PLANOGRUPO"])
        with pytest.raises(MissingColumnsError) as exc_info:
            validate_csv(_csv_bytes(df))
        assert "PLANOGRUPO" in exc_info.value.missing

    def test_faltan_varias_columnas_lista_completa(self):
        df = pd.DataFrame([_full_row()])
        df = df.drop(columns=["ANCHO", "ALTO", "Width"])
        with pytest.raises(MissingColumnsError) as exc_info:
            validate_csv(_csv_bytes(df))
        assert set(exc_info.value.missing) == {"ANCHO", "ALTO", "Width"}

    def test_error_menciona_columnas_faltantes_en_mensaje(self):
        df = pd.DataFrame([_full_row()])
        df = df.drop(columns=["SEGMENTO_ID"])
        with pytest.raises(MissingColumnsError, match="SEGMENTO_ID"):
            validate_csv(_csv_bytes(df))

    def test_csv_vacio_con_headers_validos_retorna_df_vacio(self):
        df = pd.DataFrame(columns=REQUIRED_COLUMNS)
        result = validate_csv(_csv_bytes(df))
        assert len(result) == 0

    def test_archivo_vacio_lanza_valueerror(self):
        # pandas lanza EmptyDataError con latin1 y archivo vacío
        with pytest.raises(ValueError, match="No se pudo leer"):
            validate_csv(b"")

    def test_acentos_en_datos_no_rompen_lectura(self):
        """Caracteres con acento en valores de datos deben preservarse (UTF-8)."""
        df = pd.DataFrame([_full_row(PLANOGRUPO="Refresco Área")])
        result = validate_csv(_csv_bytes(df))
        assert result["PLANOGRUPO"].iloc[0] == "Refresco Área"

    def test_bom_utf8_se_elimina(self):
        """Un archivo con BOM UTF-8 debe leerse igual que sin BOM."""
        bom = b"\xef\xbb\xbf"
        df = pd.DataFrame([_full_row()])
        sin_bom = _csv_bytes(df)
        result = validate_csv(bom + sin_bom)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Fixture: archivo CSV real de OXXO
# ---------------------------------------------------------------------------

_SAMPLES_DIR = pathlib.Path(__file__).parents[2] / "data" / "samples"
_CSV_PATH = _SAMPLES_DIR / "ejemplo_planograma.csv"


@pytest.fixture(scope="module")
def df_planograma():
    """DataFrame cargado desde el archivo CSV real de OXXO."""
    assert _CSV_PATH.exists(), (
        f"Archivo de muestra no encontrado: {_CSV_PATH}\n"
        "Coloca 'ejemplo_planograma.csv' en data/samples/ antes de correr estos tests."
    )
    content = _CSV_PATH.read_bytes()
    return validate_csv(content)


# ---------------------------------------------------------------------------
# Tests con el CSV real
# ---------------------------------------------------------------------------

class TestToyConCsvReal:
    """
    Usa data/samples/ejemplo_planograma.csv como fixture.
    Combos válidos presentes en el archivo: (BCO|CLA|HRN, CF, [3.0..5.0], DI|ID).
    """

    # ---- contrato de respuesta ----

    def test_devuelve_dict(self, df_planograma):
        out = toy_solve(df_planograma, "BCO", "CF", 4.0, "DI")
        assert isinstance(out, dict)

    def test_llave_solver_presente(self, df_planograma):
        out = toy_solve(df_planograma, "BCO", "CF", 4.0, "DI")
        assert "solver" in out

    def test_llave_score_presente(self, df_planograma):
        out = toy_solve(df_planograma, "BCO", "CF", 4.0, "DI")
        assert "score" in out

    def test_llave_results_presente(self, df_planograma):
        out = toy_solve(df_planograma, "BCO", "CF", 4.0, "DI")
        assert "results" in out

    def test_results_es_lista_no_vacia(self, df_planograma):
        out = toy_solve(df_planograma, "BCO", "CF", 4.0, "DI")
        assert isinstance(out["results"], list)
        assert len(out["results"]) > 0

    # ---- claves en cada resultado ----

    def test_cada_resultado_tiene_charola(self, df_planograma):
        out = toy_solve(df_planograma, "BCO", "CF", 4.0, "DI")
        for item in out["results"]:
            assert "charola" in item, f"Falta 'charola' en: {item}"

    def test_cada_resultado_tiene_ubicacion_bandeja(self, df_planograma):
        out = toy_solve(df_planograma, "BCO", "CF", 4.0, "DI")
        for item in out["results"]:
            assert "ubicacion_bandeja" in item, f"Falta 'ubicacion_bandeja' en: {item}"

    def test_cada_resultado_tiene_planogrupo(self, df_planograma):
        out = toy_solve(df_planograma, "BCO", "CF", 4.0, "DI")
        for item in out["results"]:
            assert "planogrupo" in item

    def test_cada_resultado_tiene_ancho_usado_cm(self, df_planograma):
        out = toy_solve(df_planograma, "BCO", "CF", 4.0, "DI")
        for item in out["results"]:
            assert "ancho_usado_cm" in item

    # ---- integridad numérica ----

    def test_score_entre_0_y_1(self, df_planograma):
        out = toy_solve(df_planograma, "BCO", "CF", 4.0, "DI")
        assert 0.0 <= out["score"] <= 1.0

    def test_totales_consistentes(self, df_planograma):
        out = toy_solve(df_planograma, "BCO", "CF", 4.0, "DI")
        assert out["asignados"] + out["sin_asignar"] == out["total_planogrupos"]
        assert out["total_planogrupos"] == len(out["results"])

    def test_charola_es_int(self, df_planograma):
        out = toy_solve(df_planograma, "BCO", "CF", 4.0, "DI")
        for item in out["results"]:
            assert isinstance(item["charola"], int)

    def test_ubicacion_bandeja_es_int(self, df_planograma):
        out = toy_solve(df_planograma, "BCO", "CF", 4.0, "DI")
        for item in out["results"]:
            assert isinstance(item["ubicacion_bandeja"], int)

    # ---- variedad de combinaciones ----

    @pytest.mark.parametrize("seg,mue,tam,dir_", [
        ("BCO", "CF", 4.0, "ID"),
        ("CLA", "CF", 5.0, "ID"),
        ("HRN", "CF", 3.0, "DI"),
    ])
    def test_otras_combinaciones_validas(self, df_planograma, seg, mue, tam, dir_):
        out = toy_solve(df_planograma, seg, mue, tam, dir_)
        assert "solver" in out
        assert "score" in out
        assert isinstance(out["results"], list)

    def test_combinacion_inexistente_retorna_error(self, df_planograma):
        out = toy_solve(df_planograma, "ZZZ", "XX", 9.9, "DI")
        assert "error" in out
        assert out["results"] == []
