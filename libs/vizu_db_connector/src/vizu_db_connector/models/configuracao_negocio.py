from pathlib import Path
import sys

for parent in Path(__file__).resolve().parents:
    candidate = parent / '..' / '..' / 'vizu_models' / 'src'
    candidate = candidate.resolve()
    if candidate.exists():
        sys.path.insert(0, str(candidate))
        break

from vizu_models.configuracao_negocio import *  # noqa: F401,F403
