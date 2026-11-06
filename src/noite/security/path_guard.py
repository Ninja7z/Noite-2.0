from __future__ import annotations

from pathlib import Path


def resolve_allowed_path(root: Path, candidate: Path, *, must_exist: bool = True) -> Path:
    """Resolve a path under root and reject traversal, symlinks and Windows junctions."""
    allowed_root = Path(root).resolve(strict=True)
    raw = Path(candidate)
    target = raw if raw.is_absolute() else allowed_root / raw
    try:
        relative = target.relative_to(allowed_root)
    except ValueError as exc:
        raise ValueError("O caminho solicitado está fora do diretório autorizado.") from exc

    # Validate every component before following anything: resolve() would otherwise
    # silently cross a symlink/junction and report only a generic "outside root" error.
    current = allowed_root
    for part in relative.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            raise ValueError("Travessia de diretório não é permitida.")
        current = current / part
        is_junction = getattr(current, "is_junction", lambda: False)()
        if current.is_symlink() or is_junction:
            raise ValueError("Links simbólicos e junctions não são permitidos.")

    try:
        resolved_no_follow = target.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise ValueError("Não foi possível validar o caminho solicitado.") from exc
    if not resolved_no_follow.is_relative_to(allowed_root):
        raise ValueError("O caminho solicitado está fora do diretório autorizado.")

    try:
        resolved = target.resolve(strict=must_exist)
    except (OSError, RuntimeError) as exc:
        raise ValueError("Não foi possível validar o caminho solicitado.") from exc
    if not resolved.is_relative_to(allowed_root):
        raise ValueError("O caminho solicitado está fora do diretório autorizado.")
    return resolved