import csv
import scrapy
from urllib.parse import urlencode
from kbo_project.utils.parsing import clean_num
from kbo_project.utils.kbo_sections import extract_dl_as_kv

BASE = (
    "https://kbopub.economie.fgov.be/kbopub/toonondernemingps.html"
)

class KboSpider(scrapy.Spider):
    name = "kbo_spider"
    custom_settings = {
        "ROBOTSTXT_OBEY": True,
    }

    def start_requests(self):
        with open("entreprises.csv", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                num = clean_num(row.get("ondernemingsnummer", ""))
                if not num:
                    continue
                params = {"ondernemingsnummer": num}
                url = f"{BASE}?{urlencode(params)}"
                yield scrapy.Request(
                    url,
                    headers={"Accept-Language": "fr"},
                    callback=self.parse_company,
                    cb_kwargs={"num": num},
                )

    def parse_company(self, response, num):
        # Extraction souple par sections (titres + contenus adjacents)
        data = {
            "Généralités": {},
            "Fonctions": {},
            "Capacités entrepreneuriales": {},
            "Qualités": {},
            "Autorisations": {},
            "NACE": {},
            "Données financières": {},
            "Liens entre entités": {},
            "Liens externes": {},
        }

        # Exemple de structure KBO : des blocs <section>/<h2>… Selon les variations, on capture par h2/h3
        for section in response.css("section, div.section, div.panel, article"):
            title = " ".join(section.css("h1,h2,h3,h4::text").getall()).strip()
            if not title:
                continue
            lower = title.lower()
            key = None
            if "général" in lower:
                key = "Généralités"
            elif "fonction" in lower:
                key = "Fonctions"
            elif "capacit" in lower and "entrepr" in lower:
                key = "Capacités entrepreneuriales"
            elif "qualit" in lower:
                key = "Qualités"
            elif "autorisation" in lower:
                key = "Autorisations"
            elif "nace" in lower:
                key = "NACE"
            elif "financi" in lower:
                key = "Données financières"
            elif "liens" in lower and "entit" in lower:
                key = "Liens entre entités"
            elif "liens externes" in lower or ("liens" in lower and "extern" in lower):
                key = "Liens externes"

            if key:
                # Essayer d’extraire les paires clef/valeur de listes définition (<dl>)
                dl = section.css("dl")
                if dl:
                    data[key] = extract_dl_as_kv(dl[0])
                else:
                    # fallback : texte brut de la section
                    text = " ".join(section.css("::text").getall()).strip()
                    data[key] = {"texte": text}

        yield {
            "ondernemingsnummer": num,
            "source": "kbo",
            "kbo": data,
        }