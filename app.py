import os
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import re as std_re
import base64
from engine import Inputs, evalua, calculate_normative_burden
from text_parser import parse_extracted_text, parse_indirect_text
from report_xlsx import build_evidence_xlsx
import datetime # Import datetime for automatic date

def get_base64_of_bin_file(bin_file):
    """Lee un archivo binario y lo devuelve en formato base64 string."""
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def get_html_print_content(inp, results, logo_b64=""):
    """Genera una cadena HTML base64 para abrir en una nueva pestaña e imprimir."""
    
    phase_rows = "".join([
        f"""<tr>
            <td>{f['fase']}</td>
            <td>{f['relacion']}</td>
            <td>{f['serie']}</td>
            <td>{f['marca']}</td>
            <td>{f['va_tc']}</td>
            <td>{f['burden_total']}</td>
            <td>{f['utilizacion']}</td>
            <td>{f['cumple']}</td>
        </tr>""" for f in results["detalle_fases"]
    ])

    # Generar los gauges para el HTML de impresión
    gauges_html = ""
    for f in results["detalle_fases"]:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=f["util_float"],
            title={'text': f"Fase {f['fase']}", 'font': {'size': 20}},
            gauge={
                'axis': {'range': [0, 120]},
                'bar': {'color': "black"},
                'steps': [
                    {'range': [0, 25], 'color': "#ff4b4b"},
                    {'range': [25, 100], 'color': "#09ab3b"},
                    {'range': [100, 120], 'color': "#ff4b4b"}
                ]
            }
        ))
        fig.update_layout(height=180, width=220, margin=dict(l=20, r=20, t=30, b=20))
        is_first = (gauges_html == "")
        # Incluimos Plotly JS desde el CDN solo en el primer gráfico
        gauges_html += f'<div style="display:inline-block;">{fig.to_html(full_html=False, include_plotlyjs="cdn" if is_first else False)}</div>'

    status_class = "status-cumple" if results["resultado"] == "cumple" else "status-no"
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; color: #333; }}
            .header {{ text-align: center; border-bottom: 3px solid #004b87; padding-bottom: 10px; margin-bottom: 20px; }}
            .logo {{ max-height: 80px; margin-bottom: 10px; }}
            .header h1 {{ color: #004b87; margin: 0; font-size: 24px; }}
            .info-grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 20px; }}
            .info-item {{ background: #f4f4f4; padding: 8px; border-radius: 4px; font-size: 14px; }}
            .status-box {{ text-align: center; padding: 15px; font-size: 22px; font-weight: bold; border-radius: 8px; margin: 20px 0; }}
            .status-cumple {{ background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
            .status-no {{ background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ccc; padding: 10px; text-align: center; font-size: 13px; }}
            th {{ background-color: #004b87; color: white; }}
            .metrics {{ display: flex; justify-content: space-around; background: #eee; padding: 10px; border-radius: 8px; margin-bottom: 20px; }}
            .metric-item {{ text-align: center; }}
            .gauges-container {{ text-align: center; margin-top: 30px; }}
            @media print {{ .no-print {{ display: none; }} }}
        </style>
    </head>
    <body>
        <div class="header">
            {f'<img src="data:image/png;base64,{logo_b64}" class="logo">' if logo_b64 else ""}
            <h1>EMCALI - REPORTE TÉCNICO DE MEDICIÓN</h1>
            <p>Validación de Burden y Selección de Transformadores de Corriente</p>
        </div>
        <div class="info-grid">
            <div class="info-item"><strong>Contratista:</strong> {inp.contratista}</div>
            <div class="info-item"><strong>Contrato:</strong> {inp.contrato_proyecto}</div>
            <div class="info-item"><strong>Proyecto:</strong> {inp.proyecto}</div>
            <div class="info-item"><strong>Dirección:</strong> {inp.direccion}</div>
            <div class="info-item"><strong>Tipo de medida:</strong> {inp.tipo_medida}</div>
            <div class="info-item"><strong>Medidor (Grup/Ser):</strong> {inp.medidor}</div>
            <div class="info-item"><strong>Clase de exactitud:</strong> {inp.clase_exactitud}</div>
            <div class="info-item"><strong>kVA Transformador:</strong> {inp.kva_transformador} kVA</div>
            <div class="info-item"><strong>Transformador:</strong> {inp.transformador_id} ({inp.transformador_marca})</div>
            <div class="info-item"><strong>Burden Medidor:</strong> {inp.burden_medidor_va_fase} VA/fase</div>
            <div class="info-item"><strong>Resistencia Cond.:</strong> {inp.r_ohm_km} Ω/km</div>
            <div class="info-item"><strong>Longitud ida:</strong> {inp.long_ida_km} Km</div>
            <div class="info-item"><strong>Fecha Elaboración:</strong> {inp.fecha_elaboracion}</div>
        </div>
        <div class="status-box {status_class}">ESTADO: {results['resultado'].upper()}</div>
        <div class="metrics">
            <div class="metric-item"><strong>kVA Autorizado:</strong><br>{results['kva_autorizado_calc']} kVA</div>
            <div class="metric-item"><strong>kVA Restante:</strong><br>{results['kva_restantes']} kVA</div>
            <div class="metric-item"><strong>TC Recomendado:</strong><br>{results['tc_recomendado']}</div>
        </div>
        <table>
            <thead><tr><th>Fase</th><th>Relación</th><th>Serie</th><th>Marca</th><th>VA TC</th><th>Burden Total</th><th>Utilización</th><th>Cumple</th></tr></thead>
            <tbody>{phase_rows}</tbody>
        </table>

        <div class="gauges-container">
            <h3>Gráficos de Utilización</h3>
            {gauges_html}
        </div>

        <script>
            window.onload = function() {{
                // Retraso para permitir que Plotly renderice los gráficos antes de imprimir
                setTimeout(function() {{
                    window.print();
                }}, 1500);
            }};
        </script>
    </body>
    </html>
    """
    return base64.b64encode(html_template.encode()).decode()

def get_normative_html_print_content(data_input, results, logo_b64=""):
    """Genera una cadena HTML base64 para el reporte de medida indirecta (Normativo)."""
    
    # Generar el gauge para el HTML
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=results['seleccion']['porcentaje_uso'],
        title={'text': f"% Carga del {data_input['tipo_transformador']}", 'font': {'size': 20}},
        gauge={
            'axis': {'range': [0, 120]},
            'bar': {'color': "black"},
            'steps': [
                {'range': [0, 25], 'color': "#ff4b4b"},
                {'range': [25, 100], 'color': "#09ab3b"},
                {'range': [100, 120], 'color': "#ff4b4b"}
            ],
            'threshold': {'line': {'color': "blue", 'width': 4}, 'thickness': 0.75, 'value': 100}
        }
    ))
    fig.update_layout(height=250, width=300, margin=dict(l=20, r=20, t=50, b=20))
    gauge_html = fig.to_html(full_html=False, include_plotlyjs="cdn")

    status_class = "status-cumple" if results['validaciones']['cumple_rango'] else "status-no"
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; color: #333; }}
            .header {{ text-align: center; border-bottom: 3px solid #004b87; padding-bottom: 10px; margin-bottom: 20px; }}
            .logo {{ max-height: 80px; margin-bottom: 10px; }}
            .header h1 {{ color: #004b87; margin: 0; font-size: 24px; }}
            .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px; }}
            .info-item {{ background: #f4f4f4; padding: 10px; border-radius: 4px; font-size: 14px; }}
            .status-box {{ text-align: center; padding: 15px; font-size: 20px; font-weight: bold; border-radius: 8px; margin: 20px 0; }}
            .status-cumple {{ background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
            .status-no {{ background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
            .metrics-container {{ display: flex; justify-content: space-around; background: #eee; padding: 15px; border-radius: 8px; }}
            .metric-card {{ text-align: center; }}
            .gauge-container {{ text-align: center; margin-top: 30px; }}
        </style>
    </head>
    <body>
        <div class="header">
            {f'<img src="data:image/png;base64,{logo_b64}" class="logo">' if logo_b64 else ""}
            <h1>EMCALI - REPORTE TÉCNICO BURDEN NORMATIVO</h1>
            <p>Validación bajo CREG 038 / NTC 5019 (Medida Indirecta)</p>
        </div>
        
        <div class="info-grid">
            <div class="info-item"><strong>Tipo:</strong> {data_input['tipo_transformador']}</div>
            <div class="info-item"><strong>Corriente Secundaria:</strong> {data_input['corriente_secundaria_A']} A</div>
            <div class="info-item"><strong>VA Nominal {data_input['tipo_transformador']}:</strong> {data_input['va_nominal_tc']} VA</div>
            <div class="info-item"><strong>Burden Medidor:</strong> {data_input['burden_medidor_VA']} VA</div>
            <div class="info-item"><strong>Longitud:</strong> {data_input['longitud_m']} m</div>
            <div class="info-item"><strong>Resistencia:</strong> {data_input['resistencia_ohm_m']} Ω/m</div>
            <div class="info-item"><strong>Fecha:</strong> {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}</div>
        </div>

        <div class="status-box {status_class}">
            {results['validaciones']['mensaje'].upper()}
        </div>

        <div class="metrics-container">
            <div class="metric-card">
                <strong>VA Conductor</strong><br>{results['calculos']['VACONDUCTOR']}
            </div>
            <div class="metric-card">
                <strong>VA Total</strong><br>{results['calculos']['VATOTAL']}
            </div>
            <div class="metric-card">
                <strong>Normalizado Sugerido</strong><br>{results['seleccion']['burden_normalizado']} VA
            </div>
            <div class="metric-card">
                <strong>% Carga</strong><br>{results['seleccion']['porcentaje_uso']}%
            </div>
        </div>

        <div class="gauge-container">
            <h3>Gráfico de Carga del Transformador</h3>
            {gauge_html}
        </div>

        <script>
            window.onload = function() {{
                setTimeout(function() {{
                    window.print();
                }}, 1200);
            }};
        </script>
    </body>
    </html>
    """
    return base64.b64encode(html_template.encode()).decode()

def render_main_module():
    st.subheader("Análisis de Burden y Selección de TC (Basado en Plantilla)")
    pasted_text = st.text_area("Pega aquí el contenido del documento de Word", height=300)

    if pasted_text:
        try:
            params = parse_extracted_text(pasted_text)
        except Exception as e:
            st.error(f"Error al procesar el texto: {e}")
            st.stop()

        st.subheader("Configuración de Entrada")
        tab_tech, tab_info = st.tabs(["⚙️ Parámetros Técnicos", "📝 Información del Proyecto"])

        with tab_tech:
            c1, c2 = st.columns(2)
            with c1:
                tipo = st.selectbox("Tipo de medida", ["Semidirecta", "Indirecta"], index=0)
                fases = st.number_input("Número de fases", value=int(params.get("fases", 3) or 3), min_value=1, max_value=3)
                
                kva_trf_from_text = params.get("capacidad_de_trafo")
                try:
                    clean_val = std_re.sub(r'[^0-9\.]', '', str(kva_trf_from_text or 0.0).replace(',', '.'))
                    kva_trf = float(clean_val) if clean_val else 0.0
                except: kva_trf = 0.0
                kva_trf = st.number_input("kVA Transformador", value=kva_trf, min_value=0.0, format="%.2f")
                
                tc_rel = st.text_input("Relación TC instalada", value=params.get("relacion_tc", "150/5"))

            with c2:
                ib = st.number_input("Ib secundaria TC [A]", value=5.0, min_value=0.0)
                va_tc = st.number_input("VA nominal TC [VA]", value=5.0, min_value=0.0)
                r_ohm_km = st.number_input("Resistencia (Ω/km)", value=0.0, format="%.4f")
                long_km = st.number_input("Longitud ida (km)", value=0.0, format="%.4f")

            exp_burden = st.expander("Ver otros parámetros de Burden")
            with exp_burden:
                b1, b2 = st.columns(2)
                burden_med = b1.number_input("Burden medidor (VA/fase)", value=0.2)
                burden_otros = b2.number_input("Burden otros (VA/fase)", value=0.0)

            if tipo == "Semidirecta":
                circuito_bt = st.selectbox("Circuito BT", ["3x120/208","3x127/220","3x254/440","120/240"], index=1)
                kv = None
            else:
                kv = st.selectbox("Nivel de tensión (kV)", [11.4, 13.2, 34.5], index=1)
                circuito_bt = None

        with tab_info:
            medidor = st.text_input("Medidor (Grupo Serie)", value=params.get("grupo_serie_medidor", "U41C_037297190334"))
            contrato = st.text_input("Número de Contrato / Cliente", value=params.get("contrato_cliente", "47274454"))
            proyecto_nom = st.text_input("Proyecto", value=f"{params.get('numero_de_proyecto', '')} - {params.get('nombre_de_proyecto', '')}".strip(" - "))
            direccion = st.text_input("Dirección", value=params.get("direccion", ""))
            transformador_id = st.text_input("ID Transformador", value=params.get("no_trafo_de_potencia", ""))
            transformador_marca = st.text_input("Marca Transformador", value=params.get("transformador_marca", ""))
            contratista = st.text_input("Contratista", value=params.get("contratista", ""))
            
            # Datos menores
            with st.expander("Más información del sitio"):
                calibre_conductor = st.text_input("Calibre Conductor", value="AWG 12")
                va_conductor_input = st.number_input("VA Conductor (Manual)", value=0.0)
                clase_exactitud = st.text_input("Clase de Exactitud", value="")
                fecha_elaboracion = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.caption(f"Fecha: {fecha_elaboracion}")

        # Manejo de TCs (Edición Manual)
        tc_marcas_ext = params.get("tc_marcas", [])
        tc_series_ext = params.get("tc_series", [])
        
        tc_marcas = []
        tc_series = []

        with st.expander("🔌 Configuración de Series y Marcas de TCs", expanded=False):
            st.caption("Verifica o ajusta los datos de los transformadores de corriente (Serie y Marca):")
            cols_tcs = st.columns(fases)
            for i in range(fases):
                label = ['R', 'S', 'T'][i]
                with cols_tcs[i]:
                    st.markdown(f"**Fase {label}**")
                    def_s = tc_series_ext[i] if i < len(tc_series_ext) else "N/A"
                    def_m = tc_marcas_ext[i] if i < len(tc_marcas_ext) else "N/A"
                    
                    s = st.text_input(f"Serie {label}", value=def_s, key=f"s_{label}")
                    m = st.text_input(f"Marca {label}", value=def_m, key=f"m_{label}")
                    
                    tc_series.append(s)
                    tc_marcas.append(m)

        # -------------------------------------------------
        inp = Inputs(
            tipo_medida=tipo, fases=fases, kva_transformador=kva_trf,
            circuito_bt=circuito_bt, kv=kv,
            tc_relacion=tc_rel.strip().replace(' A', '').replace('A', '') if tc_rel else None, # Limpiar espacios y el sufijo ' A'
            ib_sec=ib, va_tc=va_tc, burden_medidor_va_fase=burden_med,
            burden_otros_va_fase=burden_otros, r_ohm_km=r_ohm_km, long_ida_km=long_km,
            medidor=medidor, calibre_conductor=calibre_conductor, va_conductor_input=va_conductor_input,
            clase_exactitud=clase_exactitud, transformador_id=transformador_id,
            transformador_marca=transformador_marca, direccion=direccion,
            fecha_elaboracion=fecha_elaboracion, contratista=contratista,
            contrato_proyecto=contrato, proyecto=proyecto_nom,
            tc_marcas=tc_marcas, tc_series=tc_series
        )

        results = evalua(inp)

        st.divider()
        st.subheader("📊 Resultados del Análisis")
        
        # Resumen superior con métricas clave
        res_color = "green" if results["resultado"] == "cumple" else "red"
        st.markdown(f"#### Estado General: <span style='color:{res_color}; font-size:36px;'>{results['resultado'].upper()}</span>", unsafe_allow_html=True)
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("kVA Autorizado", f"{results['kva_autorizado_calc']} kVA")
        m2.metric("kVA Restante", f"{results['kva_restantes']} kVA", delta_color="inverse")
        m3.metric("TC Recomendado", results['tc_recomendado'])
        m4.metric("kVA Máx (Instalado)", f"{results['kva_max_tc_instalado']} kVA")

        # Pestañas de detalle de resultados a todo lo ancho
        tab_res, tab_json = st.tabs(["📋 Detalle de Fases", "🔍 Verificación Técnica"])
        
        with tab_res:
            st.table(results["detalle_fases"])

            st.write("---")
            st.write("#### 📈 Gráficos de Utilización")
            cols_gauge = st.columns(len(results["detalle_fases"]))
            for i, fase in enumerate(results["detalle_fases"]):
                with cols_gauge[i]:
                    st.markdown(f"<p style='text-align: center; font-weight: bold; font-size: 20px;'>Fase {fase['fase']}</p>", unsafe_allow_html=True)
                    fig = go.Figure(go.Indicator(
                        mode = "gauge+number",
                        value = fase["util_float"],
                        gauge = {
                            'axis': {'range': [0, 120]},
                            'bar': {'color': "black"},
                            'steps': [
                                {'range': [0, 25], 'color': "#ff4b4b"},
                                {'range': [25, 100], 'color': "#09ab3b"},
                                {'range': [100, 120], 'color': "#ff4b4b"}
                            ]
                        }
                    ))
                    fig.update_layout(height=180, margin=dict(l=10, r=10, t=10, b=10))
                    st.plotly_chart(fig, use_container_width=True, key=f"gauge_fase_{fase['fase']}")

        with tab_json:
            st.write("**Resumen de cumplimiento:**")
            st.json(results["cumple"])
            with st.expander("Ver JSON de análisis completo"):
                structured_json = [
                    {
                        "Fase": f["fase"],
                        "% Utilización": f["utilizacion"],
                        "Cumple": f["cumple"],
                        "Justificación": f["justificacion"]
                    } for f in results["detalle_fases"]
                ]
                st.json(structured_json)

        # Descargar evidencia
        st.divider()
        
        # Obtener el logo en base64 para el HTML desde el archivo físico
        logo_b64_html = ""
        if os.path.exists("logoemcali.png"):
            logo_b64_html = get_base64_of_bin_file("logoemcali.png")

        # Botón de Impresión HTML
        html_b64 = get_html_print_content(inp, results, logo_b64_html)
        
        # Usamos un componente HTML con JS para evadir el bloqueo de navegación data:URI
        components.html(f"""
            <button id="print_btn" style="display: inline-flex; align-items: center; justify-content: center; background-color: #f0f2f6; color: #31333f; padding: 0.5rem 1rem; border: 1px solid rgba(49, 51, 63, 0.2); border-radius: 0.5rem; cursor: pointer; font-size: 1rem; font-weight: 400; width: auto; font-family: sans-serif;">
                🖨️ Abrir Vista de Impresión (PDF)
            </button>
            <script>
                document.getElementById('print_btn').onclick = function() {{
                    var base64 = "{html_b64}";
                    var binaryString = window.atob(base64);
                    var len = binaryString.length;
                    var bytes = new Uint8Array(len);
                    for (var i = 0; i < len; i++) {{ bytes[i] = binaryString.charCodeAt(i); }}
                    var blob = new Blob([bytes], {{ type: 'text/html' }});
                    var url = URL.createObjectURL(blob);
                    window.open(url, '_blank');
                }};
            </script>
        """, height=70)

        evidence_bytes = build_evidence_xlsx(inp.__dict__, results)
        st.download_button(
            label="📥 Descargar Reporte de Evidencia (Excel)",
            data=evidence_bytes,
            file_name="Evidencia_Burden_TC.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Pega el contenido del documento de Word para comenzar.")

def render_normative_module():
    st.subheader("Cálculo de Burden Normativo (CREG 038 / NTC 5019)")
    st.info("Este módulo realiza el cálculo estricto de Burden para sistemas de medida indirecta.")

    pasted_text_ind = st.text_area("Pega aquí el contenido del documento de Word para Medida Indirecta", height=200)
    params = parse_indirect_text(pasted_text_ind) if pasted_text_ind else {}

    with st.form("form_normativo"):
        c1, c2 = st.columns(2)
        with c1:
            tipo_trf = st.selectbox("Tipo de Transformador", ["TC", "TT"], index=0 if params.get("tipo_transformador", "TC") == "TC" else 1)
            
            # Cambio dinámico del label según el tipo de transformador
            corriente_sec_label = "Corriente Secundaria (A)" if tipo_trf == "TC" else "Tensión Secundaria (V)"
            corriente_sec = st.number_input(corriente_sec_label, value=float(params.get("corriente_secundaria_A", 5.0)), step=4.0)
            va_nom_label = f"VA Nominal del {tipo_trf}"
            va_nom_tc = st.number_input(va_nom_label, value=float(params.get("va_nominal_tc", 5.0)))
            burden_med = st.number_input("Burden del Medidor (VA)", value=float(params.get("burden_medidor_VA", 0.35)), format="%.4f")
        
        with c2:
            longitud = st.number_input("Longitud Total ida+retorno (m)", value=float(params.get("longitud_m", 24.0)))
            resistencia = st.number_input("Resistencia AC RAC (Ω/m)", value=float(params.get("resistencia_ohm_m", 0.00625)), format="%.6f")
            n_medidores = st.radio("Número de Medidores", [1, 2], index=0 if params.get("numero_medidores", 1) == 1 else 1, horizontal=True)
        
        submit = st.form_submit_button("Calcular Burden Normativo")

    if submit or pasted_text_ind:
        data_input = {
            "longitud_m": longitud,
            "resistencia_ohm_m": resistencia,
            "corriente_secundaria_A": corriente_sec,
            "burden_medidor_VA": burden_med,
            "numero_medidores": n_medidores,
            "tipo_transformador": tipo_trf,
            "va_nominal_tc": va_nom_tc
        }

        res = calculate_normative_burden(data_input)
        res["resultado"] = "cumple" if res['validaciones']['cumple_rango'] else "no cumple"

        # Visualización de Resultados
        st.divider()
        col_res1, col_res2 = st.columns([1, 1])

        with col_res1:
            st.write("### Cálculos Realizados")
            st.metric("VA Conductor", f"{res['calculos']['VACONDUCTOR']} VA")
            st.metric("VA Medidor Total", f"{res['calculos']['VAMEDIDOR_TOTAL']} VA")
            st.metric("Burden Total (VATOTAL)", f"{res['calculos']['VATOTAL']} VA")

        with col_res2:
            st.write("### Selección y Validación")
            st.write(f"**Burden Normalizado Sugerido:** {res['seleccion']['burden_normalizado']} VA")
            
            # Gauge de Porcentaje de Uso
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = res['seleccion']['porcentaje_uso'],
                title = {'text': f"% Carga del {tipo_trf}"},
                gauge = {
                    'axis': {'range': [0, 120]},
                    'bar': {'color': "black"},
                    'steps': [
                        {'range': [0, 25], 'color': "red"},
                        {'range': [25, 100], 'color': "green"},
                        {'range': [100, 120], 'color': "red"}
                    ],
                    'threshold': {
                        'line': {'color': "blue", 'width': 4},
                        'thickness': 0.75,
                        'value': 100
                    }
                }
            ))
            fig.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig, use_container_width=True)

        if res['validaciones']['cumple_rango']:
            st.success(f"✅ {res['validaciones']['mensaje']}")
        else:
            st.error(f"❌ {res['validaciones']['mensaje']}")
        
        # --- NUEVA SECCIÓN DE IMPRESIÓN Y EXCEL ---
        st.divider()
        
        logo_b64_html = ""
        if os.path.exists("logoemcali.png"):
            logo_b64_html = get_base64_of_bin_file("logoemcali.png")

        # Botón de Impresión HTML
        html_b64 = get_normative_html_print_content(data_input, res, logo_b64_html)
        
        components.html(f"""
            <button id="print_btn_norm" style="display: inline-flex; align-items: center; justify-content: center; background-color: #f0f2f6; color: #31333f; padding: 0.5rem 1rem; border: 1px solid rgba(49, 51, 63, 0.2); border-radius: 0.5rem; cursor: pointer; font-size: 1rem; font-weight: 400; width: auto; font-family: sans-serif;">
                🖨️ Abrir Vista de Impresión (PDF)
            </button>
            <script>
                document.getElementById('print_btn_norm').onclick = function() {{
                    var base64 = "{html_b64}";
                    var binaryString = window.atob(base64);
                    var len = binaryString.length;
                    var bytes = new Uint8Array(len);
                    for (var i = 0; i < len; i++) {{ bytes[i] = binaryString.charCodeAt(i); }}
                    var blob = new Blob([bytes], {{ type: 'text/html' }});
                    var url = URL.createObjectURL(blob);
                    window.open(url, '_blank');
                }};
            </script>
        """, height=70)

        evidence_bytes = build_evidence_xlsx(data_input, res)
        st.download_button(
            label="📥 Descargar Reporte de Evidencia (Excel)",
            data=evidence_bytes,
            file_name="Evidencia_Burden_Normativo.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        # ------------------------------------------

        with st.expander("Ver JSON de integración"):
            st.json(res)

def main():
    st.set_page_config(page_title="Burden / Selección TC – EMCALI", layout="wide")

    # Mostrar Logo y Título en la interfaz de Streamlit
    if os.path.exists("logoemcali.png"):
        st.image("logoemcali.png", width=150)
    st.title("Burden + Selección de TC (Semidirecta / Indirecta)")
    st.caption("Herramienta técnica para la validación de medición y selección de transformadores de corriente.")

    # Créditos del desarrollador en la barra lateral
    st.sidebar.markdown("### Información del Autor")
    st.sidebar.markdown("---")
    st.sidebar.write("👨‍💻 **Ingeniero Walter Andres Betancourt**")

    # Menú de navegación
    menu = st.sidebar.radio(
        "Seleccione el Módulo",
        ["Burden/Selección TC (Plantilla)", "Medida Indirecta CREG 038"],
        index=0
    )

    if menu == "Burden/Selección TC (Plantilla)":
        render_main_module()
    else:
        render_normative_module()

if __name__ == "__main__":
    main()
