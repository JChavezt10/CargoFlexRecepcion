import io
import zipfile
from datetime import datetime

import pandas as pd
import streamlit as st


# =========================================================
# FUNCIÓN PRINCIPAL DEL MÓDULO
# =========================================================
def render():
    # Inicializar Session State
    if "ac_procesado" not in st.session_state:
        st.session_state.ac_procesado = False
    if "ac_archivos_para_descarga" not in st.session_state:
        st.session_state.ac_archivos_para_descarga = {}
    if "ac_informe_html" not in st.session_state:
        st.session_state.ac_informe_html = []

    # -------------------------------------------------------------
    # TÍTULO
    # -------------------------------------------------------------
    st.header("📦 Procesador de Archivos de Recepción (SGA & WMS)")

    st.divider()

    # -------------------------------------------------------------
    # SECCIÓN 1: CARGA DE ARCHIVOS DE ENTRADA
    # -------------------------------------------------------------
    st.subheader("1. Carga de Archivos de Entrada")

    with st.expander(
        "📖 Instrucciones para el procesamiento (Haz clic para expandir)",
        expanded=False,
    ):
        st.warning(
            "📌 **NOTA IMPORTANTE:** Asegúrese de que la estructura de las columnas "
            "del archivo **Packing List** sea estrictamente en este orden "
            "(sin importar los nombres de encabezado):\n\n"
            "**| N° Importación | Código | Color | Descripción | Cantidad |**"
        )

        st.markdown("### 📋 Reglas de procesamiento según archivos subidos:")
        st.write("")

        col_p1, col_p2, col_p3 = st.columns(3, gap="large")

        with col_p1:
            st.markdown("""
            <div style="
                background-color: rgba(128, 128, 128, 0.12);
                border-left: 4px solid #7AB800;
                border-radius: 8px;
                padding: 12px 14px;
                height: 100%;
                color: inherit;
                font-size: 0.85rem;
                line-height: 1.3;
            ">
                <h4 style="margin: 0 0 6px 0; color: inherit; font-size: 1rem;">📘 Parte 1</h4>
                <p style="margin: 4px 0; color: inherit;"><b>Si sube solo el Packing List:</b></p>
                <p style="margin: 4px 0; color: inherit;">Se generarán los archivos de:</p>
                <p style="margin: 4px 0; color: inherit;">• <b>Ingreso a SGA</b> (Aduana)</p>
                <p style="margin: 4px 0; color: inherit;">• <b>Traspaso a P2L</b></p>
            </div>
            """, unsafe_allow_html=True)

        with col_p2:
            st.markdown("""
            <div style="
                background-color: rgba(128, 128, 128, 0.12);
                border-left: 4px solid #7AB800;
                border-radius: 8px;
                padding: 12px 14px;
                height: 100%;
                color: inherit;
                font-size: 0.85rem;
                line-height: 1.3;
            ">
                <h4 style="margin: 0 0 6px 0; color: inherit; font-size: 1rem;">📗 Parte 2</h4>
                <p style="margin: 4px 0; color: inherit;"><b>Si sube Packing List + Maestro de Códigos:</b></p>
                <p style="margin: 4px 0; color: inherit;">Se generarán los archivos de:</p>
                <p style="margin: 4px 0; color: inherit;">• <b>Ingreso a SGA</b> / <b>Traspaso a P2L</b></p>
                <p style="margin: 4px 0; color: inherit;">• <b>Crear Códigos Nuevos</b></p>
                <p style="margin: 4px 0; color: inherit;">• <b>Ingreso a WMS</b></p>
            </div>
            """, unsafe_allow_html=True)

        with col_p3:
            st.markdown("""
            <div style="
                background-color: rgba(128, 128, 128, 0.12);
                border-left: 4px solid #7AB800;
                border-radius: 8px;
                padding: 12px 14px;
                height: 100%;
                color: inherit;
                font-size: 0.85rem;
                line-height: 1.3;
            ">
                <h4 style="margin: 0 0 6px 0; color: inherit; font-size: 1rem;">📙 Parte 3</h4>
                <p style="margin: 4px 0; color: inherit;"><b>Si sube los 3 archivos (+ Reporte Stock):</b></p>
                <p style="margin: 4px 0; color: inherit;">Se generarán todos los archivos anteriores más:</p>
                <p style="margin: 4px 0; color: inherit;">• <b>Ubicación de Códigos Recepcionados</b><br><i>(Cruce para visualizar ubicaciones existentes en Stock)</i></p>
            </div>
            """, unsafe_allow_html=True)

    # Carga de Archivos
    col1, col2, col3 = st.columns(3)

    with col1:
        archivo_packing = st.file_uploader(
            "1. Packing List (.xlsx / .csv) *",
            type=["xlsx", "csv"],
            key="ac_packing",
        )

    with col2:
        archivo_maestro = st.file_uploader(
            "2. Maestro de Códigos (.xlsx / .csv) [Opcional]",
            type=["xlsx", "csv"],
            key="ac_maestro",
        )

    with col3:
        archivo_stock = st.file_uploader(
            "3. Reporte de Stock (.xlsx / .csv) [Opcional]",
            type=["xlsx", "csv"],
            key="ac_stock",
        )

    st.write("")

    # Botón de Procesamiento
    if st.button(
        "🚀 Procesar y Generar Archivos",
        type="primary",
        key="ac_btn_procesar",
    ):
        if not archivo_packing:
            st.error(
                "⛔ Por favor, suba al menos el **Packing List** para comenzar el procesamiento."
            )
            st.session_state.ac_procesado = False
        else:
            try:
                tiene_maestro = archivo_maestro is not None
                tiene_stock = archivo_stock is not None

                # -------------------------------------------------------------
                # LECTURA DEL PACKING LIST
                # -------------------------------------------------------------
                if archivo_packing.name.endswith(".xlsx"):
                    df_packing = pd.read_excel(archivo_packing, dtype=str)
                else:
                    df_packing = pd.read_csv(archivo_packing, dtype=str)

                df_packing.columns = df_packing.columns.str.strip()

                imp_col = df_packing.columns[0]
                cod_col = df_packing.columns[1]
                col_col = df_packing.columns[2]
                des_col = df_packing.columns[3]
                qty_col = df_packing.columns[4]

                c_imp = df_packing[imp_col].fillna("").astype(str).str.strip()
                c_cod = df_packing[cod_col].fillna("").astype(str).str.strip()
                c_col = df_packing[col_col].fillna("").astype(str).str.strip()
                c_des = df_packing[des_col].fillna("").astype(str).str.strip()
                c_qty = pd.to_numeric(df_packing[qty_col], errors="coerce").fillna(0)

                # -------------------------------------------------------------
                # VALIDACIÓN DE CAMPOS CRÍTICOS (sin Descripción)
                # -------------------------------------------------------------
                mask_vacios = (
                    (c_imp == "")
                    | (c_cod == "")
                    | (c_col == "")
                    | (c_qty <= 0)
                )

                filas_con_error = df_packing[mask_vacios]

                if not filas_con_error.empty:
                    st.error(
                        f"⛔ **Proceso detenido:** Se encontraron "
                        f"**{len(filas_con_error)}** fila(s) con errores en campos críticos."
                    )
                    st.warning(
                        "⚠️ Se detectaron celdas en blanco (en Importación, Código o Color) "
                        "o cantidades inválidas en el **Packing List**."
                    )
                    with st.expander(
                        "🔍 Ver filas con campos vacíos o errores para corregir"
                    ):
                        st.dataframe(
                            filas_con_error[
                                [imp_col, cod_col, col_col, des_col, qty_col]
                            ],
                            use_container_width=True,
                        )
                    st.session_state.ac_procesado = False
                    st.stop()

                # Preparar DataFrame limpio
                df_packing[imp_col] = c_imp
                df_packing[cod_col] = c_cod
                df_packing[col_col] = c_col
                df_packing[des_col] = c_des
                df_packing["Qty_Int"] = c_qty.astype(int)

                df_packing["Color_Limpio"] = df_packing[col_col].apply(
                    lambda x: x.zfill(3) if x.isdigit() else x
                )
                df_packing["Codigo_WMS"] = df_packing[cod_col] + df_packing["Color_Limpio"]

                archivos_temp = {}
                informe_temp = []

                total_codigos_unicos_packing = df_packing["Codigo_WMS"].nunique()

                # -------------------------------------------------------------
                # ETAPA 1: SGA Y P2L (SIEMPRE SE GENERAN)
                # -------------------------------------------------------------
                importaciones_unicas = df_packing[imp_col].unique()
                archivos_sga_nombres = []

                for num_imp in importaciones_unicas:
                    df_imp = df_packing[df_packing[imp_col] == num_imp]
                    header_sga = (
                        "codigo;color;unidades;partida (opcional);"
                        "id_albaran;id_pedido"
                    )
                    filas_sga = (
                        df_imp[cod_col]
                        + ";"
                        + df_imp["Color_Limpio"]
                        + ";"
                        + df_imp["Qty_Int"].astype(str)
                        + ";"
                        + "NA;"
                        + df_imp[imp_col]
                        + ";"
                        + df_imp[imp_col]
                    ).tolist()

                    contenido_sga = header_sga + "\n" + "\n".join(filas_sga)
                    nombre_sga = f"IngresoSGA({num_imp}).csv"
                    archivos_temp[nombre_sga] = (
                        contenido_sga.encode("utf-8"),
                        "text/csv",
                    )
                    archivos_sga_nombres.append(nombre_sga)

                sga_txt = ", ".join([f"`{n}`" for n in archivos_sga_nombres])
                informe_temp.append(
                    f"**A. INGRESO A SGA:** {len(importaciones_unicas)} archivo(s) "
                    f"generado(s) → {sga_txt}"
                )

                header_p2l = "origen;destino;codigo;color;unidades;partida (opcional)"
                filas_p2l = (
                    "Aduana;Ubicado P2L;"
                    + df_packing[cod_col]
                    + ";"
                    + df_packing["Color_Limpio"]
                    + ";"
                    + df_packing["Qty_Int"].astype(str)
                    + ";"
                    + "NA"
                ).tolist()
                contenido_p2l = header_p2l + "\n" + "\n".join(filas_p2l)
                archivos_temp["TraspasoAduanaP2L.csv"] = (
                    contenido_p2l.encode("utf-8"),
                    "text/csv",
                )
                informe_temp.append(
                    "**B. TRASPASO DE ADUANA A P2L:** Archivo generado → "
                    "`TraspasoAduanaP2L.csv`"
                )

                # -------------------------------------------------------------
                # ETAPA 2: MAESTRO DE CÓDIGOS Y WMS
                # -------------------------------------------------------------
                cant_existentes_maestro = 0
                cant_nuevos = 0
                codigos_existentes_set = set()
                bloqueo_wms = False   # ← bandera de bloqueo parcial

                if tiene_maestro:
                    if archivo_maestro.name.endswith(".xlsx"):
                        df_maestro = pd.read_excel(archivo_maestro, dtype=str)
                    else:
                        df_maestro = pd.read_csv(archivo_maestro, dtype=str)

                    df_maestro.columns = df_maestro.columns.str.strip()
                    col_maestro_cod = df_maestro.columns[0]
                    codigos_maestro_set = set(
                        df_maestro[col_maestro_cod]
                        .fillna("")
                        .astype(str)
                        .str.strip()
                    )

                    codigos_packing_unicos = set(df_packing["Codigo_WMS"].unique())
                    codigos_nuevos_set = codigos_packing_unicos - codigos_maestro_set
                    codigos_existentes_set = codigos_packing_unicos.intersection(
                        codigos_maestro_set
                    )

                    cant_nuevos = len(codigos_nuevos_set)
                    cant_existentes_maestro = len(codigos_existentes_set)

                    # ---------------------------------------------------------
                    # VALIDACIÓN CONDICIONAL DE DESCRIPCIÓN
                    # Si hay códigos nuevos sin descripción → se bloquea solo C, D y E
                    # pero A (SGA) y B (P2L) ya generados se conservan.
                    # ---------------------------------------------------------
                    if cant_nuevos > 0:
                        mask_nuevos = df_packing["Codigo_WMS"].isin(codigos_nuevos_set)
                        mask_desc_vacia = (
                            df_packing[des_col].fillna("").astype(str).str.strip() == ""
                        )
                        filas_nuevas_sin_desc = df_packing[mask_nuevos & mask_desc_vacia]

                        if not filas_nuevas_sin_desc.empty:
                            bloqueo_wms = True
                            st.warning(
                                f"⚠️ **Aviso:** Se detectaron "
                                f"**{len(filas_nuevas_sin_desc)}** fila(s) con "
                                f"**Descripción vacía** en códigos que **NO existen "
                                f"en el Maestro de Materiales**.\n\n"
                                f"👉 Se generaron con normalidad los archivos de "
                                f"**Ingreso a SGA** y **Traspaso a P2L** (Parte 1).\n\n"
                                f"👉 **NO** se generarán los archivos de "
                                f"**Creación de Nuevos Códigos** ni **Ingreso a WMS** "
                                f"porque la Descripción es obligatoria para crear "
                                f"los materiales en WMS."
                            )
                            with st.expander(
                                "🔍 Ver filas de códigos nuevos sin Descripción"
                            ):
                                st.dataframe(
                                    filas_nuevas_sin_desc[
                                        [imp_col, cod_col, col_col, des_col, qty_col]
                                    ],
                                    use_container_width=True,
                                )
                                st.caption(
                                    "Corrige el archivo Packing List agregando la "
                                    "Descripción en estas filas y vuelve a procesar."
                                )

                    # ---------------------------------------------------------
                    # GENERACIÓN DE CÓDIGOS NUEVOS Y WMS (solo si NO hay bloqueo)
                    # ---------------------------------------------------------
                    if not bloqueo_wms:
                        # ---------------- Archivo C: Crear Códigos ----------------
                        if cant_nuevos > 0:
                            df_nuevos = (
                                df_packing[df_packing["Codigo_WMS"].isin(codigos_nuevos_set)]
                                .drop_duplicates(subset=["Codigo_WMS"])
                                .copy()
                            )

                            df_crear_wms = pd.DataFrame()
                            df_crear_wms["codigo"] = df_nuevos["Codigo_WMS"]
                            df_crear_wms["coddun"] = ""
                            df_crear_wms["codean"] = ""
                            df_crear_wms["familialogistica"] = "LA CARCASA MOVIL"
                            df_crear_wms["matunidadmedida"] = "UNIDAD"
                            df_crear_wms["matunidadmedida2"] = ""
                            df_crear_wms["rotacion"] = "A"
                            df_crear_wms["descripcionmaterial"] = df_nuevos[des_col]
                            df_crear_wms["volumen"] = ""
                            df_crear_wms["peso"] = ""
                            df_crear_wms["cantporpalet"] = 0
                            df_crear_wms["manejalote"] = 0
                            df_crear_wms["serie"] = 0
                            df_crear_wms["escaneounitario"] = 0
                            df_crear_wms["manejadecimal"] = 0
                            df_crear_wms["urlasociada"] = ""
                            df_crear_wms["cantporempaque"] = 1
                            df_crear_wms["materialnecesitamaquila"] = 0
                            df_crear_wms["accion"] = "crear"

                            output_nuevos = io.BytesIO()
                            with pd.ExcelWriter(output_nuevos, engine="openpyxl") as writer:
                                df_crear_wms.to_excel(writer, index=False)

                            archivos_temp["CrearCodigosNuevosWMS.xlsx"] = (
                                output_nuevos.getvalue(),
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            )
                            informe_temp.append(
                                f"**C. CREACIÓN DE NUEVOS CÓDIGOS:** **{cant_nuevos}** "
                                f"código(s) nuevo(s) detectado(s) de "
                                f"**{total_codigos_unicos_packing}** recepcionados → "
                                f"`CrearCodigosNuevosWMS.xlsx`"
                            )
                        else:
                            informe_temp.append(
                                f"**C. CREACIÓN DE NUEVOS CÓDIGOS:** 0 códigos nuevos "
                                f"detectados de **{total_codigos_unicos_packing}** "
                                f"recepcionados (Todos ya existen en el Maestro)."
                            )

                        # ---------------- Archivo D: Ingreso WMS ----------------
                        fecha_hoy = datetime.now().strftime("%Y%m%d")
                        df_ingreso_wms = pd.DataFrame()
                        df_ingreso_wms["pre_cod_tdo"] = ["GR"] * len(df_packing)
                        df_ingreso_wms["pre_fec_emi"] = [fecha_hoy] * len(df_packing)
                        df_ingreso_wms["pre_eta_pre"] = [fecha_hoy] * len(df_packing)
                        df_ingreso_wms["pre_num_doc"] = df_packing[imp_col].values
                        df_ingreso_wms["pre_lin_doc"] = range(1, len(df_packing) + 1)
                        df_ingreso_wms["pre_cod_pro"] = ["20613901435"] * len(df_packing)
                        df_ingreso_wms["pre_des_pro"] = ["LA CARCASA MOVIL"] * len(df_packing)
                        df_ingreso_wms["pre_cod_mat"] = df_packing["Codigo_WMS"].values
                        df_ingreso_wms["pre_pdt_mat"] = df_packing["Qty_Int"].values
                        df_ingreso_wms["pre_cod_ua"] = range(1, len(df_packing) + 1)

                        csv_ingreso_wms = df_ingreso_wms.to_csv(
                            index=False, sep=";"
                        ).encode("utf-8")
                        archivos_temp["IngresoWMS.csv"] = (csv_ingreso_wms, "text/csv")
                        informe_temp.append(
                            "**D. INGRESO A WMS CHECK:** Archivo generado → "
                            "`IngresoWMS.csv`"
                        )
                    else:
                        # Bloqueo: se omite C y D
                        informe_temp.append(
                            "⏸️ **C. CREACIÓN DE NUEVOS CÓDIGOS:** Omitido por "
                            "**Descripción vacía en códigos nuevos**. Corrige el Packing "
                            "List y vuelve a procesar."
                        )
                        informe_temp.append(
                            "⏸️ **D. INGRESO A WMS CHECK:** Omitido por "
                            "**Descripción vacía en códigos nuevos**. Corrige el Packing "
                            "List y vuelve a procesar."
                        )
                else:
                    informe_temp.append(
                        "ℹ️ **C. CREACIÓN DE NUEVOS CÓDIGOS:** Omitido "
                        "(Requiere Maestro de Códigos)."
                    )
                    informe_temp.append(
                        "ℹ️ **D. INGRESO A WMS CHECK:** Omitido "
                        "(Requiere Maestro de Códigos)."
                    )

                # -------------------------------------------------------------
                # ETAPA 3: UBICACIÓN DE CÓDIGOS (REQUIERE MAESTRO Y STOCK)
                # -------------------------------------------------------------
                if (not bloqueo_wms) and tiene_stock and tiene_maestro:
                    if archivo_stock.name.endswith(".xlsx"):
                        df_stock = pd.read_excel(archivo_stock, dtype=str)
                    else:
                        df_stock = pd.read_csv(archivo_stock, dtype=str)

                    df_stock.columns = df_stock.columns.str.strip()
                    col_stock_cod = (
                        "Código" if "Código" in df_stock.columns else df_stock.columns[1]
                    )
                    col_stock_ubi = (
                        "Ubicación"
                        if "Ubicación" in df_stock.columns
                        else df_stock.columns[5]
                    )
                    col_stock_cant = (
                        "Stock Físico"
                        if "Stock Físico" in df_stock.columns
                        else df_stock.columns[9]
                    )

                    df_stock[col_stock_cod] = (
                        df_stock[col_stock_cod].fillna("").astype(str).str.strip()
                    )
                    df_stock[col_stock_ubi] = (
                        df_stock[col_stock_ubi].fillna("").astype(str).str.strip()
                    )
                    df_stock["Stock_Num"] = pd.to_numeric(
                        df_stock[col_stock_cant], errors="coerce"
                    ).fillna(0)

                    df_stock_valido = df_stock[
                        (~df_stock[col_stock_ubi].isin(["C1-DSP-1", "C1-REC-1"]))
                        & (df_stock["Stock_Num"] > 0)
                    ].copy()

                    stock_agrupado = (
                        df_stock_valido.groupby(col_stock_cod)
                        .agg(
                            UBICACION=(
                                col_stock_ubi,
                                lambda x: " | ".join(sorted(x.unique())),
                            ),
                            STOCK=("Stock_Num", "sum"),
                        )
                        .reset_index()
                    )

                    df_packing_existentes = df_packing[
                        df_packing["Codigo_WMS"].isin(codigos_existentes_set)
                    ].copy()

                    df_cruce = pd.merge(
                        df_packing_existentes,
                        stock_agrupado,
                        left_on="Codigo_WMS",
                        right_on=col_stock_cod,
                        how="left",
                    )

                    df_cruce["STOCK"] = df_cruce["STOCK"].fillna(0).astype(int)
                    df_con_stock = df_cruce[df_cruce["STOCK"] > 0].copy()

                    cant_existentes_con_stock = df_con_stock["Codigo_WMS"].nunique()

                    if cant_existentes_con_stock > 0:
                        df_salida_excel = pd.DataFrame()
                        df_salida_excel["CODIGO"] = df_con_stock["Codigo_WMS"]
                        df_salida_excel["DESCRIPCION"] = df_con_stock[des_col]
                        df_salida_excel["UBICACION"] = df_con_stock["UBICACION"]
                        df_salida_excel["PACKING"] = df_con_stock["Qty_Int"]
                        df_salida_excel["STOCK"] = df_con_stock["STOCK"]
                        df_salida_excel["TOTAL"] = (
                            df_salida_excel["PACKING"] + df_salida_excel["STOCK"]
                        )

                        output_consolidado = io.BytesIO()
                        with pd.ExcelWriter(
                            output_consolidado, engine="openpyxl"
                        ) as writer:
                            df_salida_excel.to_excel(
                                writer, index=False, sheet_name="Ubicaciones_Stock"
                            )

                        archivos_temp["UbicacionCodigosRecepcionado.xlsx"] = (
                            output_consolidado.getvalue(),
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )
                        informe_temp.append(
                            f"**E. UBICACIÓN DE CÓDIGOS RECEPCIONADOS:** "
                            f"**{cant_existentes_con_stock}** código(s) tienen "
                            f"stock/ubicación de los **{cant_existentes_maestro}** "
                            f"que ya existen en el Maestro → "
                            f"`UbicacionCodigosRecepcionado.xlsx`"
                        )
                    else:
                        informe_temp.append(
                            f"**E. UBICACIÓN DE CÓDIGOS RECEPCIONADOS:** 0 códigos "
                            f"tienen stock/ubicación de los "
                            f"**{cant_existentes_maestro}** que ya existen en el Maestro."
                        )
                else:
                    if bloqueo_wms:
                        informe_temp.append(
                            "⏸️ **E. UBICACIÓN DE CÓDIGOS RECEPCIONADOS:** Omitido por "
                            "**Descripción vacía en códigos nuevos**."
                        )
                    else:
                        informe_temp.append(
                            "ℹ️ **E. UBICACIÓN DE CÓDIGOS RECEPCIONADOS:** Omitido "
                            "(Requiere Reporte de Stock y Maestro)."
                        )

                # Guardar en Session State
                st.session_state.ac_archivos_para_descarga = archivos_temp
                st.session_state.ac_informe_html = informe_temp
                st.session_state.ac_procesado = True

            except Exception as e:
                st.error(f"Ocurrió un error inesperado al procesar los archivos: {str(e)}")
                st.session_state.ac_procesado = False

    # -------------------------------------------------------------
    # MOSTRAR RESULTADOS
    # -------------------------------------------------------------
    if st.session_state.ac_procesado:
        st.divider()
        st.success("✅ Procesamiento completado con éxito.")

        # SECCIÓN 2: INFORME
        st.markdown("### 2. Informe de Generación de Plantillas de Recepción")
        for linea in st.session_state.ac_informe_html:
            st.markdown(linea)

        st.divider()

        # SECCIÓN 3: DESCARGAS
        st.subheader("3. Descarga de Archivos")

        fecha_hoy = datetime.now().strftime("%Y%m%d")

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for nombre_archivo, (contenido_bytes, _) in st.session_state.ac_archivos_para_descarga.items():
                zip_file.writestr(nombre_archivo, contenido_bytes)

        st.download_button(
            label="📦 DESCARGAR PAQUETE COMPLETO (.ZIP)",
            data=zip_buffer.getvalue(),
            file_name=f"Recepcion_Procesada_{fecha_hoy}.zip",
            mime="application/zip",
            type="primary",
            key="ac_btn_zip_global",
        )

        st.write("")

        with st.expander("🔻 Detalle de descargas individuales"):
            for nombre_archivo, (contenido_bytes, mime_type) in st.session_state.ac_archivos_para_descarga.items():
                st.download_button(
                    label=f"📥 Descargar {nombre_archivo}",
                    data=contenido_bytes,
                    file_name=nombre_archivo,
                    mime=mime_type,
                    key=f"ac_down_{nombre_archivo}",
                )