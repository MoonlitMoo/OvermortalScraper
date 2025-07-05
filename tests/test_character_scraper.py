import functools
import logging
import math
import os
import json
import statistics
import time
from collections import defaultdict, Counter

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.init import seed_cultivation_levels, seed_abilities, seed_rarities, seed_pet
from log import logger
from models.base import Base
from scrapers.character_scraper import CharacterScraper

# Create a test engine (use SQLite in-memory DB)
TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture(autouse=True)
def fix_dirs():
    os.chdir("..")


def save_log(test_func):
    @functools.wraps(test_func)
    def wrapper(*args, **kwargs):
        caplog = kwargs.get("caplog", None)
        caplog.set_level(logging.DEBUG, logger=logger.name)
        try:
            test_func(*args, **kwargs)
        except Exception as e:
            raise  # Re-raise to ensure the test still fails
        finally:
            # Save log
            with open("tests/overmortal_bot.log", "w") as file:
                file.write(caplog.text)

    return wrapper


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
    seed_rarities(session)
    seed_abilities(session)
    seed_pet(session)

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
    yield s

    s.stop()


def run_function_precision(target_func, runs=5, abs_tol=1e-9, rel_tol=None):
    results = []
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        results.append(target_func())
        times.append(time.perf_counter() - start)

    keys = results[0].keys()
    per_key_values = defaultdict(list)
    # Organise results per key
    for res in results:
        for k in keys:
            per_key_values[k].append(res[k])

    # Assume the mode is the true result
    mode_values = {}
    for k, vals in per_key_values.items():
        filtered = [v for v in vals if v is not None]
        if not filtered:
            mode_values[k] = None
        else:
            try:
                mode_values[k] = statistics.mode(filtered)
            except statistics.StatisticsError:
                mode_values[k] = Counter(filtered).most_common(1)[0][0]

    # Use absolute tol by default for float mode
    def is_close(a, b):
        if rel_tol is not None:
            return math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)
        return math.isclose(a, b, abs_tol=abs_tol)

    error_report = {}
    total_errors = 0
    for k, vals in per_key_values.items():
        true_val = mode_values[k]

        if isinstance(true_val, float):
            errors = [
                abs(v - true_val) if v is not None else math.nan
                for v in vals
            ]
            errors = [e for e in errors if not math.isnan(e)]

            if all(v is not None and is_close(v, true_val) for v in vals):
                continue
            total_errors += len([e for e in errors if not is_close(e, true_val)])
            error_report[k] = {
                "type": "float",
                "mean_abs_error": sum(errors) / len(errors) if errors else None,
                "true_value": true_val,
                "all_values": vals
            }

        elif isinstance(true_val, str) or true_val is None:
            mismatches = sum(1 for v in vals if v != true_val)
            if mismatches == 0:
                continue
            total_errors += mismatches
            error_report[k] = {
                "type": "None" if true_val is None else "str",
                "mismatch_count": mismatches,
                "total": len(vals),
                "true_value": true_val,
                "all_values": vals
            }

        else:
            continue
    if total_errors != 0:
        error_report["avg_error_per_run"] = total_errors / (len(per_key_values) * runs)

    time_report = {
        "average": np.average(times),
        "std": np.std(times)
    }

    return error_report, time_report


def print_error_report(error_report):
    print()
    if not error_report:
        print("All values matched their expected mode — no errors found.")
        return

    for key, info in error_report.items():
        if key == "avg_error_per_run":
            continue
        print(f"🔹 Key: {key}")
        print(f"   Type: {info['type']}")
        print(f"   True Value: {info.get('true_value')}")

        if info['type'] == 'float':
            print(f"   Mean Absolute Error: {info['mean_abs_error']:.6g}")
            print(f"   Values: {', '.join(str(v) for v in info['all_values'])}")

        elif info['type'] == 'str':
            print(f"   Mismatches: {info['mismatch_count']} / {info['total']}")
            print(f"   Values: {', '.join(str(v) for v in info['all_values'])}")

        elif info['type'] == 'None':
            print(f"   Mismatches: {info['mismatch_count']} / {info['total']}")
            print(f"   Values: {', '.join(str(v) for v in info['all_values'])}")
        print()
    print(f"Average error per run {error_report['avg_error_per_run'] * 100:.2f}%")
    print()


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
