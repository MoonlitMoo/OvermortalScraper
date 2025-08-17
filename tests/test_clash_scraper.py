import pytest

from core.log import logger
from core.screenshot_processor import ScreenshotProcessor
from core.screen import Screen
from .utils import db_session, save_log

from scrapers.clash_scraper import ClashScraper


@pytest.fixture
def scraper(db_session):
    """ Create the scraper to use with correct path to current screen. """
    screen = Screen(logger)
    processor = ScreenshotProcessor()
    s = ClashScraper(screen=screen, session=db_session, processor=processor, logger=logger)
    return s


@save_log
def test_get_opponent_br(scraper, caplog):
    """ Test that we can get the 5 enemy BRs + own BR from the Seek Opponent screen. """
    brs = scraper.get_opponent_brs()
    assert scraper.own_br
    assert len(brs) == 5
