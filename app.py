import sys
import os
import streamlit as st

# Asegurar que Python reconozca la carpeta modules sin importar la ruta de ejecución
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configuración global de la página
st.set_page_config(
    page_title="Proyecto Cargoflex",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Importación de los módulos desde la carpeta modules
from modules import ConciliacionStock, ArchivosCarcasas, ArchivosOtros, Expedicion


# =========================================================
# PANTALLA DE INICIO
# =========================================================
def mostrar_pantalla_inicio():
    st.title("Bienvenido al Portal de Operaciones Cargoflex")
    st.write("Selecciona un proceso desde el menú lateral para empezar a trabajar.")

    # Carga de la imagen local desde la carpeta assets
    ruta_imagen = "assets/LogoCargoflex.png"

    if os.path.exists(ruta_imagen):
        # Centramos el logo y lo reducimos (ya no ocupa todo el ancho)
        col_izq, col_centro, col_der = st.columns([2, 3, 2])
        with col_centro:
            st.image(ruta_imagen, width=320)
    else:
        st.warning("⚠️ No se encontró la imagen en 'assets/LogoCargoflex.png'")

    st.divider()
    st.subheader("📌 Módulos Disponibles")

    # --- Fila 1 ---
    col1, col2 = st.columns(2, gap="large")

    with col1:
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
            <h4 style="margin: 0 0 6px 0; color: inherit; font-size: 1rem;">📊 Conciliación de Stock</h4>
            <p style="margin: 4px 0; color: inherit;"><b>Propósito:</b> Auditar y cruzar la información de existencias entre los sistemas SGA y WMS.</p>
            <p style="margin: 4px 0; color: inherit;"><b>Función:</b> Compara el inventario registrado en SGA contra el de WMS para identificar rápidamente diferencias de stock (faltantes o sobrantes) y asegurar que ambos sistemas mantengan exactamente las mismas cantidades.</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
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
            <h4 style="margin: 0 0 6px 0; color: inherit; font-size: 1rem;">📱 Recepción: Carcasas</h4>
            <p style="margin: 4px 0; color: inherit;"><b>Propósito:</b> Procesar los archivos de ingreso para la recepción de carcasas.</p>
            <p style="margin: 4px 0; color: inherit;"><b>Función:</b> Valida la información del Packing List y genera automáticamente los archivos requeridos para registrar el ingreso masivo en los sistemas SGA y WMS.</p>
        </div>
        """, unsafe_allow_html=True)

    # Separación entre filas
    st.write("")

    # --- Fila 2 ---
    col3, col4 = st.columns(2, gap="large")

    with col3:
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
            <h4 style="margin: 0 0 6px 0; color: inherit; font-size: 1rem;">📦 Recepción: Otros</h4>
            <p style="margin: 4px 0; color: inherit;"><b>Propósito:</b> Procesar los archivos de ingreso para la recepción de otros clientes.</p>
            <p style="margin: 4px 0; color: inherit;"><b>Función:</b> Valida la información del Packing List y genera los archivos necesarios para registrar el ingreso masivo y la creación de nuevos códigos en el sistema WMS.</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown("""
        <div style="
            background-color: rgba(128, 128, 128, 0.12);
            border-left: 4px solid #FFA500;
            border-radius: 8px;
            padding: 12px 14px;
            height: 100%;
            color: inherit;
            font-size: 0.85rem;
            line-height: 1.3;
        ">
            <h4 style="margin: 0 0 6px 0; color: inherit; font-size: 1rem;">🚚 Expedición</h4>
            <p style="margin: 4px 0 6px 0; color: #FFA500; font-weight: bold; font-size: 0.85rem;">⏳ EN PROCESO...</p>
            <p style="margin: 4px 0; color: inherit;"><b>Propósito:</b> Validar el picking realizado por tienda antes del despacho.</p>
            <p style="margin: 4px 0; color: inherit;"><b>Función:</b> Permite subir el archivo de picking y verificar, tienda por tienda, que el picking se haya ejecutado correctamente.</p>
        </div>
        """, unsafe_allow_html=True)


# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================
def main():
    # Inicializar estado de navegación
    if "vista_actual" not in st.session_state:
        st.session_state.vista_actual = "inicio"

    # --- MENÚ LATERAL ---
    with st.sidebar:
        # Mostrar también el logo en pequeño en el menú si existe
        ruta_imagen = "assets/LogoCargoflex.png"
        if os.path.exists(ruta_imagen):
            st.image(ruta_imagen, use_container_width=True)

        st.title("☰ Menú Principal")
        st.caption("Cargoflex v1.0.0")
        st.divider()

        # Botón para regresar a Inicio
        if st.button("🏠 Inicio / Panel General", use_container_width=True):
            st.session_state.vista_actual = "inicio"

        # Botón para Conciliación
        opcion_conciliacion = st.button("📊 Conciliación de Stock", use_container_width=True)

        # Menú desplegable para Procesador de Archivos
        with st.expander("📥 Procesador de Archivos", expanded=True):
            opcion_carcasas = st.button("📱 Archivos Carcasas", use_container_width=True)
            opcion_otros = st.button("📦 Archivos Otros", use_container_width=True)

        # Botón para Expedición (En proceso)
        opcion_expedicion = st.button("🚚 Expedición (En proceso)", use_container_width=True)

        st.divider()

        # Tip con contraste adaptativo usando st.info nativo
        st.info("💡 **Tip:** Navega entre las opciones o regresa a la pantalla principal en cualquier momento.")

    # --- CONTROL DE NAVEGACIÓN ---
    if opcion_conciliacion:
        st.session_state.vista_actual = "conciliacion"
    elif opcion_carcasas:
        st.session_state.vista_actual = "carcasas"
    elif opcion_otros:
        st.session_state.vista_actual = "otros"
    elif opcion_expedicion:
        st.session_state.vista_actual = "expedicion"

    # --- RENDERING DE PÁGINAS ---
    if st.session_state.vista_actual == "inicio":
        mostrar_pantalla_inicio()
    elif st.session_state.vista_actual == "conciliacion":
        ConciliacionStock.render()
    elif st.session_state.vista_actual == "carcasas":
        ArchivosCarcasas.render()
    elif st.session_state.vista_actual == "otros":
        ArchivosOtros.render()
    elif st.session_state.vista_actual == "expedicion":
        Expedicion.render()


# =========================================================
# PUNTO DE ENTRADA
# =========================================================
if __name__ == "__main__":
    main()