"""Irish county normalisation (used by PPR parsing and provider matching)."""
from __future__ import annotations

import re

COUNTY_ALIASES = {
    "dublin": "Dublin", "dubs": "Dublin",
    "cork": "Cork", "corcaigh": "Cork",
    "galway": "Galway", "gaillimh": "Galway",
    "limerick": "Limerick", "luimneach": "Limerick",
    "waterford": "Waterford", "portlairge": "Waterford",
    "meath": "Meath", "kildare": "Kildare", "wicklow": "Wicklow",
    "kerry": "Kerry", "mayo": "Mayo", "donegal": "Donegal", "tipperary": "Tipperary",
    "wexford": "Wexford", "louth": "Louth", "westmeath": "Westmeath",
    "carlow": "Carlow", "cavan": "Cavan", "clare": "Clare", "kilkenny": "Kilkenny",
    "laois": "Laois", "leitrim": "Leitrim", "longford": "Longford",
    "monaghan": "Monaghan", "offaly": "Offaly", "roscommon": "Roscommon",
    "sligo": "Sligo",
}


def normalize_county(value: str | None) -> str | None:
    if not value:
        return None
    v = re.sub(r"^(county|co\.?)\s+", "", value.strip(), flags=re.I)
    v = re.sub(r"\s+co\.?\.?\s*$", "", v, flags=re.I)
    key = v.lower().replace("county ", "").strip()
    return COUNTY_ALIASES.get(key, v)
