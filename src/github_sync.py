"""Sincronización de archivos de configuración con el repo de GitHub.

Streamlit Community Cloud reconstruye el contenedor clonando el repo desde
git cada vez que la app se reinicia (incluyendo cuando "despierta" tras estar
inactiva, no solo en un Reboot manual). Cualquier escritura hecha en vivo
(base de datos, archivos) que no quede además comiteada en git se pierde en
ese momento. Este módulo comitea archivos JSON pequeños directamente vía la
API de contenidos de GitHub para que sobrevivan a un reinicio real.

Requiere en `.streamlit/secrets.toml` (local) o en los Secrets de la app en
Streamlit Cloud (producción):

    [github]
    token = "ghp_xxx"            # Personal Access Token con permiso de
                                  # escritura de contenidos sobre el repo
    repo = "usuario/repositorio"
    branch = "main"              # opcional, default "main"
"""

import base64
import json
import logging
from typing import Optional

import requests
import streamlit as st

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


def _get_config() -> Optional[dict]:
    try:
        cfg = st.secrets["github"]
        return {
            "token": cfg["token"],
            "repo": cfg["repo"],
            "branch": cfg.get("branch", "main"),
        }
    except Exception:
        return None


def is_configured() -> bool:
    """True si existen las credenciales de GitHub en los secrets."""
    return _get_config() is not None


def commit_json_file(path_in_repo: str, data: dict, commit_message: str) -> tuple:
    """Comitea un diccionario como JSON en `path_in_repo` dentro del repo.

    Returns:
        Tupla (ok, detalle). `ok` es True si el commit fue exitoso. `detalle`
        es un mensaje legible con la causa cuando `ok` es False (útil para
        mostrarlo en la UI sin tener que ir a revisar logs).
    """
    cfg = _get_config()
    if not cfg:
        return False, "Sin credenciales de GitHub en los secrets (falta la sección [github])."

    headers = {
        "Authorization": f"Bearer {cfg['token']}",
        "Accept": "application/vnd.github+json",
    }
    url = f"{GITHUB_API}/repos/{cfg['repo']}/contents/{path_in_repo}"

    try:
        get_resp = requests.get(url, headers=headers, params={"ref": cfg["branch"]}, timeout=10)
        if get_resp.status_code not in (200, 404):
            detalle = f"GET falló ({get_resp.status_code}): {_extraer_mensaje(get_resp)}"
            logger.error("Error leyendo %s de GitHub: %s", path_in_repo, detalle)
            return False, detalle
        sha = get_resp.json().get("sha") if get_resp.status_code == 200 else None

        content_str = json.dumps(data, indent=2, ensure_ascii=False)
        payload = {
            "message": commit_message,
            "content": base64.b64encode(content_str.encode("utf-8")).decode("utf-8"),
            "branch": cfg["branch"],
        }
        if sha:
            payload["sha"] = sha

        put_resp = requests.put(url, headers=headers, json=payload, timeout=10)
        if put_resp.status_code in (200, 201):
            return True, ""

        detalle = f"PUT falló ({put_resp.status_code}): {_extraer_mensaje(put_resp)}"
        logger.error("Error comiteando %s a GitHub: %s", path_in_repo, detalle)
        return False, detalle
    except Exception as e:
        logger.error("Error comiteando %s a GitHub: %s", path_in_repo, e)
        return False, str(e)


def _extraer_mensaje(resp: "requests.Response") -> str:
    try:
        return resp.json().get("message", resp.text[:200])
    except Exception:
        return resp.text[:200]
