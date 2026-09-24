import streamlit as st
import pandas as pd
from datetime import datetime
import io
import zipfile

# Configuración de la ventana web
st.set_page_config(page_title="Procesador SGA & WMS Check", layout="wide")

st.title("📦 Procesador de Archivos de Recepción (SGA y WMS Check)")
st.write("Herramienta para la transformación de datos y generación de archivos de carga masiva.")

# -------------------------------------------------------------
# SECCIÓN 1: CARGA DE ARCHIVOS DE ENTRADA
# -------------------------------------------------------------
st.subheader("1. CARGA DE ARCHIVOS DE ENTRADA")

col1, col2 = st.columns(2)

with col1:
    archivo_packing = st.file_uploader(
        "Cargar Packing List (.xlsx / .csv)", 
        type=["xlsx", "csv"], 
        key="packing"
    )

with col2:
    archivo_maestro = st.file_uploader(
        "Cargar Maestro de Códigos WMS Check (.xlsx / .csv)", 
        type=["xlsx", "csv"], 
        key="maestro"
    )

st.divider()

if st.button("🚀 Procesar y Generar Archivos", type="primary"):
    if not archivo_packing or not archivo_maestro:
        st.error("Por favor, suba ambos archivos de entrada para continuar.")
    else:
        try:
            # -------------------------------------------------------------
            # LECTURA Y PREPARACIÓN DE DATOS (TEXTO / STR)
            # -------------------------------------------------------------
            if archivo_packing.name.endswith('.xlsx'):
                df_packing = pd.read_excel(archivo_packing, dtype=str)
            else:
                df_packing = pd.read_csv(archivo_packing, dtype=str)

            if archivo_maestro.name.endswith('.xlsx'):
                df_maestro = pd.read_excel(archivo_maestro, dtype=str)
            else:
                df_maestro = pd.read_csv(archivo_maestro, dtype=str)

            # Limpieza de espacios en columnas
            df_packing.columns = df_packing.columns.str.strip()
            df_maestro.columns = df_maestro.columns.str.strip()
            
            # Mapeo por posición de columna del Packing List
            imp_col = df_packing.columns[0]
            cod_col = df_packing.columns[1]
            col_col = df_packing.columns[2]
            des_col = df_packing.columns[3]
            qty_col = df_packing.columns[4]

            # Limpieza estricta de cadenas y preservación de ceros
            df_packing[imp_col] = df_packing[imp_col].astype(str).str.strip()
            df_packing[cod_col] = df_packing[cod_col].astype(str).str.strip()
            
            # Preservar exactamente 3 dígitos de color (ej. 1 -> 001, 56 -> 056)
            df_packing['Color_Limpio'] = df_packing[col_col].astype(str).str.strip().apply(lambda x: x.zfill(3) if x.isdigit() else x)
            
            df_packing[des_col] = df_packing[des_col].astype(str).str.strip()
            df_packing['Qty_Int'] = pd.to_numeric(df_packing[qty_col], errors='coerce').fillna(0).astype(int)

            # Código concatenado para WMS (ejemplo: 185649 + 056 = 185649056)
            df_packing['Codigo_WMS'] = df_packing[cod_col] + df_packing['Color_Limpio']

            archivos_para_descarga = {}

            st.success("✅ Archivos procesados correctamente.")

            # -------------------------------------------------------------
            # SECCIÓN 2: INFORME DE ARCHIVOS PROCESADOS
            # -------------------------------------------------------------
            st.subheader("2. INFORME DE ARCHIVOS PROCESADOS")

            # --- A: INGRESO A SGA ---
            st.markdown("#### A. INGRESO A SGA")
            importaciones_unicas = df_packing[imp_col].unique()
            archivos_sga_nombres = []

            for num_imp in importaciones_unicas:
                df_imp = df_packing[df_packing[imp_col] == num_imp]
                header_sga = "codigo;color;unidades;partida (opcional);id_albaran;id_pedido"
                
                filas_sga = (
                    df_imp[cod_col] + ";" +
                    df_imp['Color_Limpio'] + ";" +
                    df_imp['Qty_Int'].astype(str) + ";" +
                    "NA;" +
                    df_imp[imp_col] + ";" +
                    df_imp[imp_col]
                ).tolist()
                
                contenido_sga = header_sga + "\n" + "\n".join(filas_sga)
                nombre_sga = f"IngresoSGA({num_imp}).csv"
                archivos_para_descarga[nombre_sga] = (contenido_sga.encode('utf-8'), "text/csv")
                archivos_sga_nombres.append(nombre_sga)

            st.write(f"• Se han generado **{len(importaciones_unicas)}** archivo(s) distinto(s) por importación:")
            for name in archivos_sga_nombres:
                st.caption(f"  - `{name}`")

            # --- B: TRASPASO DE ADUANA A P2L ---
            st.markdown("#### B. TRASPASO DE ADUANA A P2L")
            header_p2l = "origen;destino;codigo;color;unidades;partida (opcional)"
            filas_p2l = (
                "Aduana;Ubicado P2L;" +
                df_packing[cod_col] + ";" +
                df_packing['Color_Limpio'] + ";" +
                df_packing['Qty_Int'].astype(str) + ";" +
                "NA"
            ).tolist()
            
            contenido_p2l = header_p2l + "\n" + "\n".join(filas_p2l)
            archivos_para_descarga["TraspasoAduanaP2L.csv"] = (contenido_p2l.encode('utf-8'), "text/csv")
            st.write("• Archivo consolidado generado:")
            st.caption("  - `TraspasoAduanaP2L.csv`")

            # --- C: CREACIÓN DE NUEVOS CÓDIGOS ---
            st.markdown("#### C. CREACIÓN DE NUEVOS CÓDIGOS")
            col_maestro_cod = df_maestro.columns[0]
            codigos_maestro_set = set(df_maestro[col_maestro_cod].astype(str).str.strip())

            df_nuevos = df_packing[~df_packing['Codigo_WMS'].isin(codigos_maestro_set)].copy()
            total_codigos = len(df_packing)
            nuevos_count = len(df_nuevos)

            st.write(f"• De los **{total_codigos}** códigos del packing list, se han detectado **{nuevos_count}** código(s) nuevo(s) para su creación.")

            if nuevos_count > 0:
                df_crear_wms = pd.DataFrame()
                df_crear_wms['codigo'] = df_nuevos['Codigo_WMS']
                df_crear_wms['coddun'] = ""
                df_crear_wms['codean'] = ""
                df_crear_wms['familialogistica'] = "LA CARCASA"
                df_crear_wms['matunidadmedida'] = "UNIDAD"
                df_crear_wms['matunidadmedidaconteofisico'] = ""
                df_crear_wms['rotacion'] = "A"
                df_crear_wms['descripcionmaterial'] = df_nuevos[des_col]
                df_crear_wms['volumen'] = ""
                df_crear_wms['peso'] = ""
                df_crear_wms['cantporpalet'] = 0
                df_crear_wms['manejalote'] = 0
                df_crear_wms['serie'] = 0
                df_crear_wms['escaneounitario'] = 0
                df_crear_wms['manejadecimal'] = 0
                df_crear_wms['urlasociada'] = ""
                df_crear_wms['cantporempaque'] = 1
                df_crear_wms['materialnecesitamaquila'] = 0
                df_crear_wms['accion'] = "crear"

                output_nuevos = io.BytesIO()
                with pd.ExcelWriter(output_nuevos, engine='openpyxl') as writer:
                    df_crear_wms.to_excel(writer, index=False)
                
                archivos_para_descarga["CrearCodigosNuevosWMS.xlsx"] = (
                    output_nuevos.getvalue(), 
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                st.caption("  - `CrearCodigosNuevosWMS.xlsx`")

            # --- D: INGRESO A WMS CHECK ---
            st.markdown("#### D. INGRESO A WMS CHECK")
            fecha_hoy = datetime.now().strftime("%Y%m%d")

            df_ingreso_wms = pd.DataFrame()
            df_ingreso_wms['pre_cod_tdo'] = ["GR"] * len(df_packing)
            df_ingreso_wms['pre_fec_emi'] = [fecha_hoy] * len(df_packing)
            df_ingreso_wms['pre_eta_pre'] = [fecha_hoy] * len(df_packing)
            df_ingreso_wms['pre_num_doc'] = df_packing[imp_col].values
            df_ingreso_wms['pre_lin_doc'] = range(1, len(df_packing) + 1)
            df_ingreso_wms['pre_cod_pro'] = ["20613901435"] * len(df_packing)
            df_ingreso_wms['pre_des_pro'] = ["LA CARCASA MOVIL"] * len(df_packing)
            df_ingreso_wms['pre_cod_mat'] = df_packing['Codigo_WMS'].values
            df_ingreso_wms['pre_pdt_mat'] = df_packing['Qty_Int'].values
            df_ingreso_wms['pre_cod_ua'] = range(1, len(df_packing) + 1)

            csv_ingreso_wms = df_ingreso_wms.to_csv(index=False, sep=';').encode('utf-8')
            archivos_para_descarga["IngresoWMS.csv"] = (csv_ingreso_wms, "text/csv")
            st.write("• Archivo generado para el ingreso masivo a WMS Check:")
            st.caption("  - `IngresoWMS.csv`")

            st.divider()

            # -------------------------------------------------------------
            # SECCIÓN 3: DESCARGA DE ARCHIVOS
            # -------------------------------------------------------------
            st.subheader("3. DESCARGA DE ARCHIVOS")

            # Botones para descargas individuales directas
            for nombre_archivo, (contenido_bytes, mime_type) in archivos_para_descarga.items():
                st.download_button(
                    label=f"📥 Descargar {nombre_archivo}",
                    data=contenido_bytes,
                    file_name=nombre_archivo,
                    mime=mime_type,
                    key=f"down_{nombre_archivo}"
                )

            st.markdown("---")
            
            # Opción empaquetada unificada (.ZIP)
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for nombre_archivo, (contenido_bytes, _) in archivos_para_descarga.items():
                    zip_file.writestr(nombre_archivo, contenido_bytes)

            st.download_button(
                label="📦 DESCARGAR PAQUETE COMPLETO (.ZIP)",
                data=zip_buffer.getvalue(),
                file_name=f"Recepcion_Procesada_{fecha_hoy}.zip",
                mime="application/zip",
                type="primary"
            )

        except Exception as e:
            st.error(f"Ocurrió un error inesperado al procesar los archivos: {str(e)}")