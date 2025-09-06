import os
from dotenv import load_dotenv

load_dotenv()

BOT_NAME = "kbo_project"

SPIDER_MODULES = ["kbo_project.spiders"]
NEWSPIDER_MODULE = "kbo_project.spiders"

# Langue & UA
DEFAULT_REQUEST_HEADERS = {
    "Accept-Language": os.getenv("LANG_HEADER", "fr"),
}
DOWNLOAD_DELAY = 3  # au moins 3 secondes entre requêtes
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS = 1
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0"

# USER_AGENT = (
#     "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
#     "(KHTML, like Gecko) Chrome/123.0 Safari/537.36 ScrapyTP"
# )

ROBOTSTXT_OBEY = True
DOWNLOAD_DELAY = 0.75
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 10.0
CONCURRENT_REQUESTS_PER_DOMAIN = 4

# Pipelines Mongo
ITEM_PIPELINES = {
    "kbo_project.pipelines.MongoUpsertPipeline": 300,
}

# Mongo via .env
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("DB_NAME", "kbo_tp")
MONGO_COLLECTION = os.getenv("COLLECTION_NAME", "entreprises")

# Playwright (pour NBB CBSO)
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 60_000
PLAYWRIGHT_LAUNCH_OPTIONS = {"headless": True}