# from typing import Any, Dict, List, Optional
# from dataclasses import dataclass, field

# @dataclass
# class EntrepriseItem:
#     ondernemingsnummer: str
#     source: str
#     kbo: Dict[str, Any] | None = None
#     ejustice_publications: List[Dict[str, Any]] = field(default_factory=list)
#     nbb_depots: List[Dict[str, Any]] = field(default_factory=list)


import scrapy

class EJusticePublicationItem(scrapy.Item):
    numero = scrapy.Field()
    titre = scrapy.Field()
    code = scrapy.Field()
    adresse = scrapy.Field()
    type = scrapy.Field()
    date = scrapy.Field()
    reference = scrapy.Field()
    image_url = scrapy.Field()
    detail_url = scrapy.Field()

class EJusticeItem(scrapy.Item):
    EnterpriseNumber = scrapy.Field()
    source = scrapy.Field()
    ejustice_publications = scrapy.Field()  # liste de EJusticePublicationItem
