"""Canonical calendar parsing for claim facts.

The public claim schema predates explicit calendar fields for occurrence,
awareness and declaration dates.  Until that schema is versioned, these fields
use one closed compatibility contract:

* ``YYYY/MM/DD`` is explicitly Shamsi;
* ``YYYY-MM-DD`` with a year from 1300 through 1500 is legacy Shamsi;
* ``YYYY-MM-DD`` with a year from 1600 through 9999 is Gregorian; and
* every other spelling/year is rejected as ambiguous.

The theft clock is not legacy input: its ``calendar`` member is authoritative.
``regulatory_snapshot.as_of_date`` is an ISO Gregorian evaluation cutoff and is
validated by the JSON-schema layer.  It does not select the event snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from functools import lru_cache
import re


SHAMSI = "SHAMSI"
GREGORIAN = "GREGORIAN"
LEGACY_SHAMSI_YEAR_MIN = 1300
LEGACY_SHAMSI_YEAR_MAX = 1500
LEGACY_GREGORIAN_YEAR_MIN = 1600
LEGACY_GREGORIAN_YEAR_MAX = 9999

_DATE = re.compile(r"^(?P<year>[0-9]{4})(?P<sep>[-/])(?P<month>[0-9]{2})(?P=sep)(?P<day>[0-9]{2})$")
_SHAMSI_BREAK_YEARS = (
    -61,
    9,
    38,
    199,
    426,
    686,
    756,
    818,
    1111,
    1181,
    1210,
    1635,
    2060,
    2097,
    2192,
    2262,
    2324,
    2394,
    2456,
    3178,
)
_SHAMSI_ANCHOR_YEAR = 1404
_SHAMSI_ANCHOR_ORDINAL = date(2025, 3, 21).toordinal()


class CalendarDateError(ValueError):
    """A date is malformed, impossible, or calendar-ambiguous."""


@dataclass(frozen=True)
class ClaimDate:
    year: int
    month: int
    day: int
    calendar: str

    @property
    def canonical(self) -> str:
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"

    @property
    def shamsi(self) -> tuple[int, int, int]:
        if self.calendar == SHAMSI:
            return self.year, self.month, self.day
        return gregorian_to_shamsi(self.year, self.month, self.day)

    @property
    def iranian_year(self) -> int:
        return self.shamsi[0]

    @property
    def chronology_key(self) -> int:
        if self.calendar == GREGORIAN:
            return date(self.year, self.month, self.day).toordinal()
        gy, gm, gd = shamsi_to_gregorian(self.year, self.month, self.day)
        return date(gy, gm, gd).toordinal()

    @property
    def snapshot_anchor(self) -> str:
        year, month, day = self.shamsi
        return f"{year:04d}/{month:02d}/{day:02d}"


def parse_claim_date(value: object, *, calendar: str | None = None) -> ClaimDate:
    """Parse and validate a legacy claim date or an explicitly calendared date."""
    if not isinstance(value, str):
        raise CalendarDateError("date must be a string")
    match = _DATE.fullmatch(value)
    if match is None:
        raise CalendarDateError("date must be YYYY-MM-DD or YYYY/MM/DD")
    year = int(match.group("year"))
    month = int(match.group("month"))
    day = int(match.group("day"))
    separator = match.group("sep")

    chosen = str(calendar or "").upper() or None
    explicit_calendar = chosen is not None
    if chosen is None:
        if separator == "/":
            chosen = SHAMSI
        elif LEGACY_SHAMSI_YEAR_MIN <= year <= LEGACY_SHAMSI_YEAR_MAX:
            chosen = SHAMSI
        elif LEGACY_GREGORIAN_YEAR_MIN <= year <= LEGACY_GREGORIAN_YEAR_MAX:
            chosen = GREGORIAN
        else:
            raise CalendarDateError(
                "date calendar is ambiguous; use YYYY/MM/DD for Shamsi or a supported ISO Gregorian year"
            )
    elif chosen not in (SHAMSI, GREGORIAN):
        raise CalendarDateError(f"unsupported calendar {calendar!r}")

    if explicit_calendar and separator != "-":
        raise CalendarDateError("explicitly calendared dates must use YYYY-MM-DD")

    if chosen == GREGORIAN:
        if separator != "-":
            raise CalendarDateError("Gregorian dates must use YYYY-MM-DD")
        try:
            date(year, month, day)
        except ValueError as error:
            raise CalendarDateError(f"invalid Gregorian date: {error}") from error
    else:
        _validate_shamsi(year, month, day)
    return ClaimDate(year, month, day, chosen)


def is_shamsi_leap_year(year: int) -> bool:
    """Return JalCal's leap-year result for its supported Shamsi interval."""
    if year < 1 or year >= _SHAMSI_BREAK_YEARS[-1]:
        raise CalendarDateError(f"unsupported Shamsi year {year!r}")
    previous_break = _SHAMSI_BREAK_YEARS[0]
    jump = 0
    for current_break in _SHAMSI_BREAK_YEARS[1:]:
        jump = current_break - previous_break
        if year < current_break:
            break
        previous_break = current_break
    offset = year - previous_break
    if jump - offset < 6:
        offset = offset - jump + ((jump + 4) // 33) * 33
    leap_index = (((offset + 1) % 33) - 1) % 4
    return leap_index == 0


def _validate_shamsi(year: int, month: int, day: int) -> None:
    is_leap = is_shamsi_leap_year(year)
    if month < 1 or month > 12:
        raise CalendarDateError("invalid Shamsi month")
    if month <= 6:
        maximum = 31
    elif month <= 11:
        maximum = 30
    else:
        maximum = 30 if is_leap else 29
    if day < 1 or day > maximum:
        raise CalendarDateError("invalid Shamsi day")


def _shamsi_year_length(year: int) -> int:
    return 366 if is_shamsi_leap_year(year) else 365


@lru_cache(maxsize=None)
def _shamsi_year_start_ordinal(year: int) -> int:
    """Return a Gregorian ordinal for a supported Shamsi year boundary.

    The upper sentinel is the first day after the supported interval.  Building
    conversion from the same break-table leap predicate used by validation
    prevents boundary collisions where a validated Esfand 30 was previously
    converted with a different 33-year approximation.
    """
    if year < 1 or year > _SHAMSI_BREAK_YEARS[-1]:
        raise CalendarDateError(f"unsupported Shamsi year boundary {year!r}")
    if year >= _SHAMSI_ANCHOR_YEAR:
        elapsed = sum(
            _shamsi_year_length(item)
            for item in range(_SHAMSI_ANCHOR_YEAR, year)
        )
        return _SHAMSI_ANCHOR_ORDINAL + elapsed
    elapsed = sum(
        _shamsi_year_length(item)
        for item in range(year, _SHAMSI_ANCHOR_YEAR)
    )
    return _SHAMSI_ANCHOR_ORDINAL - elapsed


def _shamsi_day_offset(month: int, day: int) -> int:
    if month <= 6:
        return (month - 1) * 31 + day - 1
    return 186 + (month - 7) * 30 + day - 1


def gregorian_to_shamsi(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    """Convert a validated proleptic-Gregorian date into a Shamsi date."""
    ordinal = date(gy, gm, gd).toordinal()
    lower = _shamsi_year_start_ordinal(1)
    upper = _shamsi_year_start_ordinal(_SHAMSI_BREAK_YEARS[-1])
    if ordinal < lower or ordinal >= upper:
        raise CalendarDateError(
            "Gregorian date is outside the supported Shamsi conversion interval"
        )

    low = 1
    high = _SHAMSI_BREAK_YEARS[-1]
    while low + 1 < high:
        middle = (low + high) // 2
        if _shamsi_year_start_ordinal(middle) <= ordinal:
            low = middle
        else:
            high = middle
    jy = low
    days = ordinal - _shamsi_year_start_ordinal(jy)
    if days < 186:
        jm, jd = 1 + days // 31, 1 + days % 31
    else:
        jm, jd = 7 + (days - 186) // 30, 1 + (days - 186) % 30
    _validate_shamsi(jy, jm, jd)
    return jy, jm, jd


def shamsi_to_gregorian(jy: int, jm: int, jd: int) -> tuple[int, int, int]:
    """Convert a validated Shamsi date into a proleptic-Gregorian date."""
    _validate_shamsi(jy, jm, jd)
    converted = date.fromordinal(
        _shamsi_year_start_ordinal(jy) + _shamsi_day_offset(jm, jd)
    )
    return converted.year, converted.month, converted.day
