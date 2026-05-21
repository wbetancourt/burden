from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any
from tables import TABLA4_SEMI, TABLA5_IND
import datetime # Import datetime for automatic date

@dataclass
class Inputs:
    tipo_medida: str                   # "Semidirecta" / "Indirecta"
    fases: int                         # 1 o 3
    kva_transformador: float
    circuito_bt: Optional[str] = None  # semidirecta
    kv: Optional[float] = None         # indirecta
    tc_relacion: Optional[str] = None  # "150/5" o "5/5" etc.
    ib_sec: float = 5.0
    va_tc: float = 5.0
    burden_medidor_va_fase: float = 0.2
    burden_otros_va_fase: float = 0.0
    r_ohm_km: float = 0.0
    long_ida_km: float = 0.0
    # --- Nuevos campos solicitados por el usuario ---
    medidor: Optional[str] = None
    serie_medidor: Optional[str] = None
    grupo: Optional[str] = None
    calibre_conductor: Optional[str] = None
    va_conductor_input: Optional[float] = None # Asumiendo que es un VA de entrada para el conductor, no el VA_cable calculado
    clase_exactitud: Optional[str] = None
    transformador_id: Optional[str] = None # Para almacenar el identificador del transformador
    transformador_marca: Optional[str] = None # Nueva marca del transformador
    direccion: Optional[str] = None
    fecha_elaboracion: Optional[str] = None # Se establecerá automáticamente en app.py
    contratista: Optional[str] = None
    contrato_proyecto: Optional[str] = None # Número de contrato/cliente
    proyecto: Optional[str] = None # Nombre del proyecto
    tc_marcas: List[str] = None # Lista para marcas de TC por fase
    tc_series: List[str] = None # Lista para series de TC por fase
    # -------------------------------------------------

def _pick_range(value: float, ranges: List[Tuple[float, float, str]]) -> Tuple[str, float]:
    """
    Devuelve (relación_tc, kVA_max) para el rango donde kVA_min <= value <= kVA_max.
    Si no cae exacto, devuelve el último rango cuyo kVA_min <= value (comportamiento tipo BUSCARV VERDADERO).
    """
    ranges_sorted = sorted(ranges, key=lambda x: x[0])
    candidate = None
    for kmin, kmax, rel in ranges_sorted:
        if value >= kmin:
            candidate = (rel, kmax)
        else:
            break
    if candidate is None:
        # por debajo del primer rango
        first = ranges_sorted[0]
        return first[2], first[1]
    return candidate

def tc_recomendado(inp: Inputs) -> Dict[str, Optional[float]]:
    """
    Devuelve TC recomendado y kVA_max autorizado (según tabla).
    """
    if inp.tipo_medida == "Semidirecta":
        if not inp.circuito_bt:
            return {"tc": None, "kva_max": None}
        # Asegurarse de que la clave exista en TABLA4_SEMI
        if inp.circuito_bt not in TABLA4_SEMI:
            return {"tc": None, "kva_max": None}
        rel, kva_max = _pick_range(inp.kva_transformador, TABLA4_SEMI[inp.circuito_bt])
        return {"tc": rel, "kva_max": float(kva_max)}

    if inp.tipo_medida == "Indirecta":
        if inp.kv is None:
            return {"tc": None, "kva_max": None}
        # Asegurarse de que la clave exista en TABLA5_IND
        if float(inp.kv) not in TABLA5_IND:
            return {"tc": None, "kva_max": None}
        rel, kva_max = _pick_range(inp.kva_transformador, TABLA5_IND[float(inp.kv)])
        return {"tc": rel, "kva_max": float(kva_max)}

    return {"tc": None, "kva_max": None}

def kva_max_por_tc_instalado(inp: Inputs) -> Optional[float]:
    """
    kVA máximo permitido por la relación TC instalada (búsqueda exacta dentro del circuito/kV).
    """
    if not inp.tc_relacion:
        return None

    rows = []
    if inp.tipo_medida == "Semidirecta":
        rows = TABLA4_SEMI.get(inp.circuito_bt or "", [])
    else: # Indirecta
        if inp.kv is not None:
            rows = TABLA5_IND.get(float(inp.kv), [])

    for kmin, kmax, rel in rows:
        if str(rel).replace(" ", "") == str(inp.tc_relacion).replace(" ", ""):
            return float(kmax)
    return None

def burden_por_fase(inp: Inputs) -> Dict[str, float]:
    """
    Burden por fase: medidor + cables + otros
    Cable: I^2 * R_lazo; R_lazo = (2*L[km]) * (ohm/km)
    """
    r_lazo = (2 * inp.long_ida_km) * inp.r_ohm_km
    va_cable = (inp.ib_sec ** 2) * r_lazo
    va_total = inp.burden_medidor_va_fase + va_cable + inp.burden_otros_va_fase
    utiliz = va_total / inp.va_tc if inp.va_tc else 0.0
    return {
        "r_lazo_ohm": r_lazo,
        "va_cable": va_cable,
        "va_total": va_total,
        "utilizacion": utiliz
    }

def evalua(inp: Inputs) -> Dict:
    rec = tc_recomendado(inp)
    kva_inst = kva_max_por_tc_instalado(inp)
    calc_burden = burden_por_fase(inp)

    # Cálculo de kVA autorizados y restantes (Fórmula técnica solicitada)
    kva_autorizado_calc = 0.0
    try:
        if inp.tc_relacion:
            tc_primario = float(str(inp.tc_relacion).split('/')[0])
            v_ref = 0.0
            f_fases = 1.7320508 if int(inp.fases) == 3 else 1.0
            
            if inp.tipo_medida == "Semidirecta":
                if inp.circuito_bt == "3x120/208": v_ref = 208.0
                elif inp.circuito_bt == "3x127/220": v_ref = 220.0
                elif inp.circuito_bt == "3x254/440": v_ref = 440.0
                elif inp.circuito_bt == "120/240": v_ref = 240.0
            else: # Indirecta
                if inp.kv:
                    v_ref = float(inp.kv) * 1000.0
            
            kva_autorizado_calc = (f_fases * v_ref * tc_primario) / 1000.0
    except Exception:
        kva_autorizado_calc = 0.0
    
    kva_restantes = inp.kva_transformador - kva_autorizado_calc if kva_autorizado_calc > 0 else 0.0

    # Validaciones técnicas globales
    cumple_kva_tc = (kva_inst is not None) and (inp.kva_transformador <= kva_inst)
    cumple_tc_rec = (inp.tc_relacion is not None) and (rec["tc"] is not None) and (str(inp.tc_relacion).replace(" ","") == str(rec["tc"]).replace(" ",""))
    util_gen = calc_burden["utilizacion"]
    cumple_burden_general = (util_gen >= 0.25) and (util_gen <= 1.00)

    # Resultados por fase
    fases_labels = ["R", "S", "T"] if inp.fases == 3 else ["R"] # Asumimos R, S, T para 3 fases
    res_fases = []
    
    for i, label in enumerate(fases_labels):
        serie = inp.tc_series[i] if inp.tc_series and i < len(inp.tc_series) else "N/A"
        marca = inp.tc_marcas[i] if inp.tc_marcas and i < len(inp.tc_marcas) else "N/A"
        
        # La columna de la tabla solo valida el rango de Burden (25% - 100%)
        fase_cumple_burden = cumple_burden_general

        if util_gen < 0.25:
            justif = "Burden bajo (mín 25%)"
        elif util_gen > 1.00:
            justif = "Burden alto (máx 100%)"
        elif not cumple_kva_tc:
            justif = f"kVA exceso (máx {kva_inst} kVA)"
        elif not cumple_tc_rec:
            justif = f"TC no recomendado (usar {rec['tc']})"
        else:
            justif = "Cumple criterios técnicos"
        
        res_fases.append({
            "fase": label,
            "relacion": inp.tc_relacion,
            "serie": serie,
            "marca": marca,
            "va_tc": inp.va_tc,
            "burden_total": round(calc_burden["va_total"], 4),
            "utilizacion": f"{util_gen*100:.2f}%",
            "util_float": util_gen * 100, # Para el gráfico
            "cumple": "SÍ" if fase_cumple_burden else "NO",
            "justificacion": justif
        })

    # El resultado global (título) ahora coincide estrictamente con la columna "cumple" de la tabla
    apto = all([f["cumple"] == "SÍ" for f in res_fases])

    return {
        "tc_recomendado": rec["tc"],
        "kva_max_tabla": rec["kva_max"],
        "kva_max_tc_instalado": kva_inst,
        "kva_autorizado_calc": round(kva_autorizado_calc, 2),
        "kva_restantes": round(kva_restantes, 2),
        "burden": calc_burden, # Mantener para compatibilidad si se usa en otro lado
        "detalle_fases": res_fases,
        "cumple": {
            "burden": cumple_burden_general,
            "kva_vs_tc": cumple_kva_tc,
            "tc_vs_recomendado": cumple_tc_rec
        },
        "resultado": "cumple" if apto else "NO cumple"
    }

def calculate_normative_burden(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcula el BURDEN de transformadores de medida bajo normativa CREG 038.
    """
    L = float(data.get("longitud_m", 0))
    RAC = float(data.get("resistencia_ohm_m", 0))
    I = float(data.get("corriente_secundaria_A", 5))
    VA_MED = float(data.get("burden_medidor_VA", 0))
    N = int(data.get("numero_medidores", 1))
    tipo = data.get("tipo_transformador", "TC")
    VA_NOM_TC = float(data.get("va_nominal_tc", 5.0)) 

    # 1. Cálculos base (Modelo Matemático)
    # Aunque la descripción diga I * L * RAC, para obtener 3.75 con I=5, L=24, RAC=0.00625
    # se requiere I^2 * L * RAC, que es la fórmula física de carga en VA (P = I^2 * Z).
    if tipo == "TC":
        va_conductor = (I ** 2) * (L * RAC)
    else:
        # Simplificación para TT si se asume carga por impedancia
        va_conductor = L * RAC

    va_medidor_total = VA_MED * N
    va_total = va_medidor_total + va_conductor

    # 2. Selección de Burden Normalizado [2.5, 5, 10, 15, 30]
    normalizados = [2.5, 5, 10, 15, 30]
    burden_normalizado = next((val for val in normalizados if val >= va_total), normalizados[-1])

    # 3. Validaciones Normativas (25% - 100%)
    porcentaje_uso = (va_total / VA_NOM_TC) * 100
    cumple_rango = 25.0 <= porcentaje_uso <= 100.0
    
    mensaje = "El burden se encuentra dentro del rango permitido (25%-100%)" if cumple_rango else "El burden se encuentra fuera del rango permitido (25%-100%)"

    return {
        "calculos": {
            "VACONDUCTOR": round(va_conductor, 4),
            "VAMEDIDOR_TOTAL": round(va_medidor_total, 4),
            "VATOTAL": round(va_total, 4)
        },
        "seleccion": {
            "burden_normalizado": burden_normalizado,
            "porcentaje_uso": round(porcentaje_uso, 2)
        },
        "validaciones": {
            "cumple_rango": cumple_rango,
            "mensaje": mensaje
        },
        "detalle": {
            "formula_usada": "VATOTAL = VAMEDIDOR + VACONDUCTOR",
            "supuestos": "VADEVANADO despreciado"
        }
    }

__all__ = ["Inputs", "evalua", "calculate_normative_burden"]
