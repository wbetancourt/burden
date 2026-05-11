import io
import pytesseract
from pdf2image import convert_from_bytes
import re # Importar re para las expresiones regulares
from typing import Dict, Any, Optional
import platform

# Configuración dinámica para Windows (local) y Linux (Streamlit Cloud)
if platform.system() == "Windows":
    # Rutas locales (ajusta según tu PC si es necesario)
    POPPLER_PATH = r'C:\Users\Emcali-14\Downloads\Release-26.02.0-0\poppler-26.02.0\Library\bin'
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:
    # En Streamlit Cloud, estos se instalan en el PATH automáticamente vía packages.txt
    POPPLER_PATH = None 
    # pytesseract.pytesseract.tesseract_cmd ya está en /usr/bin/tesseract por defecto

def extract_data_from_scanned_pdf(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Convierte un PDF escaneado a imágenes, aplica OCR y extrae parámetros.
    """
    extracted_text = ""
    try:
        # Convertir PDF a imágenes (solo la primera página)
        images = convert_from_bytes(pdf_bytes, first_page=1, last_page=1, poppler_path=POPPLER_PATH)
        
        if images:
            extracted_text = pytesseract.image_to_string(images[0], lang='spa')
    except FileNotFoundError:
        return {"error": "Poppler no encontrado en el sistema."}
    except Exception as e:
        err_msg = str(e)
        if "poppler" in err_msg.lower():
            return {"error": "Error de Poppler: No instalado o no está en el PATH."}
        print(f"Error durante el procesamiento del PDF: {e}")
        return {}

    # Una vez que tenemos el texto, lo parseamos para extraer los campos
    return parse_extracted_text(extracted_text)

def parse_extracted_text(text: str) -> Dict[str, Any]:
    """
    Parsea el texto extraído por OCR para encontrar los parámetros específicos.
    Esta función es la más crítica y debe adaptarse al formato exacto de tus PDFs.
    """
    data = {}

    # Ejemplo de cómo extraer algunos campos usando expresiones regulares
    # Estos patrones son EJEMPLOS y DEBEN ajustarse a la estructura real de tu PDF

    # Campos generales
    data["Numero de proyecto"] = re.search(r"Proyecto\s*N[o°\.]?[:\s]*([^\n]+)", text, re.IGNORECASE)
    data["Nombre de proyecto"] = re.search(r"Nombre\s*de?\s*Proyecto[:\s]*([^\n]+)", text, re.IGNORECASE)
    data["Direccion"] = re.search(r"Direcci[oó]n[:\s]*([^\n]+)", text, re.IGNORECASE)
    data["Contratista"] = re.search(r"Contratista[:\s]*([^\n]+)", text, re.IGNORECASE)

    # Datos del Transformador
    data["No trafo de potencia"] = re.search(r"(?:No|N[o°\.]?)\s*trafo\s*(?:de\s*potencia)?[:\s]*([^\n]+)", text, re.IGNORECASE)
    data["Marca Transformador"] = re.search(r"Marca[:\s]*([^\n]+)", text, re.IGNORECASE)
    data["Capacidad de trafo"] = re.search(r"Capacidad\s*(?:de\s*trafo)?[:\s]*([\d\.,]+)", text, re.IGNORECASE)
    data["fases"] = re.search(r"fases[:\s]*(\d)", text, re.IGNORECASE)

    # Datos de TC
    data["relacion tc"] = re.search(r"relaci[oó]n\s*tc[:\s]*([^\n]+)", text, re.IGNORECASE)
    data["No. serie TC"] = re.search(r"(?:Serie|N[o°\.]?\s*serie)[:\s]*([^\n]+)", text, re.IGNORECASE)
    data["Marca TC"] = re.search(r"Marca[:\s]*([^\n]+)", text, re.IGNORECASE)

    # Datos del Medidor
    data["Medidor Nuevo"] = re.search(r"Medidor\s*Nuevo[:\s]*([^\n]+)", text, re.IGNORECASE)
    data["Grupo Serie Medidor"] = re.search(r"Grupo\s*Serie[:\s]*([^\n]+)", text, re.IGNORECASE)
    data["Cliente Medidor a Instalar"] = re.search(r"Cliente\s*Medidor[:\s]*([^\n]+)", text, re.IGNORECASE)

    # Limpiar los resultados de las expresiones regulares
    for key, match in data.items():
        if match:
            data[key] = match.group(1).strip()
        else:
            data[key] = None
            
    # Mapear a los nombres de campos esperados por la aplicación
    # Esto es crucial para que los datos extraídos se usen correctamente
    mapped_data = {k.replace(" ", "_").lower(): v for k, v in data.items() if v is not None}
    
    return mapped_data