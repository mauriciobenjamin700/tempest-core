"""``relative_time``: the cases a hand-rolled version always gets wrong.

Singular vs plural per unit, the boundary between units (a rounded amount must
never read "60 minutos"), zero and the just-now window, and "há"/"em" for past and
future — in both built-in languages. The ported constants are pinned so a drift
from ``tempest-react-sdk``'s ``relativeTime`` shows up as a failure here.
"""

from __future__ import annotations

import math

import pytest

from tempest_core import (
    RELATIVE_TIME_FALLBACK_LANGUAGE,
    RELATIVE_TIME_JUST_NOW_SECONDS,
    RELATIVE_TIME_TRANSLATIONS,
    RELATIVE_TIME_UNITS,
    Locale,
    relative_time,
)

PT = Locale(language="pt", region="BR")
EN = Locale(language="en")

MINUTE = 60.0
HOUR = 3_600.0
DAY = 86_400.0
WEEK = 7 * DAY
MONTH = 30 * DAY
YEAR = 365 * DAY


def test_ported_constants_are_pinned() -> None:
    assert RELATIVE_TIME_JUST_NOW_SECONDS == 30.0
    assert RELATIVE_TIME_UNITS == (
        ("second", 1.0, MINUTE),
        ("minute", MINUTE, HOUR),
        ("hour", HOUR, DAY),
        ("day", DAY, WEEK),
        ("week", WEEK, MONTH),
        ("month", MONTH, YEAR),
        ("year", YEAR, None),
    )
    assert RELATIVE_TIME_FALLBACK_LANGUAGE == "en"


def test_both_languages_carry_the_same_keys() -> None:
    assert set(RELATIVE_TIME_TRANSLATIONS["pt"]) == set(
        RELATIVE_TIME_TRANSLATIONS["en"]
    )


def test_default_locale_is_portuguese() -> None:
    assert relative_time(-45) == "há 45 segundos"


@pytest.mark.parametrize("seconds", [0.0, -0.0, -1.0, 1.0, -29.9, 29.9])
def test_just_now_window(seconds: float) -> None:
    assert relative_time(seconds, PT) == "agora"
    assert relative_time(seconds, EN) == "now"


@pytest.mark.parametrize(
    ("seconds", "pt", "en"),
    [
        (-30.0, "há 30 segundos", "30 seconds ago"),
        (-59.0, "há 59 segundos", "59 seconds ago"),
        (-59.5, "há 1 minuto", "1 minute ago"),
        (-60.0, "há 1 minuto", "1 minute ago"),
        (-89.0, "há 1 minuto", "1 minute ago"),
        (-90.0, "há 2 minutos", "2 minutes ago"),
        (-59 * MINUTE, "há 59 minutos", "59 minutes ago"),
        (-59.5 * MINUTE, "há 1 hora", "1 hour ago"),
        (-HOUR, "há 1 hora", "1 hour ago"),
        (-2 * HOUR, "há 2 horas", "2 hours ago"),
        (-23 * HOUR, "há 23 horas", "23 hours ago"),
        (-23.5 * HOUR, "ontem", "yesterday"),
        (-DAY, "ontem", "yesterday"),
        (-2 * DAY, "há 2 dias", "2 days ago"),
        (-6 * DAY, "há 6 dias", "6 days ago"),
        (-6.5 * DAY, "há 1 semana", "1 week ago"),
        (-WEEK, "há 1 semana", "1 week ago"),
        (-2 * WEEK, "há 2 semanas", "2 weeks ago"),
        (-29 * DAY, "há 4 semanas", "4 weeks ago"),
        (-MONTH, "há 1 mês", "1 month ago"),
        (-2 * MONTH, "há 2 meses", "2 months ago"),
        (-364 * DAY, "há 12 meses", "12 months ago"),
        (-YEAR, "há 1 ano", "1 year ago"),
        (-3 * YEAR, "há 3 anos", "3 years ago"),
    ],
)
def test_past(seconds: float, pt: str, en: str) -> None:
    assert relative_time(seconds, PT) == pt
    assert relative_time(seconds, EN) == en


@pytest.mark.parametrize(
    ("seconds", "pt", "en"),
    [
        (30.0, "em 30 segundos", "in 30 seconds"),
        (59.0, "em 59 segundos", "in 59 seconds"),
        (60.0, "em 1 minuto", "in 1 minute"),
        (89.0, "em 1 minuto", "in 1 minute"),
        (90.0, "em 2 minutos", "in 2 minutes"),
        (HOUR, "em 1 hora", "in 1 hour"),
        (5 * HOUR, "em 5 horas", "in 5 hours"),
        (DAY, "em 1 dia", "in 1 day"),
        (172_800.0, "em 2 dias", "in 2 days"),
        (WEEK, "em 1 semana", "in 1 week"),
        (3 * WEEK, "em 3 semanas", "in 3 weeks"),
        (MONTH, "em 1 mês", "in 1 month"),
        (4 * MONTH, "em 4 meses", "in 4 months"),
        (YEAR, "em 1 ano", "in 1 year"),
        (2 * YEAR, "em 2 anos", "in 2 years"),
    ],
)
def test_future(seconds: float, pt: str, en: str) -> None:
    assert relative_time(seconds, PT) == pt
    assert relative_time(seconds, EN) == en


@pytest.mark.parametrize("amount", [1, 2, 3])
@pytest.mark.parametrize("unit", ["minute", "hour", "day", "week", "month", "year"])
def test_no_amount_escapes_its_template(unit: str, amount: int) -> None:
    size = {name: size for name, size, _ in RELATIVE_TIME_UNITS}[unit]
    for locale in (PT, EN):
        for sign in (-1.0, 1.0):
            text = relative_time(sign * amount * size, locale)
            assert "{n}" not in text
            assert str(amount) in text or text in {"ontem", "yesterday"}


def test_half_rounds_up_like_math_round() -> None:
    assert relative_time(-150.0, EN) == "3 minutes ago"
    assert relative_time(-2.5 * HOUR, EN) == "3 hours ago"


def test_unknown_language_falls_back_to_english() -> None:
    assert relative_time(-90.0, Locale(language="ja")) == "2 minutes ago"


def test_custom_table_adds_a_language() -> None:
    es = {
        "es": {
            "relative_time.now": "ahora",
            "relative_time.past.minute.other": "hace {n} minutos",
        }
    }
    spanish = Locale(language="es")
    assert relative_time(0.0, spanish, es) == "ahora"
    assert relative_time(-90.0, spanish, es) == "hace 2 minutos"
    assert relative_time(-HOUR, spanish, es) == "1 hour ago"


def test_custom_table_overrides_a_builtin_template() -> None:
    override = {"pt": {"relative_time.past.day.one": "há 1 dia"}}
    assert relative_time(-DAY, PT, override) == "há 1 dia"
    assert relative_time(-2 * DAY, PT, override) == "há 2 dias"


@pytest.mark.parametrize("seconds", [math.nan, math.inf, -math.inf])
def test_non_finite_is_rejected(seconds: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        relative_time(seconds, PT)
