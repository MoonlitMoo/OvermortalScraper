import logging
import time

import numpy as np
import pytest

from log import logger
from scrapers.character_scraper import CharacterScraper
from tests.utils import save_log, db_session, run_function_precision, print_error_report, fix_dirs


@pytest.fixture
def scraper(db_session):
    """ Create the scraper to use with correct path to current screen. """
    from service.char_scraper_service import CharacterScraperService

    service = CharacterScraperService(db=db_session)
    s = CharacterScraper(service, own_character=False)
    return s


@save_log
def test_scrape_precision(scraper, caplog):
    """ Run scraper five times and assert no errors occur and print the variance in results.
    Expected to run from Taoist screen.
    """
    error_report, time_report = run_function_precision(scraper.scrape)
    print_error_report(error_report)
    print(f"Finished scrape in {time_report['average']:.1f} ({time_report['std']:.1f}) seconds")


@save_log
def test_scrape_cultivation(scraper, caplog):
    """ Checks we can get the cultivations.
    Expected to run from Taoist Compare BR screen.
    """
    error_report, time_report = run_function_precision(scraper.scrape_cultivation)
    print_error_report(error_report)
    print(f"Finished scrape in {time_report['average']:.1f} ({time_report['std']:.1f}) seconds")


@save_log
def test_scrape_abilities(scraper, caplog):
    """ Checks we can get the ability names.
    Expected to run from Taoist Compare BR screen.
    """
    res = scraper.scrape_abilities()
    print("\n" + caplog.text)
    assert res


def test_scrape_pets(scraper, caplog):
    """ Checks we can get the ability names.
    Expected to run from Taoist Compare BR screen.
    """
    caplog.set_level(logging.DEBUG, logger=logger.name)
    res = scraper.scrape_pets()
    print("\n" + caplog.text)
    assert res


def test_scrape_relics(scraper, caplog):
    """ Checks to see if we can get the relic names. """
    caplog.set_level(logging.DEBUG, logger=logger.name)
    res = scraper.scrape_relics()
    print("\n" + caplog.text)
    assert res


def test_update_speeds(scraper):
    tests = 50
    screen = scraper.screen
    times = []
    for _ in range(tests):
        start = time.perf_counter_ns()
        screen.colour()
        times.append(time.perf_counter_ns() - start)
    avg = np.average(times)
    std = np.std(times)
    screen.stop()
    print()
    print(f"Avg update time {avg / 1e9:.3f} ({std / 1e9:.3f}) s")
