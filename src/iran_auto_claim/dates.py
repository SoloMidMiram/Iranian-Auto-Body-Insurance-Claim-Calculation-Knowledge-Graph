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


def gregorian_to_shamsi(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    """Convert a validated proleptic-Gregorian date into a Shamsi date."""
    date(gy, gm, gd)
    month_days = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        365 * gy
        + (gy2 + 3) // 4
        - (gy2 + 99) // 100
        + (gy2 + 399) // 400
        - 80
        + gd
        + month_days[gm - 1]
    )
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm, jd = 1 + days // 31, 1 + days % 31
    else:
        jm, jd = 7 + (days - 186) // 30, 1 + (days - 186) % 30
    _validate_shamsi(jy, jm, jd)
    return jy, jm, jd


def shamsi_to_gregorian(jy: int, jm: int, jd: int) -> tuple[int, int, int]:
    """Convert a validated Shamsi date into a proleptic-Gregorian date."""
    _validate_shamsi(jy, jm, jd)
    if jy > 979:
        gy = 1600
        jy -= 979
    else:
        gy = 621
    days = 365 * jy + (jy // 33) * 8 + ((jy % 33) + 3) // 4 + 78 + jd
    days += (jm - 1) * 31 if jm < 7 else (jm - 7) * 30 + 186
    gy += 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        gy += 100 * ((days - 1) // 36524)
        days = (days - 1) % 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1
    leap = (gy % 4 == 0 and gy % 100 != 0) or gy % 400 == 0
    month_days = (0, 31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    gm = 1
    while gd > month_days[gm]:
        gd -= month_days[gm]
        gm += 1
    return gy, gm, gd
