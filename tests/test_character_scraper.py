import logging
import os
import json
import time

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.init import seed_cultivation_levels, seed_abilities
from log import logger
from models.base import Base
from scrapers.character_scraper import CharacterScraper

# Create a test engine (use SQLite in-memory DB)
TEST_DB_URL = "sqlite:///:memory:"


def compare_dict_results(expected, found):
    n_wrong = 0
    for k, v in found.items():
        # Deal with missing value
        if k not in expected:
            print(f'Missing exact value for {k}: {v}')
            continue
        # Deal with strings
        if isinstance(v, str):
            if expected[k] != v:
                n_wrong += 1
                print(f"Found {k}: {v}, previously {expected[k]}")
            continue
        # Deal with null values
        if v is None and expected[k] is None:
            continue
        if (expected[k] is None and v is not None) or (v is None and expected[k] is not None):
            print(f"Found {k}: {v}, previously {expected[k]}")
            continue
        # Deal with numbers
        if expected[k] == 0 and v != expected[k]:
            n_wrong += 1
            print(f"Found {k}: {v}, previously {expected[k]}")
        elif expected[k] != 0 and abs(v / expected[k] - 1) > 0.01:  # Check within 1%
            n_wrong += 1
            print(f"Found {k}: {v}, previously {expected[k]} off by {v / expected[k] * 100 - 100:3.1f}%")
    for k, _ in expected.items():
        if k not in found:
            print(f"Missing scraped value for {k}")
    return n_wrong / len(found)


@pytest.fixture(autouse=True)
def fix_dirs():
    os.chdir("..")


@pytest.fixture(scope="function")
def db_session():
    # Create test engine & session
    engine = create_engine(TEST_DB_URL)
    TestingSessionLocal = sessionmaker(bind=engine)

    # Create tables
    Base.metadata.create_all(engine)
    # Yield session to test
    session = TestingSessionLocal()

    # Set up constant static tables
    seed_cultivation_levels(session)
    seed_abilities(session)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def scraper(db_session):
    """ Create the scraper to use with correct path to current screen. """
    from service.char_scraper_service import CharacterScraperService

    service = CharacterScraperService(db=db_session)
    s = CharacterScraper(service, own_character=False)
    return s


@pytest.fixture
def scraped_results(scraper):
    """ Fixture to get an initial scraped set of results.
    Expected to run from Taoist screen.
    """
    return scraper.scrape()


def test_scrape_continuity(scraped_results, scraper):
    """ Run scraper five times and assert no errors occur and print the variance in results.
    Expected to run from Taoist screen.
    """

    times = []
    error = []
    for i in range(5):
        s_time = time.perf_counter()
        stats = scraper.scrape()
        times.append(time.perf_counter() - s_time)
        print(f"Test {i} Results")
        err = compare_dict_results(scraped_results, stats)
        error.append(err)
        print(f"Error {err * 100:3.1f}%\n------------")
    print(f"Average error {np.average(error) * 100:3.1f}% with std {np.std(error) * 100:1.2f}%")
    print(f"Average time {np.average(times):3.1f}s with std {np.std(error):2.2f}s%")


def test_scrape_cultivation(scraper, caplog):
    """ Checks we can get the cultivations.
    Expected to run from Taoist Compare BR screen.
    """
    caplog.set_level(logging.DEBUG, logger=logger.name)
    try:
        res = scraper.scrape_cultivation()
    finally:
        print("\n" + caplog.text)
    assert res


def test_scrape_abilities(scraper, caplog):
    """ Checks we can get the ability names.
    Expected to run from Taoist Compare BR screen.
    """
    caplog.set_level(logging.DEBUG, logger=logger.name)
    res = scraper.scrape_abilities()
    print("\n" + caplog.text)
    assert res
