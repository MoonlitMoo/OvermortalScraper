import json
import time

import pytest

from core.log import logger
from core.screenshot_processor import ScreenshotProcessor
from core.screen import Screen
from .utils import db_session, save_log, taoist_data

from scrapers.ranking_scraper import RankingScraper


@pytest.fixture
def scraper(db_session):
    """ Create the scraper to use with correct path to current screen. """
    screen = Screen(logger)
    processor = ScreenshotProcessor()
    s = RankingScraper(screen=screen, session=db_session, processor=processor, logger=logger)
    return s


@pytest.mark.parametrize("current_taoist, expected",
                         [[1, (550, 300)], [2, (200, 300)], [3, (900, 300)], [101, None]])
def test_get_next_taoist_special_case(scraper, current_taoist, expected):
    scraper.current_taoist = current_taoist
    pos = scraper.get_taoist_pixels()
    assert pos == expected, f"Incorrect pos {pos} for current_taoist {current_taoist}"


def test_get_next_taoist_on_board(scraper):
    """ At top of leaderboard check offset between subsequent ones is close. """
    ranks = scraper.get_visible_ranks()
    first_rank = min(ranks.keys())
    # Look for first rank
    scraper.current_taoist = first_rank
    x1, y1 = scraper.get_taoist_pixels()
    scraper.current_taoist = first_rank + 1
    # Look for second rank
    x2, y2 = scraper.get_taoist_pixels()
    assert x1 == x2, "X val is different for numerical ranks"
    assert 120 < abs(y1 - y2) < 150, "Y val offset is too different for subsequent ranks"

    # See if we can scroll to next ranks
    last_rank = max(ranks.keys())
    scraper.current_taoist = last_rank + 1
    x3, y3 = scraper.get_taoist_pixels()
    assert x3, "X val for scroll rank not found"
    assert y3, "Y val for scroll rank not found"


def test_just_keep_scrolling(scraper):
    scraper.current_taoist = 100
    x, y = scraper.get_taoist_pixels()


def test_scrape_row_taoist_card(scraper):
    """ Make sure we can get the taoist info from the row card. """
    ranks = scraper.get_visible_ranks()
    scraper.current_taoist = min(ranks.keys()) - 1
    x, y = scraper.get_taoist_pixels()

    name, br = scraper.scrape_taoist_card(x, y)
    print(f"Found Name: {name}, BR {br}")
    assert name
    assert br


@pytest.mark.parametrize("rank", [1, 2, 3])
def test_scrape_top_taoist_card(scraper, rank):
    """ Make sure we can get taoist info for the top three taoists with special conds. """
    scraper.current_taoist = rank - 1
    x, y = scraper.get_taoist_pixels()

    name, br = scraper.scrape_taoist_card(x, y)
    print(f"Found Name: {name}, BR {br}")
    assert name
    assert br


@save_log
def test_duel_taoist(scraper, caplog):
    """ Checks that we can duel a taoist and detect win/loss.
    Need to be on character screen.
    """
    res = scraper.duel_taoist()
    assert res is not None


def test_add_taoist(scraper):
    with open('temp.json') as file:
        data = json.load(file)

    scraper.service.add_taoist_from_scrape(data)


@save_log
def test_scrape_taoist(scraper, caplog):
    pos = scraper.get_taoist_pixels()
    scraper.scrape_taoist(*pos)


@save_log
def test_skip_own_taoist(scraper, caplog, monkeypatch):
    """ Makes sure that we skip own taoist while iterating.
    Needs to have own rank on leaderboard visible.
    """
    # Make sure we fail if we try scrape at all
    monkeypatch.setattr(scraper.taoist_scraper, "scrape", lambda: pytest.fail("Tried to scrape self"))
    # Set own ranking
    scraper.get_visible_ranks()
    if not scraper.my_ranking:
        pytest.fail("Didn't get own ranking.")
    # Set iteration to try scrape self
    scraper.current_taoist = scraper.my_ranking - 1
    scraper.run(max_rank=scraper.my_ranking, allow_self_update=False)


@save_log
def test_scrape_own_taoist(scraper, caplog):
    """ Checks that we can correctly scrape our own taoist. """
    scraper.setup_self()


def test_add_duel_record(scraper, taoist_data):
    scraper.service.add_taoist_from_scrape(taoist_data)
    scraper.service.add_duel_result(0, 0)


@save_log
def test_run(scraper, caplog, monkeypatch):
    """ Test we can go through all the taoists without actually scraping or duelling.
    Needs to start at the top of the leaderboard.
    """

    def mock_scrape():
        time.sleep(0.5)
        return 1

    def mock_duel():
        scraper.screen.back()
        return True, 10

    class MockTaoist:
        id = 0
    scraper.current_taoist=4
    monkeypatch.setattr(scraper.taoist_scraper, "scrape", mock_scrape)
    monkeypatch.setattr(scraper.service, "add_taoist_from_scrape", lambda x: MockTaoist())
    monkeypatch.setattr(scraper.service, "add_duel_result", lambda winner_id, loser_id, duration: 0)
    # Duel exits char screen
    monkeypatch.setattr(scraper, "duel_taoist", mock_duel)
    scraper.my_database_id = 0
    scraper.run(allow_self_update=False)
