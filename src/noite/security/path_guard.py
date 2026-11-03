from __future__ import annotations

from pathlib import Path


def resolve_allowed_path(root: Path, candidate: Path, *, must_exist: bool = True) -> Path:
    """Resolve a path under root and reject traversal, symlinks and Windows junctions."""
    allowed_root = Path(root).resolve(strict=True)
    raw = Path(candidate)
    target = raw if raw.is_absolute() else allowed_root / raw
    try:
        resolved = target.resolve(strict=must_exist)
        if not resolved.is_relative_to(allowed_root):
            raise ValueError("O caminho solicitado está fora do diretório autorizado.")
    except (OSError, RuntimeError) as exc:
        raise ValueError("Não foi possível validar o caminho solicitado.") from exc

    current = allowed_root
    try:
        relative = target.relative_to(allowed_root) if target.is_absolute() else raw
    except ValueError as exc:
        raise ValueError("O caminho solicitado está fora do diretório autorizado.") from exc
    for part in relative.parts:
        if part in {"", ".", ".."}:
            if part == "..":
                raise ValueError("Travessia de diretório não é permitida.")
            continue
        current = current / part
        is_junction = getattr(current, "is_junction", lambda: False)()
        if current.is_symlink() or is_junction:
            raise ValueError("Links simbólicos e junctions não são permitidos.")
    return resolved
