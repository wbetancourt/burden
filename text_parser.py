import re
import json
from typing import Dict, Any, Optional

def parse_extracted_text(text: str) -> Dict[str, Any]:
    """
    Parsea el texto extraído de un documento de Word para encontrar los parámetros específicos.
    Esta función usa expresiones regulares para extraer la información.
    """
    data = {}

    # Campos generales (key-value pairs)
    data["numero_de_proyecto"] = re.search(r"Número proye[^\s:]*[:\s]*([^\n]+)", text, re.IGNORECASE) # Ajustado para "proye¿tõ"
    data["nombre_de_proyecto"] = re.search(r"Nombre proyecto:?\s*([^\n]+)", text, re.IGNORECASE)
    data["direccion"] = re.search(r"Direcc[iíó]n:?\s*([^\n]+)", text, re.IGNORECASE) # Ajustado para "Direccción"
    data["contratista"] = re.search(r"Contratista:?\s*([^\n]+)", text, re.IGNORECASE)

    # DATOS DE TRANSFORMADORES DE POTENCIA (asumiendo una estructura de tabla con una fila de datos)
    # Buscamos la línea que contiene los datos del transformador, que empieza con "pp-"
    transformer_data_match = re.search(
        r"^(pp-\d+)\s+([A-Z0-9\s]+?)\s+([\d\.,]+)\s+(\d+)\s+([^\s]+)\s+([^\s]+)",
        text, re.MULTILINE | re.IGNORECASE
    )
    if transformer_data_match:
        data["no_trafo_de_potencia"] = transformer_data_match.group(1)
        data["transformador_marca"] = transformer_data_match.group(2).strip()
        data["capacidad_de_trafo"] = transformer_data_match.group(3)
        data["fases"] = transformer_data_match.group(4)
        # Los grupos 5 y 6 son "Serie trafo de distribución" y "No de nodo trafo a ener izar",
        # que no se mapean directamente a los Inputs actuales.

    # DATOS DE MEDICION - Transformadores de corriente TC (Múltiples TCs)
    data["tc_series"] = []
    data["tc_marcas"] = []
    
    # Buscamos la relación general
    # La relación TC se encuentra una vez, y luego se asume para todos los TCs listados.
    rel_match = re.search(r"Relación TC\s*([\d/]+(?:\s*A)?)", text, re.IGNORECASE)
    if rel_match:
        data["relacion_tc"] = rel_match.group(1).strip().replace(' A', '').replace('A', '')
    else:
        data["relacion_tc"] = "150/5"

    # Buscamos los patrones de series/marcas que suelen venir en bloque
    # Según el ejemplo: BTTV 18020 ATEL, BTTV 18026 ATEL...
    # Buscamos el bloque de "Transformadores de corriente TC"
    tc_block_match = re.search(r"Transformadores de corriente TC\s*(.*?)(?:Transformadores de tensión TT|Medidor nuevo)", text, re.DOTALL | re.IGNORECASE)
    if tc_block_match:
        tc_block_text = tc_block_match.group(1)
        # Ahora buscamos las series y marcas dentro de ese bloque
        # Patrón para "BTTV 18020 ATEL"
        tc_rows = re.findall(r"([A-Z]{2,4}\s*\d+)\s+([A-Z]+)", tc_block_text, re.IGNORECASE)
        for serie, marca in tc_rows:
            data["tc_series"].append(serie.strip())
            data["tc_marcas"].append(marca.strip())
    
    # Si no se encontraron TCs, inicializar con listas vacías
    if not data["tc_series"]: data["tc_series"] = ["N/A"] * 3 # Asumir 3 fases si no hay datos
    if not data["tc_marcas"]: data["tc_marcas"] = ["N/A"] * 3

    # DATOS DE MEDICION - Medidor nuevo
    # Extraer "Grupo Serie"
    # El usuario indica que es U41C_037297190334
    grupo_serie_match = re.search(r"([A-Z0-9]{4,}[_\s]\d{10,})", text)
    if grupo_serie_match:
        data["grupo_serie_medidor"] = grupo_serie_match.group(1).strip()
    else: # Si no se encuentra, usar el valor por defecto del usuario
        data["grupo_serie_medidor"] = "U41C_037297190334"

    # Extraer "Comercializador No." (Contrato/Cliente/Suscriptor)
    cliente_medidor_match = re.search(r"Comercializador No\.\s*(\d+)", text, re.IGNORECASE) # El usuario indicó que es el número de contrato/cliente
    if cliente_medidor_match:
        data["contrato_cliente"] = cliente_medidor_match.group(1).strip() # Mapeado a contrato_proyecto

    # Limpiar los resultados de las expresiones regulares
    for key, value in data.items():
        if isinstance(value, re.Match):
            data[key] = value.group(1).strip()
        elif value is None:
            data[key] = "" # Default a cadena vacía si no se encuentra

    # Combinar campos para la clase Inputs
    # Estos se combinan en app.py para mayor flexibilidad

    return data
    
def parse_indirect_text(text: str) -> Dict[str, Any]:
    """
    Parsea el texto para encontrar parámetros de medida indirecta (JSON o etiquetas).
    """
    try:
        # Intentar detectar un formato JSON primero
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0).replace("'", '"'))
    except:
        pass

    data = {}
    # Patrones para búsqueda por etiquetas en el texto pegado
    patterns = {
        "longitud_m": r"(?:longitud_m|longitud)\D*([\d\.,]+)",
        "resistencia_ohm_m": r"(?:resistencia_ohm_m|resistencia)\D*([\d\.,]+)",
        "corriente_secundaria_A": r"(?:corriente_secundaria_A|corriente)\D*([\d\.,]+)",
        "burden_medidor_VA": r"(?:burden_medidor_VA|burden del medidor)\D*([\d\.,]+)",
        "numero_medidores": r"(?:numero_medidores|medidores)\D*(\d+)",
        "tipo_transformador": r"(?:tipo_transformador|tipo)\D*(TC|TT)"
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = match.group(1).replace(',', '.')
            if key == "tipo_transformador":
                data[key] = val.upper()
            elif key == "numero_medidores":
                data[key] = int(val)
            else:
                data[key] = float(val)
    return data
