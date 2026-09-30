import streamlit as st


def render():
    st.title("🚚 Expedición")
    st.warning("⚠️ **Módulo en desarrollo.**")
    st.write(
        "Este módulo permitirá validar el picking por tienda. "
        "Se subirá el archivo de picking y se verificará, tienda por tienda, "
        "que el picking se haya realizado correctamente antes del despacho."
    )
    st.info("📌 Disponible próximamente.")