import csv
import scrapy
from urllib.parse import urlencode
from kbo_project.utils.parsing import clean_num, parse_date

SEARCH_BASE = "https://www.ejustice.just.fgov.be/cgi_t/ts.pl"

class EJusticeSpider(scrapy.Spider):
    name = "ejustice_spider"

    def start_requests(self):
        with open("entreprises.csv", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                num = clean_num(row.get("ondernemingsnummer", ""))
                if not num:
                    continue
                params = {"language": "fr", "btw": num, "fromtab": 1}
                url = f"{SEARCH_BASE}?{urlencode(params)}"
                yield scrapy.Request(url, callback=self.parse_list, cb_kwargs={"num": num})

    def parse_list(self, response, num):
        for row in response.css("table tr"):
            link = row.css("a::attr(href)").get()
            if not link:
                continue
            title = row.css("a::text").get(default="").strip()
            date_txt = "".join(row.css("td::text").getall()).strip()
            yield response.follow(link, callback=self.parse_detail, cb_kwargs={
                "num": num,
                "title_hint": title,
                "date_hint": date_txt,
            })

    def parse_detail(self, response, num, title_hint, date_hint):
        def pick(selector):
            return " ".join(response.css(selector).xpath(".//text()\n").getall()).strip() or None

        numero_pub = pick("#pubnr, .pubnr, tr:contains('Numéro') td:last-child")
        titre = pick("h1, h2, .title, .titre") or title_hint
        code = pick(".code, tr:contains('Code') td:last-child")
        adresse = pick("tr:contains('Adresse') td:last-child")
        type_pub = pick("tr:contains('Type') td:last-child")
        date_pub = parse_date(pick("tr:contains('Date') td:last-child") or date_hint)
        reference = pick("tr:contains('Référence') td:last-child")
        img_url = response.css("img::attr(src)").get()

        pub = {
            "numero": numero_pub,
            "titre": titre,
            "code": code,
            "adresse": adresse,
            "type": type_pub,
            "date": date_pub,
            "reference": reference,
            "image_url": response.urljoin(img_url) if img_url else None,
            "detail_url": response.url,
        }

        yield {
            "ondernemingsnummer": num,
            "source": "ejustice",
            "ejustice_publications": [pub],
        }