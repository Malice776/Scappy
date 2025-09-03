from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

@dataclass
class EntrepriseItem:
    ondernemingsnummer: str
    source: str
    kbo: Dict[str, Any] | None = None
    ejustice_publications: List[Dict[str, Any]] = field(default_factory=list)
    nbb_depots: List[Dict[str, Any]] = field(default_factory=list)