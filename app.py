import streamlit as st
import pandas as pd
from datetime import datetime
import io
import zipfile

# Configuración de la página
st.set_page_config(page_title="Procesador SGA & WMS Check", layout="wide")

st.title("📦 Procesador de Archivos de Recepción y Consulta de Ubicaciones")
st.write("Herramienta para la transformación de datos, generación de archivos masivos y consolidado de stock existente.")

# -------------------------------------------------------------
# SECCIÓN 1: CARGA DE ARCHIVOS DE ENTRADA
# -------------------------------------------------------------
st.subheader("1. CARGA DE ARCHIVOS DE ENTRADA")

st.info(
    "📋 **Nota sobre el Packing List:** "
    "Asegúrese de que la estructura de columnas sea: "
    "**N° Importación | Código | Color | Descripción | Cantidad** (en ese orden). "
    "Todos los campos deben estar completos (sin celdas en blanco). "
    "El Maestro de Códigos y el Reporte de Stock se cargan tal como se descargan del sistema."
)

col1, col2, col3 = st.columns(3)

with col1:
    archivo_packing = st.file_uploader(
        "1. Packing List (.xlsx / .csv) *", 
        type=["xlsx", "csv"], 
        key="packing"
    )

with col2:
    archivo_maestro = st.file_uploader(
        "2. Maestro de Códigos (.xlsx / .csv) *", 
        type=["xlsx", "csv"], 
        key="maestro"
    )

with col3:
    archivo_stock = st.file_uploader(
        "3. Reporte de Stock (.xlsx / .csv) [Opcional]", 
        type=["xlsx", "csv"], 
        key="stock"
    )

st.divider()

if st.button("🚀 Procesar y Generar Archivos", type="primary"):
    if not archivo_packing or not archivo_maestro:
        st.error("Por favor, suba al menos el Packing List y el Maestro de Códigos para continuar.")
    else:
        try:
            # -------------------------------------------------------------
            # LECTURA DE ARCHIVOS
            # -------------------------------------------------------------
            if archivo_packing.name.endswith('.xlsx'):
                df_packing = pd.read_excel(archivo_packing, dtype=str)
            else:
                df_packing = pd.read_csv(archivo_packing, dtype=str)

            if archivo_maestro.name.endswith('.xlsx'):
                df_maestro = pd.read_excel(archivo_maestro, dtype=str)
            else:
                df_maestro = pd.read_csv(archivo_maestro, dtype=str)

            # Limpieza de espacios en encabezados
            df_packing.columns = df_packing.columns.str.strip()
            df_maestro.columns = df_maestro.columns.str.strip()
            
            # Mapeo por posición de columna
            imp_col = df_packing.columns[0]
            cod_col = df_packing.columns[1]
            col_col = df_packing.columns[2]
            des_col = df_packing.columns[3]
            qty_col = df_packing.columns[4]

            # -------------------------------------------------------------
            # VALIDACIÓN ESTRICTA DE CAMPOS VACÍOS EN PACKING LIST
            # -------------------------------------------------------------
            # Crear copias limpias para comprobar celdas vacías o con puros espacios
            c_imp = df_packing[imp_col].fillna('').astype(str).str.strip()
            c_cod = df_packing[cod_col].fillna('').astype(str).str.strip()
            c_col = df_packing[col_col].fillna('').astype(str).str.strip()
            c_des = df_packing[des_col].fillna('').astype(str).str.strip()
            c_qty = pd.to_numeric(df_packing[qty_col], errors='coerce').fillna(0)

            # Detectar filas con vacíos o cantidades invalidas (<= 0)
            mask_vacios = (c_imp == '') | (c_cod == '') | (c_col == '') | (c_des == '') | (c_qty <= 0)
            filas_con_error = df_packing[mask_vacios]

            if not filas_con_error.empty:
                st.error(
                    f"⛔ **Proceso detenido:** Se detectaron **{len(filas_con_error)}** fila(s) con campos en blanco o cantidades inválidas en el **Packing List**.\n\n"
                    "Por favor, revise y complete el archivo Excel antes de volver a subirlo."
                )
                
                # Mostrar vista previa de las filas con vacíos para facilitar la corrección
                with st.expander("🔍 Ver filas con campos vacíos o errores para corregir"):
                    st.dataframe(filas_con_error[[imp_col, cod_col, col_col, des_col, qty_col]], use_container_width=True)
                
                st.stop() # Interrumpe la ejecución para que no genere archivos

            # -------------------------------------------------------------
            # PROCESAMIENTO DE DATOS (SI TODO ESTÁ CORRECTO)
            # -------------------------------------------------------------
            df_packing[imp_col] = c_imp
            df_packing[cod_col] = c_cod
            df_packing[col_col] = c_col
            df_packing[des_col] = c_des
            df_packing['Qty_Int'] = c_qty.astype(int)

            # Preservar exactamente 3 dígitos de color (ej. 1 -> 001, 56 -> 056)
            df_packing['Color_Limpio'] = df_packing[col_col].apply(lambda x: x.zfill(3) if x.isdigit() else x)

            # Código concatenado para WMS (ejemplo: 185649 + 056 = 185649056)
            df_packing['Codigo_WMS'] = df_packing[cod_col] + df_packing['Color_Limpio']

            # Cargar Maestro para validación
            col_maestro_cod = df_maestro.columns[0]
            codigos_maestro_set = set(df_maestro[col_maestro_cod].fillna('').astype(str).str.strip())

            archivos_para_descarga = {}

            st.success("✅ Archivos procesados correctamente sin errores de vacíos.")

            # -------------------------------------------------------------
            # SECCIÓN 2: INFORME DE ARCHIVOS PROCESADOS (COMPACTO)
            # -------------------------------------------------------------
            st.markdown("### 2. GENERACIÓN DE PLANILLAS DE RECEPCIÓN")

            st.markdown("", unsafe_allow_html=True)

            # --- A: INGRESO A SGA ---
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

            sga_txt = ", ".join([f"`{n}`" for n in archivos_sga_nombres])
            st.markdown(f"**A. INGRESO A SGA:** {len(importaciones_unicas)} archivo(s) generado(s) → {sga_txt}")

            # --- B: TRASPASO DE ADUANA A P2L ---
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
            st.markdown("**B. TRASPASO DE ADUANA A P2L:** Archivo generado → `TraspasoAduanaP2L.csv`")

            # --- C: CREACIÓN DE NUEVOS CÓDIGOS ---
            df_nuevos = df_packing[~df_packing['Codigo_WMS'].isin(codigos_maestro_set)].copy()
            nuevos_count = len(df_nuevos)

            if nuevos_count > 0:
                df_crear_wms = pd.DataFrame()
                df_crear_wms['codigo'] = df_nuevos['Codigo_WMS']
                df_crear_wms['coddun'] = ""
                df_crear_wms['codean'] = ""
                df_crear_wms['familialogistica'] = "LA CARCASA MOVIL"
                df_crear_wms['matunidadmedida'] = "UNIDAD"
                df_crear_wms['matunidadmedida2'] = ""
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
                st.markdown(f"**C. CREACIÓN DE NUEVOS CÓDIGOS:** {nuevos_count} código(s) nuevo(s) detectado(s) → `CrearCodigosNuevosWMS.xlsx`")
            else:
                st.markdown("**C. CREACIÓN DE NUEVOS CÓDIGOS:** 0 códigos nuevos detectados.")

            # --- D: INGRESO A WMS CHECK ---
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
            st.markdown("**D. INGRESO A WMS CHECK:** Archivo generado → `IngresoWMS.csv`")

            # --- E: UBICACIÓN DE CÓDIGOS RECEPCIONADOS ---
            if archivo_stock is not None:
                if archivo_stock.name.endswith('.xlsx'):
                    df_stock = pd.read_excel(archivo_stock, dtype=str)
                else:
                    df_stock = pd.read_csv(archivo_stock, dtype=str)
                
                df_stock.columns = df_stock.columns.str.strip()
                
                col_stock_cod = 'Código' if 'Código' in df_stock.columns else df_stock.columns[1]
                col_stock_ubi = 'Ubicación' if 'Ubicación' in df_stock.columns else df_stock.columns[5]
                col_stock_cant = 'Stock Físico' if 'Stock Físico' in df_stock.columns else df_stock.columns[9]

                df_stock[col_stock_cod] = df_stock[col_stock_cod].fillna('').astype(str).str.strip()
                df_stock[col_stock_ubi] = df_stock[col_stock_ubi].fillna('').astype(str).str.strip()
                df_stock['Stock_Num'] = pd.to_numeric(df_stock[col_stock_cant], errors='coerce').fillna(0)

                # Filtrar exclusiones (C1-DSP-1 y C1-REC-1) y stock <= 0
                df_stock_valido = df_stock[
                    (~df_stock[col_stock_ubi].isin(['C1-DSP-1', 'C1-REC-1'])) & 
                    (df_stock['Stock_Num'] > 0)
                ].copy()

                stock_agrupado = df_stock_valido.groupby(col_stock_cod).agg(
                    UBICACION=(col_stock_ubi, lambda x: " | ".join(sorted(x.unique()))),
                    STOCK=('Stock_Num', 'sum')
                ).reset_index()

                df_cruce = pd.merge(
                    df_packing, 
                    stock_agrupado, 
                    left_on='Codigo_WMS', 
                    right_on=col_stock_cod, 
                    how='left'
                )

                df_cruce['STOCK'] = df_cruce['STOCK'].fillna(0).astype(int)
                df_con_stock = df_cruce[df_cruce['STOCK'] > 0].copy()

                total_recepcionados = len(df_packing)
                total_con_stock = len(df_con_stock)

                if total_con_stock > 0:
                    df_salida_excel = pd.DataFrame()
                    df_salida_excel['CODIGO'] = df_con_stock['Codigo_WMS']
                    df_salida_excel['DESCRIPCION'] = df_con_stock[des_col]
                    df_salida_excel['UBICACION'] = df_con_stock['UBICACION']
                    df_salida_excel['PACKING'] = df_con_stock['Qty_Int']
                    df_salida_excel['STOCK'] = df_con_stock['STOCK']
                    df_salida_excel['TOTAL'] = df_salida_excel['PACKING'] + df_salida_excel['STOCK']

                    output_consolidado = io.BytesIO()
                    with pd.ExcelWriter(output_consolidado, engine='openpyxl') as writer:
                        df_salida_excel.to_excel(writer, index=False, sheet_name="Ubicaciones_Stock")

                    archivos_para_descarga["UbicacionCodigosRecepcionado.xlsx"] = (
                        output_consolidado.getvalue(),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    st.markdown(f"**E. UBICACIÓN DE CÓDIGOS RECEPCIONADOS:** De **{total_recepcionados}** códigos recepcionados, **{total_con_stock}** tienen stock → `UbicacionCodigosRecepcionado.xlsx`")
                else:
                    st.markdown(f"**E. UBICACIÓN DE CÓDIGOS RECEPCIONADOS:** De **{total_recepcionados}** códigos recepcionados, ninguno tiene stock.")
            else:
                st.markdown("**E. UBICACIÓN DE CÓDIGOS RECEPCIONADOS:** No se subió archivo de Reporte de Stock.")

            st.markdown("", unsafe_allow_html=True)

            st.divider()

            # -------------------------------------------------------------
            # SECCIÓN 3: DESCARGA DE ARCHIVOS
            # -------------------------------------------------------------
            st.subheader("3. DESCARGA DE ARCHIVOS")

            # Botón de Descarga Global (.ZIP)
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

            st.write("")

            # Menú desplegable para descargas individuales
            with st.expander("🔻 Detalle de descargas individuales"):
                for nombre_archivo, (contenido_bytes, mime_type) in archivos_para_descarga.items():
                    st.download_button(
                        label=f"📥 Descargar {nombre_archivo}",
                        data=contenido_bytes,
                        file_name=nombre_archivo,
                        mime=mime_type,
                        key=f"down_{nombre_archivo}"
                    )

        except Exception as e:
            st.error(f"Ocurrió un error inesperado al procesar los archivos: {str(e)}")