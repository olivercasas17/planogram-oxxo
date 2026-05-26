# backend/solver/toy_solver.py

import pandas as pd
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ToyResult:
    planogrupo: str
    charola: int
    ubicacion_bandeja: int
    ancho_usado: float
    score: float = 0.72   # score ficticio para que la UI lo muestre

def toy_solve(df: pd.DataFrame, segmento_id: str, mueble_id: str,
              tamaño: float, direccion: str) -> dict:
    """
    Solver heurístico (greedy) que reemplaza al MILP mientras no está listo.
    Mismo contrato de input/output que el solver real.
    """

    # 1. Filtrar el formato solicitado
    mask = (
        (df["SEGMENTO_ID"].str.strip() == segmento_id) &
        (df["MUEBLE_ID"].str.strip() == mueble_id) &
        (df["TAMAÑO_POST"].astype(float) == tamaño) &
        (df["DIRECCION_LEGO_ID"].str.strip() == direccion)
    )
    subset = df[mask].copy()

    if subset.empty:
        return {"error": "No hay datos para esa combinación", "results": []}

    # 2. Obtener charolas disponibles con sus capacidades
    charolas = (
        subset[["CHAROLA", "Width", "Height"]]
        .drop_duplicates("CHAROLA")
        .sort_values("CHAROLA")
    )

    # 3. Obtener planogrupos únicos con su ancho y alto máximo
    grupos = (
        subset.groupby("PLANOGRUPO")
        .agg(ancho=("ANCHO", "max"), alto=("ALTO", "max"))
        .reset_index()
        .sort_values("ancho", ascending=False)   # greedy: primero los más anchos
    )

    # 4. Asignar greedy
    capacidad_restante = {
        int(row["CHAROLA"]): float(row["Width"])
        for _, row in charolas.iterrows()
    }
    altura_charola = {
        int(row["CHAROLA"]): float(row["Height"])
        for _, row in charolas.iterrows()
    }

    results = []
    posicion_en_charola = {c: 1 for c in capacidad_restante}

    for _, grupo in grupos.iterrows():
        nombre = grupo["planogrupo"] if "planogrupo" in grupo else grupo["PLANOGRUPO"]
        ancho_g = float(grupo["ancho"])
        alto_g  = float(grupo["alto"])

        asignado = False
        for charola_id in sorted(capacidad_restante.keys()):
            # Compatibilidad de altura
            if alto_g > altura_charola[charola_id]:
                continue
            # Compatibilidad de ancho
            if capacidad_restante[charola_id] >= ancho_g:
                results.append(ToyResult(
                    planogrupo=nombre,
                    charola=charola_id,
                    ubicacion_bandeja=posicion_en_charola[charola_id],
                    ancho_usado=ancho_g,
                ))
                capacidad_restante[charola_id] -= ancho_g
                posicion_en_charola[charola_id] += 1
                asignado = True
                break

        if not asignado:
            # No cupó en ninguna charola — lo registramos igual para no romper la UI
            results.append(ToyResult(
                planogrupo=nombre,
                charola=-1,           # -1 = sin asignar
                ubicacion_bandeja=-1,
                ancho_usado=ancho_g,
                score=0.0,
            ))

    # 5. Calcular score ficticio pero creíble
    asignados = sum(1 for r in results if r.charola != -1)
    score_global = round(asignados / len(results), 2) if results else 0.0

    return {
        "solver": "toy_greedy_v1",        # flag para saber que es el toy
        "score": score_global,
        "total_planogrupos": len(results),
        "asignados": asignados,
        "sin_asignar": len(results) - asignados,
        "results": [
            {
                "planogrupo": r.planogrupo,
                "charola": r.charola,
                "ubicacion_bandeja": r.ubicacion_bandeja,
                "ancho_usado_cm": r.ancho_usado,
            }
            for r in results
        ]
    }