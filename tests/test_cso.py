"""CSO HPM09 provider tests using a synthetic JSON-stat fixture (offline)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product.listings.cso import housing_stats  # noqa: E402

PERIODS = ["202601", "202602", "202603", "202604", "202605"]

# statistic x period x region, C-order (stat stride 5*20, period stride 20)
STATS = {
    "HPM09C01": {},  # index
    "HPM09C02": {},  # 1m %
    "HPM09C04": {},  # 12m %
}
REGIONS = {"-": 0, "01": 1, "02": 2, "05": 3, "06": 4, "07": 5, "03": 6}

value = [0.0] * (3 * len(PERIODS) * 7)
for s, sv in enumerate(STATS):
    for p, _ in enumerate(PERIODS):
        for r, _ in REGIONS.items():
            value[s * len(PERIODS) * 7 + p * 7 + REGIONS[r]] = 100.0 + p + REGIONS[r] + s * 1000

FIXTURE = {
    "dataset": {
        "version": "2.0",
        "class": "dataset",
        "id": ["STATISTIC", "TLIST(M1)", "C02803V03373"],
        "size": [3, len(PERIODS), len(REGIONS)],
        "updated": "2026-07-15T11:00:00Z",
        "dimension": {
            "STATISTIC": {
                "category": {
                    "index": {"HPM09C01": 0, "HPM09C02": 1, "HPM09C04": 2},
                    "label": {"HPM09C01": "Residential Property Price Index", "HPM09C02": "% change 1 month", "HPM09C04": "% change 12 months"},
                }
            },
            "TLIST(M1)": {
                "category": {
                    "index": {p: i for i, p in enumerate(PERIODS)},
                    "label": {p: p for p in PERIODS},
                }
            },
            "C02803V03373": {
                "category": {
                    "index": REGIONS,
                    "label": {
                        "-": "National - all residential properties",
                        "01": "National - houses",
                        "02": "National - apartments",
                        "05": "Dublin - all residential properties",
                        "06": "Dublin - houses",
                        "07": "Dublin - apartments",
                        "03": "National excluding Dublin - all residential properties",
                    },
                }
            },
            "role": {"metric": ["STATISTIC"], "time": ["TLIST(M1)"]},
        },
        "value": value,
    }
}


def test_housing_stats_parses_latest_period():
    s = housing_stats(FIXTURE)
    assert s["dataset"] == "HPM09"
    assert s["latest_period"] == "202605"
    # index for national "-" at period 202605: 100 + 4 + 0 = 104
    assert s["national"]["index"] == 104.0
    assert s["national"]["change_1m"] == 1104.0
    assert s["national"]["change_12m"] == 2104.0


def test_housing_stats_dublin_region():
    s = housing_stats(FIXTURE)
    dublin = next(r for r in s["regions"] if r["name"] == "Dublin - all residential properties")
    assert dublin["index"] == 107.0
    assert dublin["change_12m"] == 2107.0


def test_housing_stats_has_source():
    s = housing_stats(FIXTURE)
    assert "CSO" in s["source"]


def test_housing_stats_empty_on_bad_data():
    assert housing_stats({"no": "dataset"}) == {}
    assert housing_stats({"dataset": {"no": "dimension"}}) == {}
