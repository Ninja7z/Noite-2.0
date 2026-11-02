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
        visible_directories = []
        for name in directories:
            visited += 1
            candidate_dir = Path(current) / name
            if (
                visited >= 5000
                or name.startswith(".")
                or candidate_dir.is_symlink()
                or (hasattr(candidate_dir, "is_junction") and candidate_dir.is_junction())
            ):
                continue
            visible_directories.append(name)
        directories[:] = visible_directories
        for name in filenames:
            visited += 1
            if visited > 5000:
                return matches
            if name.startswith("."):
                continue
            candidate = Path(current) / name
            if candidate.is_symlink() or (
                hasattr(candidate, "is_junction") and candidate.is_junction()
            ):
                continue
            if needle in name.casefold():
                matches.append(str(candidate.relative_to(allowed_root)))
                if len(matches) >= max_results:
                    return matches
    return matches
