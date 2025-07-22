from db.init import init_db
from scrapers.ranking_scraper import RankingScraper

session = init_db()
scraper = RankingScraper(session)
scraper.run()

session.close()
