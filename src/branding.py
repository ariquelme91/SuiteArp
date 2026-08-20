"""Logo de la app (Rentanalytics by ARP), compartido entre login y encabezado."""

import base64
import os

import streamlit as st

LOGO_PATH = os.path.join("assets", "logos", "rentanalyticsVF.png")


@st.cache_data
def logo_base64() -> str:
    """Codifica el logo una sola vez (se cachea entre reruns)."""
    with open(LOGO_PATH, "rb") as f:
        return base64.b64encode(f.read()).decode()
