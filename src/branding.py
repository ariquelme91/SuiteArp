"""Logo de la app (Rentanalytics by ARP), compartido entre login y encabezado."""

import base64
import os

import streamlit as st

LOGO_PATH = os.path.join("assets", "logos", "rentanalyticsVF.png")
LOGO_HORIZONTAL_PATH = os.path.join("assets", "logos", "RentanaliticsH.png")


@st.cache_data
def logo_base64(path: str = LOGO_PATH) -> str:
    """Codifica un logo una sola vez (se cachea entre reruns, por ruta)."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()
