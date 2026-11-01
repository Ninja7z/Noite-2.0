from __future__ import annotations

import os
from pathlib import Path


def search_workspace(root: Path, query: str, limit: int = 20) -> list[str]:
    """Search filenames only, within one configured root and without following symlinks."""
    if not query.strip():
        return []
    allowed_root = root.expanduser().resolve()
    if not allowed_root.exists() or not allowed_root.is_dir():
        return []
    max_results = max(1, min(limit, 50))
    matches: list[str] = []
    visited = 0
    needle = query.strip().casefold()

    for current, directories, filenames in os.walk(allowed_root, followlinks=False):
        directories[:] = [
            name
            for name in directories
            if not name.startswith(".") and not (Path(current) / name).is_symlink()
        ]
        for name in filenames:
            visited += 1
            candidate = Path(current) / name
            try:
                candidate.resolve().relative_to(allowed_root)
            except (OSError, ValueError):
                continue
            if needle in name.casefold():
                matches.append(str(candidate.relative_to(allowed_root)))
                if len(matches) >= max_results:
                    return matches
            if visited >= 5000:
                return matches
    return matches
