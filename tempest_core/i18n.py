"""Locale and string translation context (phase E9).

A :class:`Locale` (language tag, region, layout direction) is **input context**
the ``view(app)`` reads — like :class:`~tempestroid.theme.Theme`, it is not a
node in the tree. The view picks the active language and reads ``locale.rtl`` to
build right-to-left layouts; the two ``Style`` translators mirror ``start``/
``end`` (padding, margin, text-align) when the renderer is told the layout is
RTL.

:func:`translate` (aliased :data:`t`) is a minimal, dependency-free lookup with
``str.format`` interpolation — enough for an app to localize strings without
pulling in a heavyweight i18n stack.

:func:`relative_time` formats a signed delta in seconds ("há 3 minutos", "in 2
days") through the same :class:`Locale` and :func:`translate` lookup, so a view
that localizes its labels localizes its timestamps from the same configuration.
"""

from __future__ import annotations

import math

from pydantic import ConfigDict

from tempest_core._model import _CoreModel

__all__ = [
    "Locale",
    "RELATIVE_TIME_FALLBACK_LANGUAGE",
    "RELATIVE_TIME_JUST_NOW_SECONDS",
    "RELATIVE_TIME_TRANSLATIONS",
    "RELATIVE_TIME_UNITS",
    "relative_time",
    "translate",
    "t",
]


class Locale(_CoreModel):
    """An immutable locale: language, optional region, and layout direction.

    Attributes:
        language: The BCP-47 language tag (e.g. ``"pt"``, ``"en"``, ``"ar"``).
        region: The optional region/country subtag (e.g. ``"BR"``, ``"US"``).
        rtl: Whether the locale lays out right-to-left (e.g. Arabic, Hebrew).

    Properties:
        tag: The locale as a BCP-47 tag (``language`` or ``language-REGION``).
    """

    model_config = ConfigDict(frozen=True)

    language: str = "pt"
    region: str | None = None
    rtl: bool = False

    @property
    def tag(self) -> str:
        """Render the locale as a BCP-47 tag (``language`` or ``language-REGION``).

        Returns:
            The composed tag, e.g. ``"pt-BR"`` or ``"pt"``.
        """
        return f"{self.language}-{self.region}" if self.region else self.language


def translate(
    key: str,
    locale: Locale,
    translations: dict[str, dict[str, str]],
    **kwargs: str,
) -> str:
    """Look up and interpolate a localized string.

    Resolution order, by the locale's language: a translation table keyed by
    language (``{"pt": {"hello": "Olá, {name}"}, "en": {...}}``) is searched for
    ``locale.language``; the matched string is then interpolated with ``kwargs``
    via :meth:`str.format`. When the language or key is missing, ``key`` itself is
    returned (still interpolated when possible) so a missing translation degrades
    to the developer-facing key rather than raising. A template that references a
    placeholder no value was supplied for is returned un-interpolated instead of
    crashing the view.

    Args:
        key: The translation key to resolve.
        locale: The active locale (its :attr:`Locale.language` selects the table).
        translations: A ``{language: {key: template}}`` mapping.
        **kwargs: Interpolation values applied to the resolved template.

    Returns:
        The interpolated, localized string (or the interpolated ``key`` on miss).
    """
    template = translations.get(locale.language, {}).get(key, key)
    if not kwargs:
        return template
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template


#: Convenience alias so app code can write ``from tempest_core import t``.
t = translate


RELATIVE_TIME_JUST_NOW_SECONDS: float = 30.0
"""Deltas shorter than this (in either direction) render as "now".

Ported from tempest-react-sdk's relativeTime (``abs < 30 * SECOND``).
"""

RELATIVE_TIME_UNITS: tuple[tuple[str, float, float | None], ...] = (
    ("second", 1.0, 60.0),
    ("minute", 60.0, 3_600.0),
    ("hour", 3_600.0, 86_400.0),
    ("day", 86_400.0, 604_800.0),
    ("week", 604_800.0, 2_592_000.0),
    ("month", 2_592_000.0, 31_536_000.0),
    ("year", 31_536_000.0, None),
)
"""The ``(unit, size_seconds, limit_seconds)`` ladder, smallest unit first.

A delta is expressed in the first unit whose limit it is below (a rounded
amount that reaches the limit moves on to the next unit); ``None`` marks the
open-ended last unit. A month is 30 days and a
year 365 days — calendar-free on purpose, so the result depends only on the
delta.

Ported from tempest-react-sdk's relativeTime (``SECOND`` … ``YEAR`` and the
``abs < MINUTE`` … ``abs < YEAR`` bucket chain).
"""

RELATIVE_TIME_FALLBACK_LANGUAGE: str = "en"
"""The language used when the locale's language has no relative-time table.

It also fills, key by key, any template a partial custom table leaves out.
"""

RELATIVE_TIME_TRANSLATIONS: dict[str, dict[str, str]] = {
    "pt": {
        "relative_time.now": "agora",
        "relative_time.past.second.one": "há 1 segundo",
        "relative_time.past.second.other": "há {n} segundos",
        "relative_time.past.minute.one": "há 1 minuto",
        "relative_time.past.minute.other": "há {n} minutos",
        "relative_time.past.hour.one": "há 1 hora",
        "relative_time.past.hour.other": "há {n} horas",
        "relative_time.past.day.one": "ontem",
        "relative_time.past.day.other": "há {n} dias",
        "relative_time.past.week.one": "há 1 semana",
        "relative_time.past.week.other": "há {n} semanas",
        "relative_time.past.month.one": "há 1 mês",
        "relative_time.past.month.other": "há {n} meses",
        "relative_time.past.year.one": "há 1 ano",
        "relative_time.past.year.other": "há {n} anos",
        "relative_time.future.second.one": "em 1 segundo",
        "relative_time.future.second.other": "em {n} segundos",
        "relative_time.future.minute.one": "em 1 minuto",
        "relative_time.future.minute.other": "em {n} minutos",
        "relative_time.future.hour.one": "em 1 hora",
        "relative_time.future.hour.other": "em {n} horas",
        "relative_time.future.day.one": "em 1 dia",
        "relative_time.future.day.other": "em {n} dias",
        "relative_time.future.week.one": "em 1 semana",
        "relative_time.future.week.other": "em {n} semanas",
        "relative_time.future.month.one": "em 1 mês",
        "relative_time.future.month.other": "em {n} meses",
        "relative_time.future.year.one": "em 1 ano",
        "relative_time.future.year.other": "em {n} anos",
    },
    "en": {
        "relative_time.now": "now",
        "relative_time.past.second.one": "1 second ago",
        "relative_time.past.second.other": "{n} seconds ago",
        "relative_time.past.minute.one": "1 minute ago",
        "relative_time.past.minute.other": "{n} minutes ago",
        "relative_time.past.hour.one": "1 hour ago",
        "relative_time.past.hour.other": "{n} hours ago",
        "relative_time.past.day.one": "yesterday",
        "relative_time.past.day.other": "{n} days ago",
        "relative_time.past.week.one": "1 week ago",
        "relative_time.past.week.other": "{n} weeks ago",
        "relative_time.past.month.one": "1 month ago",
        "relative_time.past.month.other": "{n} months ago",
        "relative_time.past.year.one": "1 year ago",
        "relative_time.past.year.other": "{n} years ago",
        "relative_time.future.second.one": "in 1 second",
        "relative_time.future.second.other": "in {n} seconds",
        "relative_time.future.minute.one": "in 1 minute",
        "relative_time.future.minute.other": "in {n} minutes",
        "relative_time.future.hour.one": "in 1 hour",
        "relative_time.future.hour.other": "in {n} hours",
        "relative_time.future.day.one": "in 1 day",
        "relative_time.future.day.other": "in {n} days",
        "relative_time.future.week.one": "in 1 week",
        "relative_time.future.week.other": "in {n} weeks",
        "relative_time.future.month.one": "in 1 month",
        "relative_time.future.month.other": "in {n} months",
        "relative_time.future.year.one": "in 1 year",
        "relative_time.future.year.other": "in {n} years",
    },
}
"""The built-in relative-time templates, keyed by language then by key.

Keys follow ``relative_time.<past|future>.<unit>.<one|other>`` plus
``relative_time.now``; ``{n}`` is the rounded amount. The past day singular is
"ontem" / "yesterday" as in the source; it means a 24-hour delta, not the
previous calendar day.

Ported from tempest-react-sdk's relativeTime (``PT_BR`` / ``EN``), with full
unit words and the "há" / "em" prefixes in place of its abbreviations.
"""


def _round_half_up(value: float) -> int:
    """Round a non-negative value to the nearest integer, halves going up.

    Python's :func:`round` rounds half to even (``round(2.5) == 2``); the source
    uses JavaScript's ``Math.round``, which sends halves up. Matching it keeps the
    unit boundaries identical across the two SDKs.

    Args:
        value: The non-negative amount to round.

    Returns:
        The nearest integer, with ``.5`` rounded up.
    """
    return math.floor(value + 0.5)


def _relative_time_table(
    language: str,
    translations: dict[str, dict[str, str]] | None,
) -> dict[str, dict[str, str]]:
    """Build the one-language table :func:`translate` resolves against.

    Layers, lowest first: the fallback language's built-in templates, the
    built-in templates for ``language``, then the caller's ``translations`` for
    ``language``. A partial custom table therefore degrades key by key to the
    fallback language instead of leaking a raw key.

    Args:
        language: The language to build the table for.
        translations: Optional caller-supplied ``{language: {key: template}}``.

    Returns:
        ``{language: {key: template}}`` holding every relative-time key.
    """
    custom = translations or {}
    merged = {
        **RELATIVE_TIME_TRANSLATIONS[RELATIVE_TIME_FALLBACK_LANGUAGE],
        **RELATIVE_TIME_TRANSLATIONS.get(language, {}),
        **custom.get(language, {}),
    }
    return {language: merged}


def relative_time(
    seconds: float,
    locale: Locale | None = None,
    translations: dict[str, dict[str, str]] | None = None,
) -> str:
    """Format a signed delta in seconds as localized relative time.

    The delta is ``target - now``: negative is the past ("há 3 minutos"),
    positive the future ("em 2 dias"). The core never reads a clock, so "now" is
    the app's decision and the function stays deterministic and testable.

    Rules, in order:

    #. A delta shorter than :data:`RELATIVE_TIME_JUST_NOW_SECONDS` in either
       direction — zero included — renders as "agora" / "now".
    #. Otherwise the delta picks the first unit of :data:`RELATIVE_TIME_UNITS`
       whose limit it is below, and the amount is the delta in that unit rounded
       half up. So 59 s is "59 segundos", 60 s and 89 s are "1 minuto" and 90 s
       is "2 minutos".
    #. When rounding lifts the amount to the unit's limit, the next unit takes
       over: 59.5 s is "1 minuto", never "60 segundos", and 59.5 min is "1
       hora". This step is the one deliberate divergence from the source, which
       prints "60 min atrás" there.
    #. An amount of exactly 1 picks the singular template, anything else the
       plural one.

    The language comes from ``locale`` — the same :class:`Locale` the app hands
    to :func:`translate` — and the templates are resolved through
    :func:`translate`. A language with neither a built-in nor a custom table falls
    back to :data:`RELATIVE_TIME_FALLBACK_LANGUAGE`.

    Args:
        seconds: The signed delta ``target - now``, in seconds.
        locale: The active locale; ``None`` uses the default :class:`Locale`
            (Portuguese).
        translations: Optional ``{language: {key: template}}`` overriding or
            adding templates (keys as in :data:`RELATIVE_TIME_TRANSLATIONS`),
            e.g. a Spanish table.

    Returns:
        The localized relative-time string.

    Raises:
        ValueError: If ``seconds`` is ``nan`` or infinite — no amount of time
            describes it, and rendering "há inf anos" would hide the bad input.

    Examples:
        >>> relative_time(-45)
        'há 45 segundos'
        >>> relative_time(-90)
        'há 2 minutos'
        >>> relative_time(172_800, Locale(language="en"))
        'in 2 days'
    """
    if not math.isfinite(seconds):
        raise ValueError(f"relative_time needs a finite delta, got {seconds!r}")
    active = locale if locale is not None else Locale()
    custom = translations or {}
    language = (
        active.language
        if active.language in RELATIVE_TIME_TRANSLATIONS or active.language in custom
        else RELATIVE_TIME_FALLBACK_LANGUAGE
    )
    table = _relative_time_table(language, custom)
    lookup = Locale(language=language)
    magnitude = abs(seconds)
    if magnitude < RELATIVE_TIME_JUST_NOW_SECONDS:
        return translate("relative_time.now", lookup, table)
    direction = "future" if seconds > 0 else "past"
    for unit, size, limit in RELATIVE_TIME_UNITS:
        if limit is not None and magnitude >= limit:
            continue
        amount = _round_half_up(magnitude / size)
        if limit is None or amount * size < limit:
            plurality = "one" if amount == 1 else "other"
            return translate(
                f"relative_time.{direction}.{unit}.{plurality}",
                lookup,
                table,
                n=str(amount),
            )
    raise AssertionError("RELATIVE_TIME_UNITS must end with an open-ended unit")
