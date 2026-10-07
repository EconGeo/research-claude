import sys
from pathlib import Path
_DT = Path(__file__).resolve().parents[1] / "skills/ztp-data-tag/scripts"
if str(_DT) not in sys.path:
    sys.path.insert(0, str(_DT))
