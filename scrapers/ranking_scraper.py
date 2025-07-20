from log import logger
from scrapers.character_scraper import CharacterScraper
from service.char_scraper_service import CharacterScraperService
from service.ranking_scraper_service import RankingScraperService


class RankingScraper:
    """ Scrapes taoist data from the Chaos Ranking leaderboard. """

    def __init__(self, session):
        self.service = RankingScraperService(session)
        self.taoist_scraper = CharacterScraper(CharacterScraperService(session))
        self.screen = self.taoist_scraper.screen
        self.processor = self.taoist_scraper.processor
        self.current_taoist = 0
        self.my_ranking = None


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

    def get_visible_ranks(self):
        """ Gets dictionary of rank to y value from the current screen.

        Returns
        dict
            rank: y value
        """
        # Find all the BR pics, sorted in ascending y.
        br_image = "resources/ranking_scraper/br_symbol.png"
        br_positions = self.screen.find_all_images(br_image)
        br_positions = sorted(br_positions, key=lambda x: x[0][1])

        ranks = []
        y_vals = []
        # Get all the ranking numbers
        for (_, y), _ in br_positions:
            box = (55, 140, y, y + 60)  # Box x + size is constant, we just need the right y values from br icons.
            text = self.processor.extract_text_from_area(self.screen.CURRENT_SCREEN, box)
            try:
                ranks.append(int(text))
                y_vals.append(y + 30)  # Set the y value to be centred on the row with +30 offset
            except ValueError:
                logger.warning(f"[get_next_taoist] Failed to get rank from text {text}.")

        # Last one is always me, so we can trim it off
        if self.my_ranking is None:
            self.my_ranking = ranks[-1]

        return {r: y for r, y in zip(ranks[:-1], y_vals[:-1])}

    def get_next_taoist(self):
        """ Using the current taoist rank, get the pixel to click for the next taoist to scrape. \

        Returns
        int, int | None
            Y value of the next taoist, centred in row. None if next not found.
        """
        match self.current_taoist:
            case 0:  # Get number 1 taoist
                return 550, 300
            case 1:  # Get number 2 taoist
                return 300, 300
            case 2:  # Get number 3 taoist
                return 900, 300
            case 100:  # Last taoist
                return None
            case _:  # Get next numerical taoist
                pass
        assert 2 < self.current_taoist < 100, "Unknown taoist case"

        next_rank = self.current_taoist + 1
        ranks = self.get_visible_ranks()
        # Try scroll if not found
        if next_rank not in ranks:
            self.screen.swipe(5, 1200, 5, 800, 200)  # 400 pixel ~3 rows
            self.screen.swipe(5, 1200, 500, 1200, 100)  # Slide horizontal to stop any further scrolling
            ranks = self.get_visible_ranks()
            if next_rank not in ranks:
                logger.warning("[get_next_taoist] Failed to get next taoist after scroll")
                return None
        return 300, ranks[next_rank]

    def run(self):
        # Iterate through taoists
        # Scrape taoist
        # End + stats
        pass
