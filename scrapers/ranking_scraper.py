from scrapers.character_scraper import CharacterScraper
from service.char_scraper_service import CharacterScraperService
from service.ranking_scraper_service import RankingScraperService


class RankingScraper:
    """ Scrapes taoist data from the Chaos Ranking leaderboard. """

    def __init__(self, session):
        self.service = RankingScraperService(session)
        self.taoist_scraper = CharacterScraper(CharacterScraperService(session))
        self.screen = self.taoist_scraper.screen
        self.current_taoist = 0

    def duel_taoist(self):
        # Hit the duel button
        # Check win/loss
        pass

    def scrape_taoist(self):
        # Scrape the taoist data
        # Determine if update
        # Determine if duel
        # Store results
        pass

    def run(self):
        # Iterate through taoists
        # Scrape taoist
        # End + stats
        pass
