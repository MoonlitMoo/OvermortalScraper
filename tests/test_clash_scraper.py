import numpy as np
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


@save_log
def test_basic_predictor(scraper, caplog):
    enemy_brs = np.linspace(30e9, 60e9, 5).tolist()
    scraper.own_br = 40e9
    proba = scraper.basic_predict(enemy_brs)
    assert all(proba)


@save_log
def test_get_taoist_location(scraper, caplog):
    for i in range(5):
        assert scraper.get_opponent_location(i)
