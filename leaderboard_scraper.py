from db.init import init_db
from core.log import logger
from scrapers.ranking_scraper import RankingScraper
from core.screenshot_processor import ScreenshotProcessor
from core.screen import Screen

""" 
Requires running from the Chaos Ranking Otherworld BR leaderboard
"""

session = init_db()
screen = Screen(logger)
processer = ScreenshotProcessor()
scraper = RankingScraper(screen, session, processer, logger)
scraper.run()

session.close()
