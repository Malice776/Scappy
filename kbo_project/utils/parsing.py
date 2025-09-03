import re
from datetime import datetime
from typing import Optional

NUM_RE = re.compile(r"\D+")

def clean_num(n: str) -> str:
    return NUM_RE.sub("", n or "")

def parse_date(s: str) -> Optional[str]:
    s = (s or "").strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    return None