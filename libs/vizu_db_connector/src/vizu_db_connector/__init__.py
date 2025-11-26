from .database import get_db_session
from .crud import BaseCRUD, get_cliente_vizu_by_api_key

# Ensure the local `libs/vizu_models/src` directory is on sys.path so imports
# of the `vizu_models` package resolve to the local library in this mono-repo
# (avoid requiring an installed package or duplicating model code).
import sys
from pathlib import Path

def _add_local_vizu_models_to_path():
	base = Path(__file__).resolve()
	# Walk parents and find a path that contains `libs/vizu_models/src`.
	for parent in base.parents:
		candidate = parent / 'libs' / 'vizu_models' / 'src'
		if candidate.exists():
			sys.path.insert(0, str(candidate))
			return True
	return False

_add_local_vizu_models_to_path()

# Re-export the shared `vizu_models` package so callers can access model
# symbols via `vizu_db_connector.models` or import model names directly from
# `vizu_db_connector` (legacy compatibility).
try:
	import vizu_models as models  # type: ignore
except Exception:
	# Let import errors surface when tests run; keep import-time tolerant to
	# avoid failing test discovery prematurely in partial environments.
	models = None  # type: ignore

__all__ = [
	"get_db_session",
	"BaseCRUD",
	"get_cliente_vizu_by_api_key",
	"models",
]
