import pytest

from .utils import db_session, fix_dirs

from scrapers.ranking_scraper import RankingScraper


@pytest.fixture
def scraper(db_session):
    """ Create the scraper to use with correct path to current screen. """
    s = RankingScraper(db_session)
    return s


@pytest.mark.parametrize("current_taoist, expected",
                         [[0, (550, 300)], [1, (300, 300)], [2, (900, 300)], [100, None]])
def test_get_next_taoist_special_case(scraper, current_taoist, expected):
    scraper.current_taoist = current_taoist
    pos = scraper.get_next_taoist()
    assert pos == expected, f"Incorrect pos {pos} for current_taoist {current_taoist}"


def test_get_next_taoist_on_board(scraper):
    """ At top of leaderboard check offset between subsequent ones is close. """
    ranks = scraper.get_visible_ranks()
    first_rank = min(ranks.keys())
    # Look for first rank
    scraper.current_taoist = first_rank - 1
    x1, y1 = scraper.get_next_taoist()
    scraper.current_taoist = first_rank
    # Look for second rank
    x2, y2 = scraper.get_next_taoist()
    assert x1 == x2, "X val is different for numerical ranks"
    assert 120 < abs(y1 - y2) < 150, "Y val offset is too different for subsequent ranks"

    # See if we can scroll to next ranks
    last_rank = max(ranks.keys())
    scraper.current_taoist = last_rank
    x3, y3 = scraper.get_next_taoist()
    assert x3, "X val for scroll rank not found"
    assert y3, "Y val for scroll rank not found"
