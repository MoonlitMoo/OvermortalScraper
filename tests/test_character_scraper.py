import logging
import os
import json
import time

import numpy as np
import pytest

from log import logger
from scrapers.character_scraper import CharacterScraper


def compare_dict_results(expected, found):
    n_wrong = 0
    for k, v in found.items():
        if k not in expected:
            print(f'Missing exact value for {k}: {v}')
            continue
        if isinstance(v, str):
            if expected[k] != v:
                n_wrong += 1
                print(f"Found {k}: {v}, previously {expected[k]}")
            continue
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


@pytest.fixture
def scraper():
    """ Create the scraper to use with correct path to current screen. """
    s = CharacterScraper(own_character=False)
    return s


@pytest.fixture
def scraped_results(tmp_path, scraper):
    """ Fixture to get an initial scraped set of results.
    Expected to run from Taoist screen.
    """
    file_path = os.path.join(tmp_path, "test_output.txt")
    res = scraper.scrape()
    with open(file_path, 'w') as file:
        file.write(json.dumps(res, indent=2))
    return file_path


def test_scrape_continuity(scraped_results, scraper):
    """ Run scraper five times and assert no errors occur and print the variance in results.
    Expected to run from Taoist screen.
    """
    with open(scraped_results, 'r', encoding='utf-8') as file:
        first_run = json.load(file)

    times = []
    error = []
    for i in range(5):
        s_time = time.perf_counter()
        stats = scraper.scrape()
        times.append(time.perf_counter() - s_time)
        print(f"Test {i} Results")
        err = compare_dict_results(first_run, stats)
        error.append(err)
        print(f"Error {err * 100:3.1f}%\n------------")
    print(f"Average error {np.average(error) * 100:3.1f}% with std {np.std(error) * 100:1.2f}%")
    print(f"Average time {np.average(times):3.1f}s with std {np.std(error):2.2f}s%")


def test_scrape_abilities(scraper, caplog):
    """ Checks we can get the abilitie names.
    Expected to run from Taoist Compare BR screen.
    """
    caplog.set_level(logging.DEBUG, logger=logger.name)
    res = scraper.scrape_abilities()
    print("\n" + caplog.text)
    assert res
