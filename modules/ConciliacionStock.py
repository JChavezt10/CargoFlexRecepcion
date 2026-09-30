import io
import pandas as pd
import streamlit as st


# =========================================================
# FUNCIONES AUXILIARES
# =========================================================
def procesar_datos(sga_file, wms_file):
    # --- PROCESAR SGA ---
    df_sga_raw = pd.read_excel(sga_file, sheet_name=0)

    header_idx = None
    for idx, row in df_sga_raw.iterrows():
        if "Código" in row.values or "Codigo" in row.values:
            header_idx = idx
            break

    if header_idx is not None:
        df_sga = df_sga_raw.iloc[header_idx + 1 :].copy()
        df_sga.columns = [
            str(col).strip() for col in df_sga_raw.iloc[header_idx].values
        ]
    else:
        df_sga = df_sga_raw.copy()

    # Formatear código SGA (quitar punto) y limpiar
    df_sga["CodCol"] = (
        df_sga["Código"]
        .astype(str)
        .str.replace(".", "", regex=False)
        .str.strip()
    )
    df_sga["Ubicado P2L"] = pd.to_numeric(
        df_sga["Ubicado P2L"], errors="coerce"
    ).fillna(0)

    sga_filt = df_sga[
        (df_sga["Ubicado P2L"] > 0)
        & (df_sga["CodCol"].notna())
        & (df_sga["CodCol"] != "nan")
    ]

    resumen_sga = (
        sga_filt.groupby("CodCol", as_index=False)
        .agg({"Descripción": "first", "Ubicado P2L": "sum"})
        .rename(columns={"Ubicado P2L": "SGA"})
    )

    # --- PROCESAR WMS CHECK ---
    df_wms = pd.read_excel(wms_file, sheet_name=0)
    df_wms["CodCol"] = df_wms["Código"].astype(str).str.strip()
    df_wms["Stock Físico"] = pd.to_numeric(
        df_wms["Stock Físico"], errors="coerce"
    ).fillna(0)
    df_wms["Ubicación"] = df_wms["Ubicación"].astype(str).str.strip()

    # Descartar 'C1-DSP-1' y ceros
    wms_filt = df_wms[
        (df_wms["Ubicación"] != "C1-DSP-1")
        & (df_wms["Stock Físico"] > 0)
        & (df_wms["CodCol"].notna())
        & (df_wms["CodCol"] != "nan")
    ]

    resumen_wms = (
        wms_filt.groupby("CodCol", as_index=False)
        .agg({"Descripción": "first", "Stock Físico": "sum"})
        .rename(columns={"Stock Físico": "WMS"})
    )

    # --- CONCILIACIÓN GENERAL ---
    todos_codigos = pd.DataFrame(
        {
            "CodCol": list(
                set(resumen_sga["CodCol"]).union(set(resumen_wms["CodCol"]))
            )
        }
    )

    resumen = todos_codigos.merge(
        resumen_sga, on="CodCol", how="left"
    ).merge(
        resumen_wms[["CodCol", "WMS", "Descripción"]],
        on="CodCol",
        how="left",
        suffixes=("_SGA", "_WMS"),
    )

    resumen["DESCRIPCIÓN"] = resumen["Descripción_SGA"].combine_first(
        resumen["Descripción_WMS"]
    )
    resumen["SGA"] = resumen["SGA"].fillna(0).astype(int)
    resumen["WMS"] = resumen["WMS"].fillna(0).astype(int)
    resumen["DIF(WMS-SGA)"] = resumen["WMS"] - resumen["SGA"]

    def definir_estado(dif):
        if dif == 0:
            return "OK"
        elif dif > 0:
            return "SOBRANTE EN WMS"
        else:
            return "SOBRANTE EN SGA"

    resumen["ESTADO"] = resumen["DIF(WMS-SGA)"].apply(definir_estado)

    resumen_cuadre = resumen[
        ["CodCol", "DESCRIPCIÓN", "SGA", "WMS", "DIF(WMS-SGA)", "ESTADO"]
    ].sort_values(by="CodCol")

    # --- DIFERENCIAS CON UBICACIÓN ---
    diferencias = resumen_cuadre[resumen_cuadre["ESTADO"] != "OK"].copy()

    wms_ubicaciones = (
        wms_filt.groupby("CodCol")["Ubicación"]
        .apply(lambda locs: ", ".join(sorted(locs.unique())))
        .reset_index()
    )

    diferencias_detalle = diferencias.merge(
        wms_ubicaciones, on="CodCol", how="left"
    )
    diferencias_detalle["Ubicación"] = diferencias_detalle["Ubicación"].fillna(
        "SIN UBICACIÓN EN WMS"
    )

    diferencias_detalle = diferencias_detalle[
        [
            "CodCol",
            "DESCRIPCIÓN",
            "Ubicación",
            "SGA",
            "WMS",
            "DIF(WMS-SGA)",
            "ESTADO",
        ]
    ]

    return resumen_cuadre, diferencias_detalle


def generar_excel(resumen_cuadre, diferencias_detalle, exp_resumen, exp_dif):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        workbook = writer.book

        ok_fmt = workbook.add_format(
            {"bg_color": "#C6EFCE", "font_color": "#006100"}
        )
        diff_fmt = workbook.add_format(
            {"bg_color": "#FFC7CE", "font_color": "#9C0006"}
        )

        if exp_dif:
            diferencias_detalle.to_excel(
                writer, sheet_name="Diferencias_Ubicacion", index=False
            )
            ws = writer.sheets["Diferencias_Ubicacion"]
            ws.conditional_format(
                "G2:G10000",
                {
                    "type": "cell",
                    "criteria": "not equal to",
                    "value": '"OK"',
                    "format": diff_fmt,
                },
            )

        if exp_resumen:
            resumen_cuadre.to_excel(
                writer, sheet_name="Resultado General", index=False
            )
            ws = writer.sheets["Resultado General"]
            ws.conditional_format(
                "F2:F10000",
                {
                    "type": "cell",
                    "criteria": "equal to",
                    "value": '"OK"',
                    "format": ok_fmt,
                },
            )
            ws.conditional_format(
                "F2:F10000",
                {
                    "type": "cell",
                    "criteria": "not equal to",
                    "value": '"OK"',
                    "format": diff_fmt,
                },
            )

    buffer.seek(0)
    return buffer


# =========================================================
# RENDER (punto de entrada del módulo)
# =========================================================
def render():
    st.header("📦 Conciliación de Stock (SGA vs WMS Check)")
    st.markdown(
        "Sube los archivos de stock descargados de SGA y WMS Check para procesar."
    )

    # 1. Carga de Archivos
    col_up1, col_up2 = st.columns(2)

    with col_up1:
        sga_file = st.file_uploader(
            "Cargar Archivo de SGA (.xlsx)",
            type=["xlsx", "xls"],
            key="sga_file_conciliacion",
        )

    with col_up2:
        wms_file = st.file_uploader(
            "Cargar Archivo de WMS Check (.xlsx)",
            type=["xlsx", "xls"],
            key="wms_file_conciliacion",
        )

    # Botón para procesar
    procesar_btn = st.button(
        "🚀 Procesar y Conciliar Stock", type="primary", key="btn_conciliacion"
    )

    # Guardar estado de procesamiento
    if sga_file and wms_file and procesar_btn:
        with st.spinner("Procesando y cruzando información..."):
            resumen_cuadre, diferencias_detalle = procesar_datos(
                sga_file, wms_file
            )
            st.session_state["resumen_cuadre"] = resumen_cuadre
            st.session_state["diferencias_detalle"] = diferencias_detalle

    # Mostrar resultados
    if "resumen_cuadre" in st.session_state:
        resumen_cuadre = st.session_state["resumen_cuadre"]
        diferencias_detalle = st.session_state["diferencias_detalle"]

        st.success("¡Conciliación completada con éxito!")

        # Cálculos para métricas
        cant_codigos = len(resumen_cuadre)
        sum_sga = resumen_cuadre["SGA"].sum()
        sum_wms = resumen_cuadre["WMS"].sum()

        cant_dif = len(diferencias_detalle)
        suma_dif = diferencias_detalle["DIF(WMS-SGA)"].sum()

        # Métricas adaptadas y centradas
        m1, m2, m3, m4 = st.columns(4)

        with m1:
            st.metric("CANTIDAD DE CÓDIGOS", f"{cant_codigos:,}")

        with m2:
            if sum_sga == sum_wms:
                st.metric("SUMA TOTAL DE CÓDIGOS", f"{sum_wms:,}")
            else:
                st.markdown(
                    f"""SUMA TOTAL DE CÓDIGOS

WMS: {sum_wms:,}


SGA: {sum_sga:,}
""",
                    unsafe_allow_html=True,
                )

        with m3:
            st.metric("CANTIDAD DE CÓDIGOS CON DIFERENCIA", f"{cant_dif:,}")

        with m4:
            st.metric("SUMA DE CÓDIGOS CON DIFERENCIA", f"{suma_dif:,}")

        st.divider()

        # Configuración de alineación de columnas para las tablas
        config_columnas = {
            "SGA": st.column_config.NumberColumn("SGA", alignment="center"),
            "WMS": st.column_config.NumberColumn("WMS", alignment="center"),
            "DIF(WMS-SGA)": st.column_config.NumberColumn(
                "DIF(WMS-SGA)", alignment="center"
            ),
            "ESTADO": st.column_config.TextColumn(
                "ESTADO", alignment="center"
            ),
        }

        # Sección de Exportación
        st.subheader("📥 Exportar Resultados a Excel")
        col_exp1, col_exp2, col_exp3 = st.columns([1, 1, 2])

        with col_exp1:
            exp_dif = st.checkbox(
                "Incluir Hoja de Diferencias",
                value=True,
                key="exp_dif_conciliacion",
            )
        with col_exp2:
            exp_resumen = st.checkbox(
                "Incluir Resultado General",
                value=True,
                key="exp_resumen_conciliacion",
            )

        if exp_dif or exp_resumen:
            excel_bytes = generar_excel(
                resumen_cuadre, diferencias_detalle, exp_resumen, exp_dif
            )
            st.download_button(
                label="📥 Descargar Excel Seleccionado",
                data=excel_bytes,
                file_name="Conciliacion_Stock.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                key="dl_conciliacion",
            )
        else:
            st.warning("Selecciona al menos una hoja para exportar.")

        st.divider()

        # Visualización de Tablas
        tab1, tab2 = st.tabs(
            ["⚠️ Diferencias (Con Ubicación)", "📊 Resultado General"]
        )

        with tab1:
            col_title, col_filter = st.columns([2, 1])

            with col_title:
                st.markdown("**Diferencias con Ubicación Física en WMS Check:**")

            with col_filter:
                opciones_estado = [
                    e
                    for e in diferencias_detalle["ESTADO"].unique()
                    if e != "OK"
                ]
                if not opciones_estado:
                    opciones_estado = ["SOBRANTE EN WMS", "SOBRANTE EN SGA"]

                filtro_estado = st.multiselect(
                    "Filtrar Estado:",
                    options=opciones_estado,
                    default=opciones_estado,
                    key="filtro_estado_dif",
                )

            df_dif_mostrar = diferencias_detalle[
                diferencias_detalle["ESTADO"].isin(filtro_estado)
            ]

            if len(df_dif_mostrar) > 0:
                st.dataframe(
                    df_dif_mostrar,
                    use_container_width=True,
                    hide_index=True,
                    column_config=config_columnas,
                )
            else:
                if len(diferencias_detalle) == 0:
                    st.info(
                        "¡Excelente! No existen diferencias de stock entre ambos sistemas."
                    )
                else:
                    st.info(
                        "No hay registros que coincidan con el filtro seleccionado."
                    )

        with tab2:
            st.markdown("**Resultado General del Cuadre de Stock:**")
            st.dataframe(
                resumen_cuadre,
                use_container_width=True,
                hide_index=True,
                column_config=config_columnas,
            )

    elif not (sga_file and wms_file):
        st.info("👈 Por favor, carga los dos archivos arriba para comenzar.")