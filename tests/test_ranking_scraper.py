import json

import pytest

from .utils import db_session, fix_dirs, save_log

from scrapers.ranking_scraper import RankingScraper


@pytest.fixture
def scraper(db_session):
    """ Create the scraper to use with correct path to current screen. """
    s = RankingScraper(db_session)
    return s


@pytest.mark.parametrize("current_taoist, expected",
                         [[0, (550, 300)], [1, (200, 300)], [2, (900, 300)], [100, None]])
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


def test_scrape_row_taoist_card(scraper):
    """ Make sure we can get the taoist info from the row card. """
    ranks = scraper.get_visible_ranks()
    scraper.current_taoist = min(ranks.keys()) - 1
    x, y = scraper.get_next_taoist()

    name, br = scraper.scrape_taoist_card(x, y)
    print(f"Found Name: {name}, BR {br}")
    assert name
    assert br


@pytest.mark.parametrize("rank", [1, 2, 3])
def test_scrape_top_taoist_card(scraper, rank):
    """ Make sure we can get taoist info for the top three taoists with special conds. """
    scraper.current_taoist = rank - 1
    x, y = scraper.get_next_taoist()

    name, br = scraper.scrape_taoist_card(x, y)
    print(f"Found Name: {name}, BR {br}")
    assert name
    assert br


def test_get_all_taoists(scraper):
    total = 0
    print()
    while scraper.current_taoist < 100:
        pos = scraper.get_next_taoist()
        scraper.current_taoist += 1
        if pos is None:
            continue
        n, b = scraper.scrape_taoist_card(*pos)
        total += 1
        print(f"Rank {scraper.current_taoist}: '{n}', {b:.3e} BR")
    assert total == 100, "Didn't find all taoists"


def test_add_taoist(scraper):
    with open('temp.json') as file:
        data = json.load(file)

    scraper.service.add_taoist_from_scrape(data)


@save_log
def test_scrape_taoist(scraper, caplog):
    pos = scraper.get_next_taoist()
    scraper.scrape_taoist(*pos)


@save_log
def test_skip_own_taoist(scraper, caplog, monkeypatch):
    """ Makes sure that we skip own taoist while iterating. """
    # Make sure we fail if we try scrape at all
    monkeypatch.setattr(scraper.taoist_scraper, "scrape", lambda: pytest.fail("Tried to scrape self"))
    # Set own ranking
    scraper.get_visible_ranks()
    if not scraper.my_ranking:
        pytest.fail("Didn't get own ranking.")
    # Set iteration to try scrape self
    scraper.current_taoist = scraper.my_ranking - 1
    scraper.run(max_rank=scraper.my_ranking)


@save_log
def test_run(scraper, caplog, monkeypatch):
    """ Test we can go through all the taoists (without scraping) """
    monkeypatch.setattr(scraper.taoist_scraper, "scrape", lambda: {})
    monkeypatch.setattr(scraper.service, "add_taoist_from_scrape", lambda x: 0)
    scraper.run()
