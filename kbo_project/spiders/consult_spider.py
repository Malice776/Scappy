import csv
import scrapy
from kbo_project.utils.parsing import clean_num, parse_date

class ConsultSpider(scrapy.Spider):
    name = "consult_spider"

    def start_requests(self):
        with open("entreprises.csv", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                num = clean_num(row.get("EnterpriseNumber", ""))  
                if not num:
                    continue
                url = f"https://consult.cbso.nbb.be/consult-enterprise/{num}"
                yield scrapy.Request(
                    url,
                    meta={"playwright": True, "playwright_page_methods": [
                        ("wait_for_selector", "text=Dépôts"),
                    ]},
                    callback=self.parse_deposits,
                    cb_kwargs={"num": num},
                )

    async def parse_deposits(self, response, num):
        rows = response.css("table tr, .deposit-row, .mat-row")
        for r in rows:
            year = "".join(r.css("td:nth-child(1) ::text, .year::text").getall()).strip()
            date_txt = "".join(r.css("td:nth-child(2) ::text, .date::text").getall()).strip()
            type_txt = "".join(r.css("td:nth-child(3) ::text, .type::text").getall()).strip()
            ref = "".join(r.css("td:nth-child(4) ::text, .ref::text").getall()).strip()
            pdf = r.css("a[href*='.pdf']::attr(href)").get()
            if not (year or date_txt or type_txt or ref or pdf):
                continue
            yield {
                "EnterpriseNumbe": num,
                "source": "nbb",
                "nbb_depots": [{
                    "exercice": year or None,
                    "date_depot": parse_date(date_txt),
                    "type": type_txt or None,
                    "reference": ref or None,
                    "pdf_url": response.urljoin(pdf) if pdf else None,
                    "page_url": response.url,
                }],
            }