"""The legacy calendar compatibility contract is explicit and bounded."""

from __future__ import annotations

import pytest

from iran_auto_claim.dates import (
    GREGORIAN,
    SHAMSI,
    CalendarDateError,
    parse_claim_date,
)


@pytest.mark.parametrize(
    ("value", "calendar"),
    [
        ("1300-01-01", SHAMSI),
        ("1500-01-01", SHAMSI),
        ("1600-01-01", GREGORIAN),
        ("9999-12-31", GREGORIAN),
    ],
)
def test_legacy_calendar_range_boundaries(value, calendar):
    assert parse_claim_date(value).calendar == calendar


@pytest.mark.parametrize(
    "value",
    [
        "0001-01-01",
        "1299-12-29",
        "1501-01-01",
        "1599-12-31",
    ],
)
def test_dash_dates_between_compatibility_ranges_are_ambiguous(value):
    with pytest.raises(CalendarDateError, match="calendar is ambiguous"):
        parse_claim_date(value)


def test_explicit_calendar_metadata_overrides_the_legacy_year_heuristic():
    assert parse_claim_date("1501-01-01", calendar=SHAMSI).calendar == SHAMSI
    assert parse_claim_date("1501-01-01", calendar=GREGORIAN).calendar == GREGORIAN
    assert parse_claim_date("1404-01-01", calendar=GREGORIAN).calendar == GREGORIAN
    assert parse_claim_date("2025-03-21", calendar=SHAMSI).calendar == SHAMSI


def test_explicit_calendar_metadata_requires_the_canonical_dash_spelling():
    with pytest.raises(CalendarDateError, match="explicitly calendared"):
        parse_claim_date("1404/01/01", calendar=SHAMSI)


def test_equivalent_gregorian_and_shamsi_dates_share_one_chronology_key():
    shamsi = parse_claim_date("1404-01-01", calendar=SHAMSI)
    gregorian = parse_claim_date("2025-03-21", calendar=GREGORIAN)
    assert shamsi.chronology_key == gregorian.chronology_key
    assert gregorian.snapshot_anchor == "1404/01/01"


def test_legacy_shamsi_slash_form_is_explicit_outside_the_dash_range():
    parsed = parse_claim_date("1200/01/01")
    assert parsed.calendar == SHAMSI
    assert parsed.canonical == "1200-01-01"
