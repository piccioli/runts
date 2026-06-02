"""Async downloader for RUNTS allegati."""

import hashlib
import logging
import re
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[àáâã]", "a", text)
    text = re.sub(r"[èéêë]", "e", text)
    text = re.sub(r"[ìíîï]", "i", text)
    text = re.sub(r"[òóôõ]", "o", text)
    text = re.sub(r"[ùúûü]", "u", text)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")[:50]


def _build_filename(
    codice_pratica: str, anno, documento: str, used_names: set[str]
) -> str:
    parts = [codice_pratica]
    if anno:
        parts.append(str(anno))
    parts.append(_slugify(documento))
    base = "_".join(parts) + ".pdf"

    if base not in used_names:
        used_names.add(base)
        return base

    i = 2
    while True:
        candidate = "_".join(parts) + f"_{i}.pdf"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
        i += 1


async def download_attachments(
    client: httpx.AsyncClient,
    id_runts: str,
    attachments: list[dict],
    dest_dir: Path,
    max_size_mb: int = 50,
) -> list[dict]:
    """Download allegati, return enriched list with filename/path/hash/size/skip_reason."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    max_bytes = max_size_mb * 1024 * 1024
    used_names: set[str] = set()
    results = []

    for att in attachments:
        url = att.get("url")
        if not url:
            results.append(
                {**att, "skip_reason": "no_url", "filename": None, "path": None}
            )
            continue

        filename = _build_filename(
            att["codice_pratica"], att.get("anno"), att["documento"], used_names
        )
        dest_path = dest_dir / filename

        try:
            # HEAD request to check size first
            try:
                head = await client.head(url, follow_redirects=True)
                content_length = int(head.headers.get("content-length", 0))
                if content_length and content_length > max_bytes:
                    logger.warning(
                        "Allegato troppo grande (%d MB), skip: %s",
                        content_length // (1024 * 1024),
                        filename,
                    )
                    results.append(
                        {
                            **att,
                            "skip_reason": "size_exceeded",
                            "filename": filename,
                            "path": None,
                            "size": content_length,
                        }
                    )
                    continue
            except Exception:
                pass  # proceed without size check if HEAD fails

            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()

            content = response.content
            if len(content) > max_bytes:
                logger.warning(
                    "Allegato troppo grande (%d MB), skip: %s",
                    len(content) // (1024 * 1024),
                    filename,
                )
                results.append(
                    {
                        **att,
                        "skip_reason": "size_exceeded",
                        "filename": filename,
                        "path": None,
                        "size": len(content),
                    }
                )
                continue

            sha256 = hashlib.sha256(content).hexdigest()
            dest_path.write_bytes(content)

            mime = (
                response.headers.get("content-type", "application/pdf")
                .split(";")[0]
                .strip()
            )
            rel_path = f"attachments/{id_runts}/{filename}"

            results.append(
                {
                    **att,
                    "filename": filename,
                    "path": rel_path,
                    "mime": mime,
                    "size": len(content),
                    "hash_sha256": sha256,
                    "skip_reason": None,
                }
            )
            logger.debug("Scaricato %s (%d KB)", filename, len(content) // 1024)

        except Exception as exc:
            logger.warning("Download fallito per %s: %s", filename, exc)
            results.append(
                {
                    **att,
                    "skip_reason": f"error: {exc}",
                    "filename": filename,
                    "path": None,
                }
            )

    return results
