"""
Tests unitarios del algoritmo heurístico (solver/algoritmo.py).

Cubre:
  - Contrato del DataFrame de salida (columnas, tipos, attrs)
  - Restricción de ancho por charola (≤ 55 cm)
  - Sin posiciones duplicadas (c, j) por grupo
  - Fase 2 repara sobrecupo correctamente
  - Productos no colocados marcados con FLAG_NO_COLOCADO=True
  - Validación post-heurístico con la función validar()
"""

import pathlib

import numpy as np
import pandas as pd
import pytest

from solver.algoritmo import (
    ANCHO_CHAROLA_CM,
    COLS_FORMATO,
    planogramar_heuristico,
    validar,
)
from solver.schemas import REQUIRED_COLUMNS, MissingColumnsError, validate_csv


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_grupo(n_productos: int, ancho: float, tamano_post: float = 3.0,
                direccion: str = "DI", segmento: str = "BCO") -> pd.DataFrame:
    """
    Crea un DataFrame de un único formato con n_productos.
    Los históricos (CHAROLA, UBICACION_BANDEJA) se distribuyen 1 producto por slot,
    empezando en charola 1, posición 1..n_productos.
    Cada producto tiene ancho `ancho` cm (NUM_FRENTES=1, SEPARADOR=0).
    """
    rows = []
    for i in range(n_productos):
        rows.append({
            "SEGMENTO_ID":       segmento,
            "MUEBLE_ID":         "CF",
            "PLANOGRUPO":        "PG-Test",
            "TAMANO_POST":       tamano_post,
            "DIRECCION_LEGO_ID": direccion,
            "CONJUNTO_ID":       "TST",
            "CHAROLA":           1,           # todos quieren ir a charola 1
            "UBICACION_BANDEJA": i + 1,
            "NUM_FRENTES":       1,
            "ANCHO":             ancho,
            "ALTO":              25.0,
            "SEPARADOR":         0,
        })
    return pd.DataFrame(rows)


def _make_multicharola(n_charolas: int, productos_por_charola: int,
                       ancho: float, tamano_post: float = 3.0) -> pd.DataFrame:
    """Crea un formato con productos distribuidos en n_charolas charolas."""
    rows = []
    for c in range(1, n_charolas + 1):
        for j in range(1, productos_por_charola + 1):
            rows.append({
                "SEGMENTO_ID":       "BCO",
                "MUEBLE_ID":         "CF",
                "PLANOGRUPO":        "PG-Multi",
                "TAMANO_POST":       tamano_post,
                "DIRECCION_LEGO_ID": "DI",
                "CONJUNTO_ID":       "TST",
                "CHAROLA":           c,
                "UBICACION_BANDEJA": j,
                "NUM_FRENTES":       1,
                "ANCHO":             ancho,
                "ALTO":              25.0,
                "SEPARADOR":         0,
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def df_real():
    csv_path = pathlib.Path(__file__).parents[2] / "data" / "samples" / "ejemplo_planograma.csv"
    assert csv_path.exists(), f"CSV de muestra no encontrado: {csv_path}"
    return validate_csv(csv_path.read_bytes())


@pytest.fixture(scope="module")
def resultado_real(df_real):
    return planogramar_heuristico(df_real)


# ---------------------------------------------------------------------------
# Contrato de salida (DataFrame)
# ---------------------------------------------------------------------------

class TestContratoSalida:

    def test_devuelve_dataframe(self):
        df = _make_grupo(5, ancho=8.0)
        out = planogramar_heuristico(df)
        assert isinstance(out, pd.DataFrame)

    def test_columnas_obligatorias_presentes(self):
        df = _make_grupo(5, ancho=8.0)
        out = planogramar_heuristico(df)
        for col in ("CHAROLA", "UBICACION_BANDEJA", "ANCHO_OCUPADO_CM",
                    "X_INICIO_CM", "X_FIN_CM", "FLAG_NO_COLOCADO"):
            assert col in out.columns, f"Falta columna: {col}"

    def test_attrs_score_presente(self):
        df = _make_grupo(5, ancho=8.0)
        out = planogramar_heuristico(df)
        assert "Score" in out.attrs
        assert "Z" in out.attrs
        assert "Z_H" in out.attrs

    def test_score_entre_0_y_1(self):
        df = _make_grupo(5, ancho=8.0)
        out = planogramar_heuristico(df)
        score = out.attrs["Score"]
        assert 0.0 <= score <= 1.0, f"Score fuera de rango: {score}"

    def test_flag_no_colocado_es_bool(self):
        df = _make_grupo(5, ancho=8.0)
        out = planogramar_heuristico(df)
        assert out["FLAG_NO_COLOCADO"].dtype == bool or \
               set(out["FLAG_NO_COLOCADO"].unique()).issubset({True, False})


# ---------------------------------------------------------------------------
# Restricción de ancho (≤ 55 cm) — BUG CRÍTICO REPORTADO
# ---------------------------------------------------------------------------

class TestRestriccionAncho:

    def test_ninguna_charola_excede_ancho_caso_holgado(self):
        """5 productos de 8 cm → 40 cm total, bien dentro de 55 cm."""
        df = _make_grupo(5, ancho=8.0)
        out = planogramar_heuristico(df)
        v = validar(out)
        assert v["charolas_que_exceden_ancho"] == 0

    def test_ninguna_charola_excede_ancho_caso_limite(self):
        """6 productos de 9 cm → 54 cm, justo por debajo de 55 cm."""
        df = _make_grupo(6, ancho=9.0)
        out = planogramar_heuristico(df)
        v = validar(out)
        assert v["charolas_que_exceden_ancho"] == 0

    def test_fase2_repara_sobrecupo(self):
        """8 productos de 10 cm en charola 1 → 80 cm > 55 cm.
        La Fase 2 debe expulsar productos hasta que ancho ≤ 55 cm."""
        df = _make_grupo(8, ancho=10.0)
        out = planogramar_heuristico(df)
        v = validar(out)
        assert v["charolas_que_exceden_ancho"] == 0, \
            f"Fase 2 no reparó: {v['charolas_que_exceden_ancho']} charola(s) exceden"

    def test_expulsados_marcados_no_colocados(self):
        """Los productos que no caben deben llevar FLAG_NO_COLOCADO=True."""
        # 8 × 10 cm = 80 cm en 1 charola → al menos 2 no caben (55 cm / 10 = 5.5 → max 5)
        df = _make_grupo(8, ancho=10.0)
        out = planogramar_heuristico(df)
        no_col = out["FLAG_NO_COLOCADO"].sum()
        assert no_col >= 2, f"Se esperaban ≥2 no colocados, hubo {no_col}"

    def test_ancho_por_charola_valido_en_multicharola(self):
        """3 charolas × 5 productos de 9 cm → 45 cm por charola, deben caber."""
        df = _make_multicharola(n_charolas=3, productos_por_charola=5, ancho=9.0)
        out = planogramar_heuristico(df)
        v = validar(out)
        assert v["charolas_que_exceden_ancho"] == 0

    def test_ancho_por_charola_no_excede_con_csv_real(self, resultado_real):
        v = validar(resultado_real)
        assert v["charolas_que_exceden_ancho"] == 0, \
            f"CSV real: {v['charolas_que_exceden_ancho']} charola(s) exceden 55 cm"


# ---------------------------------------------------------------------------
# Posiciones duplicadas — BUG CRÍTICO REPORTADO
# ---------------------------------------------------------------------------

class TestSinDuplicados:

    def test_sin_posiciones_duplicadas_caso_simple(self):
        df = _make_grupo(5, ancho=8.0)
        out = planogramar_heuristico(df)
        v = validar(out)
        assert v["posiciones_duplicadas"] == 0

    def test_sin_posiciones_duplicadas_sobrecupo(self):
        """Incluso cuando la Fase 2 expulsa productos no deben quedar duplicados."""
        df = _make_grupo(8, ancho=10.0)
        out = planogramar_heuristico(df)
        v = validar(out)
        assert v["posiciones_duplicadas"] == 0

    def test_sin_posiciones_duplicadas_multicharola(self):
        df = _make_multicharola(n_charolas=3, productos_por_charola=4, ancho=8.0)
        out = planogramar_heuristico(df)
        v = validar(out)
        assert v["posiciones_duplicadas"] == 0

    def test_sin_posiciones_duplicadas_csv_real(self, resultado_real):
        v = validar(resultado_real)
        assert v["posiciones_duplicadas"] == 0, \
            f"CSV real: {v['posiciones_duplicadas']} posicion(es) duplicada(s)"


# ---------------------------------------------------------------------------
# Productos no colocados
# ---------------------------------------------------------------------------

class TestNoColocados:

    def test_todos_colocados_cuando_hay_espacio(self):
        """5 productos de 8 cm → 40 cm < 55 cm; todos deben colocarse."""
        df = _make_grupo(5, ancho=8.0)
        out = planogramar_heuristico(df)
        assert out["FLAG_NO_COLOCADO"].sum() == 0

    def test_hay_no_colocados_cuando_no_hay_espacio(self):
        """8 productos de 10 cm en una charola de 55 cm → máx. 5 caben."""
        df = _make_grupo(8, ancho=10.0)
        out = planogramar_heuristico(df)
        assert out["FLAG_NO_COLOCADO"].sum() >= 1

    def test_no_colocados_no_tienen_charola(self):
        """Productos con FLAG_NO_COLOCADO=True deben tener CHAROLA=NaN."""
        df = _make_grupo(8, ancho=10.0)
        out = planogramar_heuristico(df)
        no_col = out[out["FLAG_NO_COLOCADO"] == True]
        assert no_col["CHAROLA"].isna().all(), \
            "Productos no colocados tienen CHAROLA asignada"

    def test_colocados_tienen_charola_entera(self):
        """Productos colocados deben tener CHAROLA como entero válido."""
        df = _make_grupo(5, ancho=8.0)
        out = planogramar_heuristico(df)
        col = out[out["FLAG_NO_COLOCADO"] == False]
        assert col["CHAROLA"].notna().all()
        assert (col["CHAROLA"] >= 1).all()


# ---------------------------------------------------------------------------
# Score Z
# ---------------------------------------------------------------------------

class TestScoreZ:

    def test_score_1_cuando_todos_en_posicion_historica(self):
        """Con factor_ancho=1.0 y datos holgados, todos van a su posición histórica."""
        df = _make_multicharola(n_charolas=3, productos_por_charola=3, ancho=8.0)
        out = planogramar_heuristico(df, factor_ancho=1.0)
        assert out.attrs["Score"] == pytest.approx(1.0, abs=1e-6)

    def test_score_decrece_con_estres(self):
        """factor_ancho > 1 fuerza reparaciones → Score debe bajar."""
        df = _make_multicharola(n_charolas=2, productos_por_charola=4, ancho=7.0)
        s_normal = planogramar_heuristico(df, factor_ancho=1.0).attrs["Score"]
        s_estres = planogramar_heuristico(df, factor_ancho=2.0).attrs["Score"]
        assert s_estres <= s_normal

    def test_z_equal_zh_cuando_score_1(self):
        df = _make_multicharola(n_charolas=2, productos_por_charola=3, ancho=8.0)
        out = planogramar_heuristico(df, factor_ancho=1.0)
        assert out.attrs["Z"] == out.attrs["Z_H"]

    def test_csv_real_score_alto(self, resultado_real):
        """El CSV real en modo imitación (factor_ancho=1.0) debe tener Score≈1."""
        score = resultado_real.attrs["Score"]
        assert score >= 0.95, f"Score bajo en CSV real: {score:.4f}"


# ---------------------------------------------------------------------------
# validate_csv
# ---------------------------------------------------------------------------

def _csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def _full_row(**overrides) -> dict:
    base = {
        "MUEBLE_ID":         "CF",
        "PLANOGRUPO":        "PG-A",
        "CHAROLA":           1,
        "UBICACION_BANDEJA": 1,
        "ANCHO":             10.0,
        "ALTO":              25.0,
        "NUM_FRENTES":       1,
        "TAMANO_POST":       3.0,
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

    def test_columnas_opcionales_no_requeridas(self):
        """SEGMENTO_ID, DIRECCION_LEGO_ID, CONJUNTO_ID son opcionales."""
        df = pd.DataFrame([_full_row()])
        result = validate_csv(_csv_bytes(df))
        assert isinstance(result, pd.DataFrame)

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
        df = df.drop(columns=["ANCHO", "ALTO"])
        with pytest.raises(MissingColumnsError) as exc_info:
            validate_csv(_csv_bytes(df))
        assert set(exc_info.value.missing) == {"ANCHO", "ALTO"}

    def test_error_menciona_columnas_faltantes_en_mensaje(self):
        df = pd.DataFrame([_full_row()])
        df = df.drop(columns=["MUEBLE_ID"])
        with pytest.raises(MissingColumnsError, match="MUEBLE_ID"):
            validate_csv(_csv_bytes(df))

    def test_csv_vacio_con_headers_validos_retorna_df_vacio(self):
        df = pd.DataFrame(columns=REQUIRED_COLUMNS)
        result = validate_csv(_csv_bytes(df))
        assert len(result) == 0

    def test_archivo_vacio_lanza_valueerror(self):
        with pytest.raises(ValueError):
            validate_csv(b"")

    def test_acentos_en_datos_no_rompen_lectura(self):
        df = pd.DataFrame([_full_row(PLANOGRUPO="Refresco Área")])
        result = validate_csv(_csv_bytes(df))
        assert result["PLANOGRUPO"].iloc[0] == "Refresco Área"

    def test_bom_utf8_se_elimina(self):
        bom = b"\xef\xbb\xbf"
        df = pd.DataFrame([_full_row()])
        result = validate_csv(bom + _csv_bytes(df))
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
