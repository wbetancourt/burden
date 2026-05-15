# Calculador de Burden y Selección de TC - EMCALI

Esta aplicación web, desarrollada en Python con Streamlit, permite automatizar el cálculo de burden y la selección de transformadores de corriente (TC) y potencial (TP) para mediciones semidirectas e indirectas, siguiendo los lineamientos de la norma **IEEE Std. 241-1990**.

## Características

- **Cálculo de Burden:** Análisis vectorial de impedancia (R + jX) según calibre, material y tipo de conduit.
- **Selección Automática:** Recomendación de relación de TC basada en tablas normativas de EMCALI.
- **Análisis de Error:** Cálculo de caída de tensión y error porcentual en TPs.
- **Procesamiento de Documentos:** Extracción de datos desde texto pegado (OCR listo para PDF).
- **Reportes:** Generación de archivos Excel de evidencia y vista de impresión técnica.

## Instalación

1. Clonar el repositorio.
2. Crear un entorno virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```
3. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. **Nota:** Para el procesamiento de PDF/OCR, es necesario tener instalado [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) y [Poppler](https://poppler.freedesktop.org/) en el sistema.

## Ejecución

```bash
streamlit run app.py
```