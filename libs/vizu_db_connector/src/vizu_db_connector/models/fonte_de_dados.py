from pathlib import Path
import sys

# Ensure the local vizu_models package (libs/vizu_models/src) is available
for parent in Path(__file__).resolve().parents:
    candidate = parent / '..' / '..' / 'vizu_models' / 'src'
    candidate = candidate.resolve()
    if candidate.exists():
        sys.path.insert(0, str(candidate))
        break

from vizu_models.fonte_de_dados import *  # noqa: F401,F403
