from db.init import init_db
from log import logger
from scrapers.ranking_scraper import RankingScraper
from scrapers.screenshot_processor import ScreenshotProcesser
from screen import Screen

session = init_db()
screen = Screen(logger)
processer = ScreenshotProcesser()
scraper = RankingScraper(screen, session, processer, logger)
scraper.run()

session.close()
