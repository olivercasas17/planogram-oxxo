# -*- coding: utf-8 -*-
"""
================================================================================
 HEURÍSTICO DE ASIGNACIÓN — implementación fiel del algoritmo del equipo
================================================================================
Traducción a Python del documento "Método Heurístico de Asignación", adaptado a
NIVEL PRODUCTO (UPC/ITEM) y al esquema de entrada/salida acordado, para procesar
ejemplo_planograma.csv.

El algoritmo es un método de IMITACIÓN + REPARACIÓN: parte del acomodo histórico
del socio y lo ajusta para que sea factible, maximizando la similitud (score Z).
Por eso REQUIERE el histórico como referencia (X^H). En este código:

  • La "demanda" (qué productos colocar, con su ANCHO/ALTO/NUM_FRENTES) sale de
    las filas del CSV.
  • La referencia histórica X^H = las columnas CHAROLA / UBICACION_BANDEJA.
  • La SALIDA es un acomodo nuevo (CHAROLA / UBICACION_BANDEJA recalculadas).

Como Hc (altura de la charola) y Pj (ancho de la posición) NO vienen como
columnas, se reconstruyen del histórico:
  Hc[c]      = altura del producto más alto que el histórico puso en la charola c
  Pj[(c,j)]  = ancho efectivo del producto que el histórico puso en la posición j

Nota sobre las posiciones: en la realidad cada charola es una tira continua de
55 cm; "posición j" es un slot ORDINAL para casar con el histórico. Por eso la
restricción dura de ancho es la de la charola (R5, Wc); el ancho de posición Pj
(R7) se usa como SEÑAL dentro del Beneficio (qué tan bien llena el hueco), no
como tope rígido.

----------------------------------------------------------------------------
FASES (tal cual el documento):
  Fase 1  Construcción inicial : colocar cada producto en su posición histórica
                                  si es factible (libre, altura, compatibilidad).
  Fase 2  Reparación           : resolver conflictos de posición y exceso de
                                  ancho por charola (quitar el de menor aporte).
  Fase 3  Llenado              : llenar posiciones libres con el producto de mayor
                                  Beneficio = 0.5·Hg/Hc + 0.3·Wg/Pj + 0.2·X^H
  Fase 4  Mejora local         : swaps y reubicaciones mientras suba el score Z.
  Score  Z = Σ_{g,c,j} (X_{gcj} · X^H_{gcj})²   ;   Score = Z* / Z^H ∈ [0,1]
================================================================================
"""

import re
import numpy as np
import pandas as pd


# ==============================================================================
# PARÁMETROS / GEOMETRÍA
# ==============================================================================
ANCHO_CHAROLA_CM = 55.0
CHAROLAS_POR_TAMANO = {3.0: 18, 3.5: 20, 4.0: 24, 4.5: 26, 5.0: 30}
COLS_FORMATO = ["SEGMENTO_ID", "MUEBLE_ID", "PLANOGRUPO",
                "TAMANO_POST", "DIRECCION_LEGO_ID", "CONJUNTO_ID"]

# Pesos del Beneficio de la Fase 3 (documento del equipo)
W_ALTURA, W_ANCHO, W_HIST = 0.5, 0.3, 0.2


def num_charolas(tamano_post: float) -> int:
    t = round(float(tamano_post), 1)
    return CHAROLAS_POR_TAMANO.get(t, max(1, int(round(6 * t))))


# ==============================================================================
# CARGA ROBUSTA DEL CSV (BOM + encoding mixto) Y NORMALIZACIÓN DE NOMBRES
# ==============================================================================
def cargar_csv(ruta: str) -> pd.DataFrame:
    df = None
    for enc in ("utf-8-sig", "latin-1", "cp1252"):
        try:
            df = pd.read_csv(ruta, encoding=enc)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    if df is None:
        df = pd.read_csv(ruta, encoding="latin-1", encoding_errors="replace")
    df.columns = [re.sub(r"[^0-9A-Za-z_]", "", c) for c in df.columns]
    df = df.rename(columns={"TAMAO_POST": "TAMANO_POST",
                            "DISEO_REFERENCIA": "DISENO_REFERENCIA"})
    return df


# ==============================================================================
# ESTRUCTURA DE UNA INSTANCIA (un formato)
# ==============================================================================
class Instancia:
    """Productos + geometría (Hc, Pj, grid de slots) reconstruidos del histórico.

    factor_ancho : escala el ancho efectivo de los productos (simula más demanda
                   de frentes de la que cabe). 1.0 = datos tal cual.
    """

    def __init__(self, sub, n_charolas, ancho_charola=ANCHO_CHAROLA_CM,
                 factor_ancho=1.0):
        self.Wc = ancho_charola
        self.n_charolas = n_charolas

        sub = sub.reset_index(drop=True).copy()
        sep = sub["SEPARADOR"] if "SEPARADOR" in sub.columns else 0
        sub["W"] = (sub["ANCHO"] * sub["NUM_FRENTES"] + sep) * factor_ancho
        self.df = sub

        self.W = sub["W"].to_numpy(float)
        self.H = sub["ALTO"].to_numpy(float)
        self.frentes = sub["NUM_FRENTES"].to_numpy(float)
        self.c_hist = sub["CHAROLA"].to_numpy(int)            # X^H: charola
        self.j_hist = sub["UBICACION_BANDEJA"].to_numpy(int)  # X^H: posición
        self.mueble = sub["MUEBLE_ID"].astype(str).to_numpy()
        self.P = len(sub)

        # Hc[c] = producto más alto que el histórico puso en la charola c
        self.Hc = {}
        for c in range(1, n_charolas + 1):
            alturas = self.H[self.c_hist == c]
            self.Hc[c] = float(alturas.max()) if alturas.size else float(self.H.max())

        # Mueble de cada charola (del histórico) -> compatibilidad A_gc por tipo
        self.mueble_charola = {}
        for c in range(1, n_charolas + 1):
            mm = self.mueble[self.c_hist == c]
            self.mueble_charola[c] = mm[0] if mm.size else self.mueble[0]

        # Grid de slots (c, j) y ancho de posición Pj (del histórico, sin escalar)
        self.slots, self.Pj, self.Jmax = [], {}, {}
        Wsin = (sub["ANCHO"] * sub["NUM_FRENTES"] + sep).to_numpy(float)
        for c in range(1, n_charolas + 1):
            js = self.j_hist[self.c_hist == c]
            jmax = int(js.max()) if js.size else 0
            self.Jmax[c] = jmax
            for j in range(1, jmax + 1):
                self.slots.append((c, j))
                w_occ = Wsin[(self.c_hist == c) & (self.j_hist == j)]
                self.Pj[(c, j)] = float(w_occ[0]) if w_occ.size else self.Wc

    def compatible(self, p, c):
        """A_gc: producto p compatible con charola c (mismo tipo de mueble)."""
        return self.mueble[p] == self.mueble_charola[c]

    def prioridad(self, p):
        """Anchor SKUs primero: más frentes, luego más ancho."""
        return (self.frentes[p], self.W[p])

    def aporte_historico(self, p, c, j):
        """1 si (c,j) es la posición histórica de p (su contribución a Z)."""
        return int(self.c_hist[p] == c and self.j_hist[p] == j)


# ==============================================================================
# SOLUCIÓN (asignación producto <-> slot) Y SCORE
# ==============================================================================
class Solucion:
    def __init__(self, inst):
        self.inst = inst
        self.asig = {}                  # producto -> (c, j)
        self.ocupa = {}                 # (c, j)   -> producto
        self.ancho_usado = {c: 0.0 for c in range(1, inst.n_charolas + 1)}

    def libre(self, c, j):
        return (c, j) not in self.ocupa

    def colocar(self, p, c, j):
        self.asig[p] = (c, j); self.ocupa[(c, j)] = p
        self.ancho_usado[c] += self.inst.W[p]

    def quitar(self, p):
        c, j = self.asig.pop(p); del self.ocupa[(c, j)]
        self.ancho_usado[c] -= self.inst.W[p]
        return c, j

    def factible_altura(self, p, c):
        return self.inst.H[p] <= self.inst.Hc[c] + 1e-9

    def score_Z(self):
        """Z = Σ (X·X^H)² = nº de productos colocados en su posición histórica."""
        return sum(self.inst.aporte_historico(p, c, j) ** 2
                   for p, (c, j) in self.asig.items())


# ==============================================================================
# FASE 1 — CONSTRUCCIÓN INICIAL (colocar en posiciones históricas factibles)
# ==============================================================================
def fase1_construccion(inst, sol):
    disponibles = []
    orden = sorted(range(inst.P), key=lambda p: inst.prioridad(p), reverse=True)
    for p in orden:
        c, j = inst.c_hist[p], inst.j_hist[p]
        ok = ((c, j) in inst.Pj            # el slot existe en el grid
              and sol.libre(c, j)          # posición libre (R1)
              and sol.factible_altura(p, c)
              and inst.compatible(p, c))
        # El ancho por charola (Wc) NO se chequea aquí: se permite sobrecupo
        # temporal y lo repara la Fase 2 (como en el documento).
        if ok:
            sol.colocar(p, c, j)
        else:
            disponibles.append(p)
    return disponibles


# ==============================================================================
# FASE 2 — REPARACIÓN (conflictos ya evitados en F1; aquí: exceso de ancho)
# ==============================================================================
def fase2_reparacion(inst, sol, disponibles):
    for c in range(1, inst.n_charolas + 1):
        while sol.ancho_usado[c] > inst.Wc + 1e-9:
            en_c = [p for p, (cc, _) in sol.asig.items() if cc == c]
            if not en_c:
                break
            # menor aporte histórico primero; a igualdad, el más ancho (libera más)
            peor = min(en_c, key=lambda p: (inst.aporte_historico(p, *sol.asig[p]),
                                            -inst.W[p]))
            sol.quitar(peor)
            disponibles.append(peor)
    return disponibles


# ==============================================================================
# FASE 3 — LLENADO DE ESPACIOS VACÍOS (mayor Beneficio)
#   Beneficio(g,c,j) = 0.5·Hg/Hc + 0.3·Wg/Pj + 0.2·X^H_{gcj}
# ==============================================================================
def beneficio(inst, p, c, j):
    h = inst.H[p] / inst.Hc[c] if inst.Hc[c] > 0 else 0.0
    w = inst.W[p] / inst.Pj[(c, j)] if inst.Pj[(c, j)] > 0 else 0.0
    return (W_ALTURA * min(h, 1.0) + W_ANCHO * min(w, 1.0)
            + W_HIST * inst.aporte_historico(p, c, j))


def fase3_llenado(inst, sol, disponibles):
    disponibles = list(disponibles)
    libres = [s for s in inst.slots if sol.libre(*s)]
    for (c, j) in libres:
        if not disponibles:
            break
        cands = [p for p in disponibles
                 if sol.factible_altura(p, c) and inst.compatible(p, c)
                 and sol.ancho_usado[c] + inst.W[p] <= inst.Wc + 1e-9]
        if not cands:
            continue
        mejor = max(cands, key=lambda p: beneficio(inst, p, c, j))
        sol.colocar(mejor, c, j)
        disponibles.remove(mejor)
    return disponibles                  # los que sigan aquí no se pudieron colocar


# ==============================================================================
# FASE 4 — MEJORA LOCAL (swaps y reubicaciones que suban Z)
# ==============================================================================
def _delta_swap(inst, sol, p1, p2):
    c1, j1 = sol.asig[p1]; c2, j2 = sol.asig[p2]
    antes = inst.aporte_historico(p1, c1, j1) + inst.aporte_historico(p2, c2, j2)
    desp = inst.aporte_historico(p1, c2, j2) + inst.aporte_historico(p2, c1, j1)
    return desp - antes


def _swap_factible(inst, sol, p1, p2):
    c1, j1 = sol.asig[p1]; c2, j2 = sol.asig[p2]
    if not (sol.factible_altura(p1, c2) and sol.factible_altura(p2, c1)
            and inst.compatible(p1, c2) and inst.compatible(p2, c1)):
        return False
    if c1 != c2:
        n1 = sol.ancho_usado[c1] - inst.W[p1] + inst.W[p2]
        n2 = sol.ancho_usado[c2] - inst.W[p2] + inst.W[p1]
        if n1 > inst.Wc + 1e-9 or n2 > inst.Wc + 1e-9:
            return False
    return True


def fase4_mejora_local(inst, sol, max_pasadas=8):
    mejora, pasadas = True, 0
    while mejora and pasadas < max_pasadas:
        mejora = False; pasadas += 1

        # Reubicaciones: mover p a un slot libre si sube Z
        libres = [s for s in inst.slots if sol.libre(*s)]
        for p in list(sol.asig.keys()):
            c0, j0 = sol.asig[p]
            base = inst.aporte_historico(p, c0, j0)
            for (c, j) in libres:
                if (sol.factible_altura(p, c) and inst.compatible(p, c)
                        and sol.ancho_usado[c] + inst.W[p] <= inst.Wc + 1e-9
                        and inst.aporte_historico(p, c, j) > base):
                    sol.quitar(p); sol.colocar(p, c, j); mejora = True
                    break
            if mejora:
                break
        if mejora:
            continue

        # Swaps: intercambiar dos productos si sube Z
        ps = list(sol.asig.keys())
        for a in range(len(ps)):
            for b in range(a + 1, len(ps)):
                p1, p2 = ps[a], ps[b]
                if _delta_swap(inst, sol, p1, p2) > 0 and _swap_factible(inst, sol, p1, p2):
                    c1, j1 = sol.asig[p1]; c2, j2 = sol.asig[p2]
                    sol.quitar(p1); sol.quitar(p2)
                    sol.colocar(p1, c2, j2); sol.colocar(p2, c1, j1)
                    mejora = True
                    break
            if mejora:
                break
    return sol


# ==============================================================================
# ORQUESTADOR POR FORMATO  (sigue el pseudocódigo del documento)
# ==============================================================================
def heuristico_formato(sub, n_charolas, ancho_charola=ANCHO_CHAROLA_CM,
                       factor_ancho=1.0, mejora_local=True):
    inst = Instancia(sub, n_charolas, ancho_charola, factor_ancho)
    sol = Solucion(inst)

    disp = fase1_construccion(inst, sol)        # Fase 1
    disp = fase2_reparacion(inst, sol, disp)    # Fase 2
    disp = fase3_llenado(inst, sol, disp)       # Fase 3
    if mejora_local:
        fase4_mejora_local(inst, sol)           # Fase 4

    # --- Verificación de factibilidad post-fases ---
    # Si alguna charola sigue excediendo el ancho (no debería ocurrir porque la
    # Fase 2 lo repara, pero como salvaguarda explícita) se expulsan los productos
    # sobrantes marcándolos como no colocados en lugar de generar un acomodo inválido.
    for c in range(1, n_charolas + 1):
        while sol.ancho_usado[c] > ancho_charola + 1e-6:
            en_c = [p for p, (cc, _) in sol.asig.items() if cc == c]
            if not en_c:
                break
            peor = min(en_c, key=lambda p: (inst.aporte_historico(p, *sol.asig[p]),
                                            -inst.W[p]))
            sol.quitar(peor)
            disp.append(peor)

    # --- Construir el DataFrame de salida ---
    direccion = str(sub["DIRECCION_LEGO_ID"].iloc[0]).upper()
    izquierda = (direccion == "ID")             # ID: posición 1 a la izquierda
    filas = []
    for c in range(1, n_charolas + 1):
        en_c = sorted([(j, p) for (cc, j), p in sol.ocupa.items() if cc == c])
        x = 0.0
        for pos, (j, p) in enumerate(en_c, start=1):
            w = inst.W[p]
            if izquierda:
                x_ini, x_fin = x, x + w
            else:
                x_fin = ancho_charola - x; x_ini = x_fin - w
            rec = inst.df.loc[p].to_dict()
            rec.update({"CHAROLA": c, "UBICACION_BANDEJA": pos,
                        "ANCHO_OCUPADO_CM": round(float(w), 2),
                        "X_INICIO_CM": round(float(x_ini), 2),
                        "X_FIN_CM": round(float(x_fin), 2),
                        "FLAG_NO_COLOCADO": False})
            filas.append(rec)
            x += w
    for p in range(inst.P):                     # productos que no se colocaron
        if p not in sol.asig:
            rec = inst.df.loc[p].to_dict()
            rec.update({"CHAROLA": np.nan, "UBICACION_BANDEJA": np.nan,
                        "ANCHO_OCUPADO_CM": round(float(inst.W[p]), 2),
                        "X_INICIO_CM": np.nan, "X_FIN_CM": np.nan,
                        "FLAG_NO_COLOCADO": True})
            filas.append(rec)

    out = pd.DataFrame(filas).drop(columns=["W"], errors="ignore")
    out.attrs["Z"] = sol.score_Z()
    out.attrs["Z_H"] = inst.P                   # histórico: todos en su posición
    return out


# ==============================================================================
# ORQUESTADOR GLOBAL
# ==============================================================================
def planogramar_heuristico(df, ancho_charola=ANCHO_CHAROLA_CM,
                           n_charolas_override=None, factor_ancho=1.0,
                           mejora_local=True):
    """
    Aplica el heurístico a todos los formatos y concatena.

    factor_ancho : 1.0 -> modo IMITACIÓN (reproduce el acomodo factible del
                          socio; Score≈1). >1 -> PRUEBA DE ESTRÉS: infla la
                          demanda de frentes para que las charolas se desborden
                          y se vean las Fases 2-4 reparando.
    """
    presentes = [c for c in COLS_FORMATO if c in df.columns]
    salidas, Z_tot, ZH_tot = [], 0, 0
    for clave, sub in df.groupby(presentes, dropna=False):
        clave = clave if isinstance(clave, tuple) else (clave,)
        info = dict(zip(presentes, clave))
        n = n_charolas_override or num_charolas(info.get("TAMANO_POST", 4.0))
        out = heuristico_formato(sub, n, ancho_charola, factor_ancho, mejora_local)
        Z_tot += out.attrs["Z"]; ZH_tot += out.attrs["Z_H"]
        salidas.append(out)
    res = pd.concat(salidas, ignore_index=True)
    res.attrs["Score"] = (Z_tot / ZH_tot) if ZH_tot else float("nan")
    res.attrs["Z"] = Z_tot; res.attrs["Z_H"] = ZH_tot
    return res


# ==============================================================================
# VALIDACIÓN DE FACTIBILIDAD
# ==============================================================================
def validar(salida, ancho_charola=ANCHO_CHAROLA_CM):
    col = salida[salida["FLAG_NO_COLOCADO"] == False]
    presentes = [c for c in COLS_FORMATO if c in salida.columns]
    g = col.groupby(presentes + ["CHAROLA"], dropna=False)
    anchos = g["ANCHO_OCUPADO_CM"].sum()
    dobles = col.groupby(presentes + ["CHAROLA", "UBICACION_BANDEJA"],
                         dropna=False).size()
    return {
        "charolas_que_exceden_ancho": int((anchos > ancho_charola + 1e-6).sum()),
        "posiciones_duplicadas": int((dobles > 1).sum()),
        "productos_no_colocados": int(salida["FLAG_NO_COLOCADO"].sum()),
        "ocupacion_media_%": round(float(anchos.mean() / ancho_charola * 100), 1),
    }


# ==============================================================================
# DEMO  —  ejecútalo tal cual en Colab
# ==============================================================================
COLS_OUT = ["SEGMENTO_ID", "MUEBLE_ID", "PLANOGRUPO", "TAMANO_POST",
            "DIRECCION_LEGO_ID", "CONJUNTO_ID", "CHAROLA", "UBICACION_BANDEJA",
            "ITEM", "ITEM_DESC", "NUM_FRENTES", "ANCHO", "ALTO", "PROFUNDO",
            "ANCHO_OCUPADO_CM", "X_INICIO_CM", "X_FIN_CM", "FLAG_NO_COLOCADO"]

if __name__ == "__main__":
    RUTA = "ejemplo_planograma.csv"
    df = cargar_csv(RUTA)
    print(f"Cargado: {len(df)} filas, {df.columns.size} columnas\n")

    # ---------- MODO IMITACIÓN (factor_ancho=1.0) ----------
    print("=== MODO IMITACIÓN: reproduce el acomodo del socio ===")
    sol = planogramar_heuristico(df, factor_ancho=1.0)
    print(f"  Score = Z*/Z^H = {sol.attrs['Score']:.4f}  (Z={sol.attrs['Z']}, Z^H={sol.attrs['Z_H']})")
    for k, v in validar(sol).items():
        print(f"  {k}: {v}")
    cols = [c for c in COLS_OUT if c in sol.columns]
    sol[cols].to_csv("planograma_heuristico.csv", index=False, encoding="utf-8-sig")
    print("  -> guardado planograma_heuristico.csv\n")

    # ---------- PRUEBA DE ESTRÉS (factor_ancho=1.3) ----------
    print("=== PRUEBA DE ESTRÉS (frentes +30%): se activan las Fases 2-4 ===")
    s2 = planogramar_heuristico(df, factor_ancho=1.3)
    print(f"  Score = {s2.attrs['Score']:.4f}  (cae porque hubo que reparar)")
    for k, v in validar(s2).items():
        print(f"  {k}: {v}")