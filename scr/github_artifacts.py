import os
import io
import time
import zipfile
from pathlib import Path
from typing import Optional, List, Dict

import requests

# Configurações básicas – ajuste se quiser parametrizar via secrets/env do Streamlit
GITHUB_OWNER = os.environ.get("GH_OWNER", "niltonsainz")
GITHUB_REPO = os.environ.get("GH_REPO", "clipping-legislativo-faciap")
ARTIFACT_PREFIX = os.environ.get("ARTIFACT_PREFIX", "clipping-database-")
GITHUB_TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

API_BASE = "https://api.github.com"
API_VERSION = "2022-11-28"

def _new_session() -> requests.Session:
    s = requests.Session()
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    s.headers.update(headers)
    return s

def _list_artifacts(session: requests.Session, per_page: int = 50) -> List[Dict]:
    """Lista artifacts do repositório (mais recentes primeiro pelo lado do cliente)."""
    url = f"{API_BASE}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/artifacts?per_page={per_page}"
    r = session.get(url, timeout=30)
    r.raise_for_status()
    return r.json().get("artifacts", [])

def _pick_latest_db_artifact(artifacts: List[Dict]) -> Optional[Dict]:
    """Escolhe o artifact mais novo que comece com o prefixo e não esteja expirado."""
    candidates = [
        a for a in artifacts
        if a.get("name", "").startswith(ARTIFACT_PREFIX) and not a.get("expired")
    ]
    if not candidates:
        return None
    # Ordena por created_at desc (string ISO ordena bem)
    candidates.sort(key=lambda a: a.get("created_at", ""), reverse=True)
    return candidates[0]

def _download_artifact_zip(session: requests.Session, artifact: Dict) -> bytes:
    """Baixa o ZIP do artifact."""
    url = artifact["archive_download_url"]
    r = session.get(url, timeout=120)
    r.raise_for_status()
    return r.content

def download_latest_db_artifact(dest_path: str = "data/clipping_faciap.db",
                                max_age_seconds: int = 600) -> str:
    """
    Baixa o último artifact de DB do repositório e grava como dest_path.
    - Só baixa se:
        - dest_path não existir, ou
        - mtime de dest_path for mais antigo que max_age_seconds.
    - Requer GH_TOKEN em secrets/ambiente no Streamlit Cloud.
    - Em caso de erro, retorna dest_path sem alterar (fallback silencioso).
    """
    try:
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        if dest.exists():
            age = time.time() - dest.stat().st_mtime
            if age < max_age_seconds:
                return dest_path

        session = _new_session()
        artifacts = _list_artifacts(session, per_page=50)
        latest = _pick_latest_db_artifact(artifacts)
        if not latest:
            # Sem artifact compatível – deixa como está
            return dest_path

        zip_bytes = _download_artifact_zip(session, latest)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            # Procura o primeiro arquivo .db
            member = next((n for n in zf.namelist() if n.lower().endswith(".db")), None)
            if not member:
                return dest_path
            # Extrai diretamente para dest_path
            with zf.open(member) as src, open(dest, "wb") as dst:
                dst.write(src.read())

        return dest_path
    except Exception:
        # Fallback silencioso – não quebra a app se a API falhar
        return dest_path
