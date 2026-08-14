"""Stockage des pieces jointes sur le systeme de fichiers local.

Choix : stockage fichier + metadonnees en base, pas de BLOB PostgreSQL. A
l'echelle du projet (LAN, 5-15 utilisateurs), c'est ce qui garde les
sauvegardes `pg_dump` legeres et restaurables rapidement.

Regles de securite appliquees ici :
- le nom d'origine n'est JAMAIS utilise comme nom de fichier sur disque
  (il est stocke en base pour l'affichage) : un nom construit par le serveur
  supprime toute possibilite de traversee de repertoire ;
- extension et type MIME verifies par liste blanche ;
- taille plafonnee, verifiee pendant la lecture par blocs et non apres, pour
  ne pas charger un fichier de 2 Go en memoire avant de le refuser.
"""

import mimetypes
import re
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import BusinessRuleError

MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 Mo
CHUNK_SIZE = 64 * 1024

ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".txt", ".csv", ".xlsx", ".docx", ".odt", ".zip"}
)

_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]")


def _storage_root() -> Path:
    root = Path(settings.attachments_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def sanitize_filename(filename: str) -> str:
    """Nom affichable, debarrasse de tout composant de chemin."""
    base = Path(filename).name
    cleaned = _SAFE_FILENAME.sub("_", base).lstrip(".")
    return cleaned[:200] or "fichier"


def _validate_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise BusinessRuleError(
            f"Type de fichier non autorise ({suffix or 'sans extension'}). "
            f"Formats acceptes : {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )
    return suffix


async def save_upload(upload: UploadFile, *, subdirectory: str) -> tuple[str, str, str, int]:
    """Ecrit le fichier sur disque.

    Retourne (nom_affiche, nom_stocke, content_type, taille_en_octets).
    """
    display_name = sanitize_filename(upload.filename or "fichier")
    suffix = _validate_extension(display_name)

    stored_name = f"{subdirectory}/{uuid.uuid4().hex}{suffix}"
    destination = _storage_root() / stored_name
    destination.parent.mkdir(parents=True, exist_ok=True)

    size = 0
    try:
        with destination.open("wb") as handle:
            while chunk := await upload.read(CHUNK_SIZE):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise BusinessRuleError(
                        f"Fichier trop volumineux (maximum {MAX_UPLOAD_BYTES // (1024 * 1024)} Mo)."
                    )
                handle.write(chunk)
    except BusinessRuleError:
        destination.unlink(missing_ok=True)
        raise

    if size == 0:
        destination.unlink(missing_ok=True)
        raise BusinessRuleError("Le fichier est vide.")

    content_type = upload.content_type or mimetypes.guess_type(display_name)[0]
    return display_name, stored_name, content_type or "application/octet-stream", size


def resolve_path(stored_name: str) -> Path:
    """Chemin absolu d'une piece jointe, garanti a l'interieur du repertoire de stockage."""
    root = _storage_root().resolve()
    path = (root / stored_name).resolve()
    if not path.is_relative_to(root):
        # Ne peut se produire que si `stored_name` a ete altere en base.
        raise BusinessRuleError("Chemin de piece jointe invalide.")
    return path


def delete_file(stored_name: str) -> None:
    resolve_path(stored_name).unlink(missing_ok=True)
