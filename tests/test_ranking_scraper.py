import pytest

from .utils import db_session, fix_dirs
from scrapers.ranking_scraper import RankingScraper


@pytest.fixture
def scraper(db_session):
    """ Create the scraper to use with correct path to current screen. """
    s = RankingScraper(db_session)
    return s


def test_get_next_taoist(scraper):
    pass
