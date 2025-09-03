from scrapy import signals

class AcceptLanguageMiddleware:
    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_request(self, request, spider):
    
        return None