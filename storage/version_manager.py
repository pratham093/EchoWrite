"""
Version Manager — Persists every content transformation as a timestamped
JSON record with full original + rewritten text and metadata.
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import settings


class VersionManager:
    """File-based version store — each version is a self-contained JSON file."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = Path(storage_dir) if storage_dir else settings.CONTENT_VERSIONS_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _version_path(self, version_id: str) -> Path:
        return self.storage_dir / f"{version_id}.json"

    @staticmethod
    def _generate_version_id(url: str) -> str:
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        digest = hashlib.sha256(f"{url}{stamp}".encode()).hexdigest()[:10]
        return f"{stamp}_{digest}"

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def save_version(
        self,
        url: str,
        original: str,
        rewritten: str,
        metadata: Dict[str, Any] | None = None,
    ) -> str:
        """Persist a new version; return its version_id."""
        vid = self._generate_version_id(url)
        record = {
            "version_id": vid,
            "url": url,
            "original": original,
            "rewritten": rewritten,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
        }
        with self._version_path(vid).open("w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)
        return vid

    def get_version(self, version_id: str) -> Optional[Dict[str, Any]]:
        path = self._version_path(version_id)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return lightweight summaries of stored versions (newest first)."""
        records: list[dict] = []
        for path in self.storage_dir.glob("*.json"):
            try:
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                meta = data.get("metadata", {})
                records.append(
                    {
                        "version_id": data.get("version_id"),
                        "url": data.get("url"),
                        "created_at": data.get("created_at"),
                        "style": meta.get("style"),
                        "iterations": meta.get("iterations"),
                        "quality_score": meta.get("quality_score"),
                    }
                )
            except (json.JSONDecodeError, OSError):
                continue
        records.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        return records[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        history = self.get_history(limit=10_000)
        unique_urls = {item["url"] for item in history if item.get("url")}
        return {"total_versions": len(history), "unique_urls": len(unique_urls)}
