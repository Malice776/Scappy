from parsel import Selector

SECTION_LABELS_FR = [
    "Généralités",
    "Fonctions",
    "Capacités entrepreneuriales",
    "Qualités",
    "Autorisations",
    "NACE",
    "Données financières",
    "Liens entre entités",
    "Liens externes",
]

def extract_dl_as_kv(sel: Selector) -> dict:
    data = {}
    for row in sel.xpath(".//dt|.//dd"):
        tag = row.root.tag
        text = " ".join(row.xpath(".//text()\n").getall()).strip()
        if tag == "dt":
            current = text.rstrip(":")
            data[current] = None
            last = current
        else:
            if data:
                data[last] = text
    return data