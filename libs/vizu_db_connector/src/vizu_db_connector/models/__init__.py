"""Dynamic forwarder package.

This package makes imports like
`from vizu_db_connector.models.fonte_de_dados import FonteDeDados`
work by delegating them to the canonical `vizu_models` package located at
`libs/vizu_models/src` in the mono-repo. The implementation does not copy
model code; it only maps submodule imports to the corresponding
`vizu_models.<submodule>` module.

This keeps the code DRY and ensures the repo-local `vizu_models` is used
for tests and runtime.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path


def _ensure_local_vizu_models_on_path() -> None:
    # Walk up from this file to repo root and insert libs/vizu_models/src
    # into sys.path so imports resolve to the local package.
    base = Path(__file__).resolve()
    for parent in base.parents:
        candidate = parent / '..' / '..' / 'vizu_models' / 'src'
        candidate = candidate.resolve()
        if candidate.exists():
            sys.path.insert(0, str(candidate))
            return


_ensure_local_vizu_models_on_path()

try:
    import vizu_models  # type: ignore
except Exception as exc:  # pragma: no cover - surface import error in tests
    raise

# List of model submodules exposed by vizu_models that callers may import
# as `vizu_db_connector.models.<submodule>`.
_SUBMODULES = [
    'cliente_vizu',
    'configuracao_negocio',
    'credencial_servico_externo',
    'fonte_de_dados',
    'cliente_final',
    'conversa',
    'vizu_client_context',
]

# For each submodule, import vizu_models.<submodule> and register it in
# sys.modules under the vizu_db_connector.models.<submodule> name. This makes
# Python treat that module path as if it were a real submodule of this
# package, satisfying imports that expect package-style structure.
for _name in _SUBMODULES:
    src_name = f'vizu_models.{_name}'
    target_name = f'{__name__}.{_name}'
    try:
        _mod = importlib.import_module(src_name)
    except Exception:
        # Re-raise with context for easier debugging in CI/local runs.
        raise
    sys.modules[target_name] = _mod
    globals()[_name] = _mod

__all__ = _SUBMODULES

