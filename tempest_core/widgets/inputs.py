"""Input widgets: text fields, selection controls and value sliders.

These are the value-bearing leaves of the IR. Each declares its change handler
in ``event_schemas`` so the boundary can validate the payload, and stores its
current value as a JSON scalar (``str``/``bool``/``float``) so the serializer
carries it to the device unchanged. The handler receives the validated typed
event (it may also be declared zero-argument when the value is not needed).

Every value-bearing widget is also **styled via the H2 Chakra-ergonomics
variant API**: it carries ``size`` / ``color_scheme`` (plus ``theme`` / ``media``
build-time inputs, kept out of the IR), the FIELD family adds ``field_variant``,
and a ``model_validator`` bakes the resolved :class:`~tempest_core.style.Style`
into ``style`` exactly like :class:`~tempest_core.widgets.button.Button`. An
explicit ``style`` override is always merged on top, so existing calls keep
working with sensible defaults.
"""

from __future__ import annotations

from enum import StrEnum
from typing import ClassVar

from pydantic import Field, PrivateAttr, model_validator

from tempest_core.icons import Icons
from tempest_core.style import ComponentState, FieldVariant, Size, Style
from tempest_core.theme import MediaQueryData, Theme
from tempest_core.variants import (
    ResponsiveSize,
    merge_styles,
    resolve_field_variant,
    resolve_field_variant_states,
    resolve_selection_variant,
    resolve_selection_variant_states,
    resolve_slider_variant,
    resolve_slider_variant_states,
)
from tempest_core.widgets.base import (
    DateChangeHandler,
    FileSelectHandler,
    RangeChangeHandler,
    SelectHandler,
    SlideHandler,
    SubmitHandler,
    TextChangeHandler,
    TimeChangeHandler,
    ToggleHandler,
    Widget,
)
from tempest_core.widgets.events import (
    DateChangeEvent,
    Event,
    FileSelectEvent,
    RangeChangeEvent,
    SelectEvent,
    SlideEvent,
    SubmitEvent,
    TextChangeEvent,
    TimeChangeEvent,
    ToggleEvent,
)

__all__ = [
    "KeyboardType",
    "Input",
    "TextArea",
    "Checkbox",
    "Switch",
    "Slider",
    "DatePicker",
    "FilePicker",
    "Dropdown",
    "TimePicker",
    "RangeSlider",
    "Autocomplete",
    "PinInput",
    "MaskedInput",
]


class KeyboardType(StrEnum):
    """The soft-keyboard variant a text field requests on the device.

    Maps to Android ``inputType`` on the device renderer and to Qt input-method
    hints in the simulator.

    Attributes:
        TEXT: The default full alphanumeric keyboard for free-form text, with no
            specialization.
        NUMBER: A numeric keypad optimized for entering numbers (digits, and
            typically a decimal/sign key).
        EMAIL: A text keyboard tuned for email addresses, surfacing the ``@`` and
            ``.`` keys for quicker entry.
        PHONE: A telephone dial pad for phone numbers (digits plus ``+``, ``*``
            and ``#``).
        URL: A text keyboard tuned for web addresses, surfacing ``/`` and ``.``
            and omitting the space bar in favor of URL-friendly keys.
        PASSWORD: A keyboard for secret entry; the field masks its characters and
            the platform disables suggestions/auto-correct so the value is not
            cached or learned.
    """

    TEXT = "text"
    NUMBER = "number"
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    PASSWORD = "password"


class _FieldWidget(Widget):
    """Mixin base for value-bearing FIELD widgets (text input / select / …).

    Holds the shared H2 field-variant machinery — the ``field_variant`` / ``size``
    / ``color_scheme`` / ``theme`` / ``media`` resolution inputs, the
    ``model_validator`` that bakes the resolved
    :class:`~tempest_core.style.Style` into ``style`` (caller override merged on
    top), and :meth:`state_styles` — so every field leaf inherits identical
    wiring, mirroring :class:`~tempest_core.widgets.button.Button`. Subclasses may
    override :meth:`_field_invalid` to drive the resolver's ``invalid`` flag (the
    text :class:`Input` does, from its ``error``). Not a concrete widget itself —
    it is never registered or serialized.

    Methods:
        state_styles: Resolve the per-interaction-state style table for the
            renderers (default/hover/pressed/disabled/focus).
    """

    #: ``theme``/``media`` are build-time resolution inputs only and stay out of
    #: the IR props (the resolved ``style`` already carries their effect).
    prop_exclude_names: ClassVar[frozenset[str]] = frozenset({"theme", "media"})

    field_variant: FieldVariant = Field(
        default=FieldVariant.OUTLINE,
        description="The field treatment (outline/filled/flushed).",
    )
    size: ResponsiveSize = Field(
        default=Size.MD,
        description="The density size — a single ``Size`` or a per-breakpoint map.",
    )
    color_scheme: str = Field(
        default="primary",
        description="The Material 3 role family the focus tint paints with.",
    )
    theme: Theme = Field(
        default_factory=Theme,
        description="The design-system theme whose tokens resolve the variant.",
    )
    media: MediaQueryData | None = Field(
        default=None,
        description="Optional viewport snapshot for a responsive ``size``.",
    )

    _style_override: Style | None = PrivateAttr(default=None)

    def _field_invalid(self) -> bool:
        """Whether the field should resolve as invalid (error role border/label).

        Returns:
            ``False`` by default; :class:`Input` overrides this from its ``error``.
        """
        return False

    @model_validator(mode="after")
    def _resolve_field_style(self) -> _FieldWidget:
        """Bake the resolved field style into ``style`` (override layered on top).

        Returns:
            The field widget with its ``style`` field resolved.
        """
        override = self.style
        self._style_override = override
        resolved = resolve_field_variant(
            variant=self.field_variant,
            size=self.size,
            color_scheme=self.color_scheme,
            theme=self.theme,
            invalid=self._field_invalid(),
            media=self.media,
        )
        merged = merge_styles(resolved, override) if override is not None else resolved
        object.__setattr__(self, "style", merged)
        return self

    def state_styles(self) -> dict[ComponentState, Style]:
        """Resolve the per-interaction-state style table for the renderers.

        Returns:
            A mapping of each :class:`~tempest_core.style.ComponentState` to its
            resolved, override-merged ``Style``.
        """
        states = resolve_field_variant_states(
            variant=self.field_variant,
            size=self.size,
            color_scheme=self.color_scheme,
            theme=self.theme,
            invalid=self._field_invalid(),
            media=self.media,
        )
        override = self._style_override
        if override is None:
            return states
        return {state: merge_styles(style, override) for state, style in states.items()}


class _SelectionWidget(Widget):
    """Mixin base for SELECTION widgets (checkbox / switch).

    Holds the shared H2 selection-variant machinery — ``size`` / ``color_scheme``
    / ``theme`` / ``media`` (no ``variant``, as M3 gives selection controls one
    affordance each), the ``model_validator`` baking the resolved
    :class:`~tempest_core.style.Style` into ``style`` from
    :func:`~tempest_core.variants.resolve_selection_variant` (passing the
    control's ``checked``), and :meth:`state_styles`. Not a concrete widget
    itself.

    Methods:
        state_styles: Resolve the per-interaction-state style table for the
            renderers (default/hover/pressed/disabled/focus).
    """

    prop_exclude_names: ClassVar[frozenset[str]] = frozenset({"theme", "media"})

    checked: bool = Field(default=False, description="Whether the control is on.")
    size: ResponsiveSize = Field(
        default=Size.MD,
        description="The density size — a single ``Size`` or a per-breakpoint map.",
    )
    color_scheme: str = Field(
        default="primary",
        description="The Material 3 role family the accent paints with.",
    )
    theme: Theme = Field(
        default_factory=Theme,
        description="The design-system theme whose tokens resolve the variant.",
    )
    media: MediaQueryData | None = Field(
        default=None,
        description="Optional viewport snapshot for a responsive ``size``.",
    )

    _style_override: Style | None = PrivateAttr(default=None)

    @model_validator(mode="after")
    def _resolve_selection_style(self) -> _SelectionWidget:
        """Bake the resolved selection style into ``style`` (override on top).

        Returns:
            The selection widget with its ``style`` field resolved.
        """
        override = self.style
        self._style_override = override
        resolved = resolve_selection_variant(
            size=self.size,
            color_scheme=self.color_scheme,
            theme=self.theme,
            checked=self.checked,
            media=self.media,
        )
        merged = merge_styles(resolved, override) if override is not None else resolved
        object.__setattr__(self, "style", merged)
        return self

    def state_styles(self) -> dict[ComponentState, Style]:
        """Resolve the per-interaction-state style table for the renderers.

        Returns:
            A mapping of each :class:`~tempest_core.style.ComponentState` to its
            resolved, override-merged ``Style``.
        """
        states = resolve_selection_variant_states(
            size=self.size,
            color_scheme=self.color_scheme,
            theme=self.theme,
            checked=self.checked,
            media=self.media,
        )
        override = self._style_override
        if override is None:
            return states
        return {state: merge_styles(style, override) for state, style in states.items()}


class _SliderWidget(Widget):
    """Mixin base for SLIDER widgets (slider / range slider).

    Holds the shared H2 slider-variant machinery — ``size`` / ``color_scheme`` /
    ``theme`` / ``media`` (no ``variant``), the ``model_validator`` baking the
    resolved :class:`~tempest_core.style.Style` into ``style`` from
    :func:`~tempest_core.variants.resolve_slider_variant`, and
    :meth:`state_styles`. Not a concrete widget itself.

    Methods:
        state_styles: Resolve the per-interaction-state style table for the
            renderers (default/hover/pressed/disabled/focus).
    """

    prop_exclude_names: ClassVar[frozenset[str]] = frozenset({"theme", "media"})

    size: ResponsiveSize = Field(
        default=Size.MD,
        description="The density size — a single ``Size`` or a per-breakpoint map.",
    )
    color_scheme: str = Field(
        default="primary",
        description="The Material 3 role family the active track paints with.",
    )
    theme: Theme = Field(
        default_factory=Theme,
        description="The design-system theme whose tokens resolve the variant.",
    )
    media: MediaQueryData | None = Field(
        default=None,
        description="Optional viewport snapshot for a responsive ``size``.",
    )

    _style_override: Style | None = PrivateAttr(default=None)

    @model_validator(mode="after")
    def _resolve_slider_style(self) -> _SliderWidget:
        """Bake the resolved slider style into ``style`` (override on top).

        Returns:
            The slider widget with its ``style`` field resolved.
        """
        override = self.style
        self._style_override = override
        resolved = resolve_slider_variant(
            size=self.size,
            color_scheme=self.color_scheme,
            theme=self.theme,
            media=self.media,
        )
        merged = merge_styles(resolved, override) if override is not None else resolved
        object.__setattr__(self, "style", merged)
        return self

    def state_styles(self) -> dict[ComponentState, Style]:
        """Resolve the per-interaction-state style table for the renderers.

        Returns:
            A mapping of each :class:`~tempest_core.style.ComponentState` to its
            resolved, override-merged ``Style``.
        """
        states = resolve_slider_variant_states(
            size=self.size,
            color_scheme=self.color_scheme,
            theme=self.theme,
            media=self.media,
        )
        override = self._style_override
        if override is None:
            return states
        return {state: merge_styles(style, override) for state, style in states.items()}


class Input(_FieldWidget):
    """A single-line editable text field, styled via the H2 field-variant API.

    The field resolves its base :class:`~tempest_core.style.Style` from its
    ``field_variant`` / ``size`` / ``color_scheme`` against the design-system
    ``theme``, via :func:`~tempest_core.variants.resolve_field_variant`, passing
    ``invalid=bool(self.error)`` so a field carrying an error message also paints
    its border/label the ``error`` role. An explicit ``style`` is **merged on top**
    of the resolved base (its set fields win), so hand-styling still works and
    existing ``Input(...)`` calls keep working with sensible defaults.

    Attributes:
        value: The current text value.
        placeholder: The hint shown when the field is empty.
        secure: Whether the text is masked (password field). When set, the
            renderer also offers a visibility toggle ("eye") that reveals the
            text locally without a round-trip to Python.
        pattern: An optional regular expression the value must fully match to be
            considered valid. The renderer evaluates it and reports the result
            via :attr:`TextChangeEvent.valid`.
        error: An optional validation message shown when the value is invalid.
            A non-empty error also forces the resolved border/label to the
            ``error`` role.
        keyboard: The soft-keyboard variant the field requests.
        max_length: An optional cap on the number of characters.
        leading_icon: An optional icon name shown inside the field on the start
            (leading) edge — a curated :class:`~tempestroid.icons.Icons` value
            (or its string) or an arbitrary platform icon name. The renderer
            resolves and places it; ``None`` shows no leading icon.
        trailing_icon: An optional icon name shown inside the field on the end
            (trailing) edge, resolved like :attr:`leading_icon`. ``None`` shows
            no trailing icon.
        field_variant: The field treatment (outline/filled/flushed).
        size: The density size — a single :class:`~tempest_core.style.Size` or a
            per-breakpoint map.
        color_scheme: The Material 3 role family the focus tint paints with.
        theme: The design-system theme whose tokens resolve the variant.
        media: Optional viewport snapshot used to resolve a responsive ``size``.
        on_change: Handler invoked with a :class:`TextChangeEvent` on each edit.
    """

    event_schemas: ClassVar[dict[str, type[Event]]] = {"on_change": TextChangeEvent}

    value: str = Field(default="", description="The current text value.")
    placeholder: str = Field(
        default="", description="The hint shown when the field is empty."
    )
    secure: bool = Field(
        default=False,
        description="Whether the text is masked (password field). When set, the "
        'renderer also offers a visibility toggle ("eye") that reveals the text '
        "locally without a round-trip to Python.",
    )
    pattern: str | None = Field(
        default=None,
        description="An optional regular expression the value must fully match to be "
        "considered valid. The renderer evaluates it and reports the result via "
        ":attr:`TextChangeEvent.valid`.",
    )
    error: str = Field(
        default="",
        description="An optional validation message shown when the value is invalid.",
    )
    keyboard: KeyboardType = Field(
        default=KeyboardType.TEXT,
        description="The soft-keyboard variant the field requests.",
    )
    max_length: int | None = Field(
        default=None, description="An optional cap on the number of characters."
    )
    leading_icon: Icons | str | None = Field(
        default=None,
        description=(
            "Optional icon name shown inside the field on the start (leading) "
            "edge — a curated Icons value or an arbitrary platform icon name."
        ),
    )
    trailing_icon: Icons | str | None = Field(
        default=None,
        description=(
            "Optional icon name shown inside the field on the end (trailing) "
            "edge — a curated Icons value or an arbitrary platform icon name."
        ),
    )
    on_change: TextChangeHandler | None = Field(
        default=None,
        description="Handler invoked with a :class:`TextChangeEvent` on each edit.",
    )

    def _field_invalid(self) -> bool:
        """Whether the field resolves as invalid (driven by ``error``).

        Returns:
            ``True`` when a non-empty validation ``error`` is set.
        """
        return bool(self.error)


class TextArea(_FieldWidget):
    """A multi-line editable text field, styled via the H2 field-variant API.

    Resolves its base :class:`~tempest_core.style.Style` from its ``field_variant``
    / ``size`` / ``color_scheme`` against the ``theme`` like :class:`Input`; an
    explicit ``style`` is merged on top.

    Attributes:
        value: The current text value.
        placeholder: The hint shown when the field is empty.
        rows: The number of visible text rows (initial height hint).
        max_length: An optional cap on the number of characters.
        field_variant: The field treatment (outline/filled/flushed).
        size: The density size — a single :class:`~tempest_core.style.Size` or a
            per-breakpoint map.
        color_scheme: The Material 3 role family the focus tint paints with.
        theme: The design-system theme whose tokens resolve the variant.
        media: Optional viewport snapshot used to resolve a responsive ``size``.
        on_change: Handler invoked with a :class:`TextChangeEvent` on each edit.
    """

    event_schemas: ClassVar[dict[str, type[Event]]] = {"on_change": TextChangeEvent}

    value: str = Field(default="", description="The current text value.")
    placeholder: str = Field(
        default="", description="The hint shown when the field is empty."
    )
    rows: int = Field(
        default=3, description="The number of visible text rows (initial height hint)."
    )
    max_length: int | None = Field(
        default=None, description="An optional cap on the number of characters."
    )
    on_change: TextChangeHandler | None = Field(
        default=None,
        description="Handler invoked with a :class:`TextChangeEvent` on each edit.",
    )


class Checkbox(_SelectionWidget):
    """A labelled boolean checkbox, styled via the H2 selection-variant API.

    Resolves its accent/ring :class:`~tempest_core.style.Style` from its ``size``
    / ``color_scheme`` against the ``theme`` (passing ``checked``); an explicit
    ``style`` is merged on top.

    Attributes:
        label: The text shown beside the control.
        checked: Whether the box is currently checked.
        size: The density size — a single :class:`~tempest_core.style.Size` or a
            per-breakpoint map.
        color_scheme: The Material 3 role family the accent paints with.
        theme: The design-system theme whose tokens resolve the variant.
        media: Optional viewport snapshot used to resolve a responsive ``size``.
        on_change: Handler invoked with a :class:`ToggleEvent` on toggle.
    """

    event_schemas: ClassVar[dict[str, type[Event]]] = {"on_change": ToggleEvent}

    label: str = Field(default="", description="The text shown beside the control.")
    on_change: ToggleHandler | None = Field(
        default=None,
        description="Handler invoked with a :class:`ToggleEvent` on toggle.",
    )


class Switch(_SelectionWidget):
    """A labelled on/off switch (toggle), styled via the H2 selection-variant API.

    Distinct from :class:`Checkbox` only in its rendered affordance — both carry
    the same boolean semantics and the same accent resolution.

    Attributes:
        label: The text shown beside the control.
        checked: Whether the switch is currently on.
        size: The density size — a single :class:`~tempest_core.style.Size` or a
            per-breakpoint map.
        color_scheme: The Material 3 role family the accent paints with.
        theme: The design-system theme whose tokens resolve the variant.
        media: Optional viewport snapshot used to resolve a responsive ``size``.
        on_change: Handler invoked with a :class:`ToggleEvent` on toggle.
    """

    event_schemas: ClassVar[dict[str, type[Event]]] = {"on_change": ToggleEvent}

    label: str = Field(default="", description="The text shown beside the control.")
    on_change: ToggleHandler | None = Field(
        default=None,
        description="Handler invoked with a :class:`ToggleEvent` on toggle.",
    )


class Slider(_SliderWidget):
    """A draggable value slider over a numeric range (H2 slider-variant API).

    Resolves its active/inactive track + thumb :class:`~tempest_core.style.Style`
    from its ``size`` / ``color_scheme`` against the ``theme``; an explicit
    ``style`` is merged on top.

    Attributes:
        value: The current value, clamped to ``[min_value, max_value]``.
        min_value: The lowest selectable value.
        max_value: The highest selectable value.
        step: The increment between selectable values.
        size: The density size — a single :class:`~tempest_core.style.Size` or a
            per-breakpoint map.
        color_scheme: The Material 3 role family the active track paints with.
        theme: The design-system theme whose tokens resolve the variant.
        media: Optional viewport snapshot used to resolve a responsive ``size``.
        on_change: Handler invoked with a :class:`SlideEvent` as the value moves.
    """

    event_schemas: ClassVar[dict[str, type[Event]]] = {"on_change": SlideEvent}

    value: float = Field(
        default=0.0,
        description="The current value, clamped to ``[min_value, max_value]``.",
    )
    min_value: float = Field(default=0.0, description="The lowest selectable value.")
    max_value: float = Field(default=100.0, description="The highest selectable value.")
    step: float = Field(
        default=1.0, description="The increment between selectable values."
    )
    on_change: SlideHandler | None = Field(
        default=None,
        description="Handler invoked with a :class:`SlideEvent` as the value moves.",
    )


class DatePicker(_FieldWidget):
    """A date selection field, styled via the H2 field-variant API (field trigger).

    Attributes:
        value: The selected date as an ISO ``yyyy-mm-dd`` string (``""`` if unset).
        label: An optional label shown with the field.
        field_variant: The field treatment (outline/filled/flushed).
        size: The density size — a single :class:`~tempest_core.style.Size` or a
            per-breakpoint map.
        color_scheme: The Material 3 role family the focus tint paints with.
        theme: The design-system theme whose tokens resolve the variant.
        media: Optional viewport snapshot used to resolve a responsive ``size``.
        on_change: Handler invoked with a :class:`DateChangeEvent` on selection.
    """

    event_schemas: ClassVar[dict[str, type[Event]]] = {"on_change": DateChangeEvent}

    value: str = Field(
        default="",
        description='The selected date as an ISO ``yyyy-mm-dd`` string (``""`` if '
        "unset).",
    )
    label: str = Field(
        default="", description="An optional label shown with the field."
    )
    on_change: DateChangeHandler | None = Field(
        default=None,
        description="Handler invoked with a :class:`DateChangeEvent` on selection.",
    )


class FilePicker(_FieldWidget):
    """A field-shaped trigger that opens the platform file picker (H2 field API).

    Attributes:
        label: The button text.
        value: The selected file's display name/URI (``""`` until one is chosen).
        field_variant: The field treatment (outline/filled/flushed).
        size: The density size — a single :class:`~tempest_core.style.Size` or a
            per-breakpoint map.
        color_scheme: The Material 3 role family the focus tint paints with.
        theme: The design-system theme whose tokens resolve the variant.
        media: Optional viewport snapshot used to resolve a responsive ``size``.
        on_select: Handler invoked with a :class:`FileSelectEvent` on selection.
    """

    event_schemas: ClassVar[dict[str, type[Event]]] = {"on_select": FileSelectEvent}

    label: str = Field(default="Choose file", description="The button text.")
    value: str = Field(
        default="",
        description='The selected file\'s display name/URI (``""`` until one is '
        "chosen).",
    )
    on_select: FileSelectHandler | None = Field(
        default=None,
        description="Handler invoked with a :class:`FileSelectEvent` on selection.",
    )


class Dropdown(_FieldWidget):
    """A single-choice dropdown / select control, styled via the H2 field API.

    Attributes:
        options: The selectable option strings, in display order.
        value: The currently selected option, or ``None`` when nothing is chosen.
        placeholder: The hint shown while no option is selected.
        leading_icon: An optional icon name shown inside the control on the start
            (leading) edge — a curated :class:`~tempestroid.icons.Icons` value
            (or its string) or an arbitrary platform icon name.
        trailing_icon: An optional icon name shown inside the control on the end
            (trailing) edge, resolved like :attr:`leading_icon`.
        field_variant: The field treatment (outline/filled/flushed).
        size: The density size — a single :class:`~tempest_core.style.Size` or a
            per-breakpoint map.
        color_scheme: The Material 3 role family the focus tint paints with.
        theme: The design-system theme whose tokens resolve the variant.
        media: Optional viewport snapshot used to resolve a responsive ``size``.
        on_select: Handler invoked with a :class:`SelectEvent` (carrying the
            option ``value`` and its 0-based ``index``) on selection.
    """

    event_schemas: ClassVar[dict[str, type[Event]]] = {"on_select": SelectEvent}

    options: list[str] = Field(
        default_factory=list,
        description="The selectable option strings, in display order.",
    )
    value: str | None = Field(
        default=None,
        description="The currently selected option, or ``None`` when nothing is "
        "chosen.",
    )
    placeholder: str = Field(
        default="Select…", description="The hint shown while no option is selected."
    )
    leading_icon: Icons | str | None = Field(
        default=None,
        description=(
            "Optional icon name shown inside the control on the start (leading) "
            "edge — a curated Icons value or an arbitrary platform icon name."
        ),
    )
    trailing_icon: Icons | str | None = Field(
        default=None,
        description=(
            "Optional icon name shown inside the control on the end (trailing) "
            "edge — a curated Icons value or an arbitrary platform icon name."
        ),
    )
    on_select: SelectHandler | None = Field(
        default=None,
        description="Handler invoked with a :class:`SelectEvent` (carrying the option "
        "``value`` and its 0-based ``index``) on selection.",
    )


class TimePicker(_FieldWidget):
    """A time selection field, styled via the H2 field-variant API (field trigger).

    Attributes:
        value: The selected time as a 24-hour ``"HH:MM"`` string (``""`` if unset).
        label: An optional label shown with the field.
        field_variant: The field treatment (outline/filled/flushed).
        size: The density size — a single :class:`~tempest_core.style.Size` or a
            per-breakpoint map.
        color_scheme: The Material 3 role family the focus tint paints with.
        theme: The design-system theme whose tokens resolve the variant.
        media: Optional viewport snapshot used to resolve a responsive ``size``.
        on_change: Handler invoked with a :class:`TimeChangeEvent` on selection.
    """

    event_schemas: ClassVar[dict[str, type[Event]]] = {"on_change": TimeChangeEvent}

    value: str = Field(
        default="",
        description='The selected time as a 24-hour ``"HH:MM"`` string (``""`` if '
        "unset).",
    )
    label: str = Field(
        default="", description="An optional label shown with the field."
    )
    on_change: TimeChangeHandler | None = Field(
        default=None,
        description="Handler invoked with a :class:`TimeChangeEvent` on selection.",
    )


class RangeSlider(_SliderWidget):
    """A dual-handle slider selecting a ``[low, high]`` sub-range (H2 slider API).

    Attributes:
        low: The current lower bound, clamped to ``[min_value, high]``.
        high: The current upper bound, clamped to ``[low, max_value]``.
        min_value: The lowest selectable value.
        max_value: The highest selectable value.
        step: The increment between selectable values.
        size: The density size — a single :class:`~tempest_core.style.Size` or a
            per-breakpoint map.
        color_scheme: The Material 3 role family the active track paints with.
        theme: The design-system theme whose tokens resolve the variant.
        media: Optional viewport snapshot used to resolve a responsive ``size``.
        on_change: Handler invoked with a :class:`RangeChangeEvent` carrying both
            bounds as the range moves.
    """

    event_schemas: ClassVar[dict[str, type[Event]]] = {"on_change": RangeChangeEvent}

    low: float = Field(
        default=0.0,
        description="The current lower bound, clamped to ``[min_value, high]``.",
    )
    high: float = Field(
        default=100.0,
        description="The current upper bound, clamped to ``[low, max_value]``.",
    )
    min_value: float = Field(default=0.0, description="The lowest selectable value.")
    max_value: float = Field(default=100.0, description="The highest selectable value.")
    step: float = Field(
        default=1.0, description="The increment between selectable values."
    )
    on_change: RangeChangeHandler | None = Field(
        default=None,
        description="Handler invoked with a :class:`RangeChangeEvent` carrying both "
        "bounds as the range moves.",
    )


class Autocomplete(_FieldWidget):
    """A text field that suggests and selects from a list of options (H2 field API).

    Emits a :class:`TextChangeEvent` as the user types and a :class:`SelectEvent`
    when a suggestion is chosen. Both handlers serialize as distinct tokens on the
    node (the multi-handler pattern shared with ``LazyColumn``).

    Attributes:
        options: The candidate suggestions, filtered against the typed text.
        value: The current text value.
        placeholder: The hint shown when the field is empty.
        leading_icon: An optional icon name shown inside the field on the start
            (leading) edge — a curated :class:`~tempestroid.icons.Icons` value
            (or its string) or an arbitrary platform icon name.
        trailing_icon: An optional icon name shown inside the field on the end
            (trailing) edge, resolved like :attr:`leading_icon`.
        field_variant: The field treatment (outline/filled/flushed).
        size: The density size — a single :class:`~tempest_core.style.Size` or a
            per-breakpoint map.
        color_scheme: The Material 3 role family the focus tint paints with.
        theme: The design-system theme whose tokens resolve the variant.
        media: Optional viewport snapshot used to resolve a responsive ``size``.
        on_change: Handler invoked with a :class:`TextChangeEvent` on each edit.
        on_select: Handler invoked with a :class:`SelectEvent` when a suggestion
            is selected.
    """

    event_schemas: ClassVar[dict[str, type[Event]]] = {
        "on_change": TextChangeEvent,
        "on_select": SelectEvent,
    }

    options: list[str] = Field(
        default_factory=list,
        description="The candidate suggestions, filtered against the typed text.",
    )
    value: str = Field(default="", description="The current text value.")
    placeholder: str = Field(
        default="", description="The hint shown when the field is empty."
    )
    leading_icon: Icons | str | None = Field(
        default=None,
        description=(
            "Optional icon name shown inside the field on the start (leading) "
            "edge — a curated Icons value or an arbitrary platform icon name."
        ),
    )
    trailing_icon: Icons | str | None = Field(
        default=None,
        description=(
            "Optional icon name shown inside the field on the end (trailing) "
            "edge — a curated Icons value or an arbitrary platform icon name."
        ),
    )
    on_change: TextChangeHandler | None = Field(
        default=None,
        description="Handler invoked with a :class:`TextChangeEvent` on each edit.",
    )
    on_select: SelectHandler | None = Field(
        default=None,
        description="Handler invoked with a :class:`SelectEvent` when a suggestion is "
        "selected.",
    )


class PinInput(_FieldWidget):
    """A segmented PIN / OTP entry of single-character cells (H2 field API).

    Forces the OUTLINE field variant (the segmented cells read as outlined boxes).
    Emits a :class:`TextChangeEvent` (the concatenated value) on each edit and a
    :class:`SubmitEvent` once every cell is filled.

    Attributes:
        length: The number of single-character cells.
        value: The current concatenated value.
        secure: Whether each cell masks its character (PIN rather than OTP).
        size: The density size — a single :class:`~tempest_core.style.Size` or a
            per-breakpoint map.
        color_scheme: The Material 3 role family the focus tint paints with.
        theme: The design-system theme whose tokens resolve the variant.
        media: Optional viewport snapshot used to resolve a responsive ``size``.
        on_change: Handler invoked with a :class:`TextChangeEvent` on each edit.
        on_complete: Handler invoked with a :class:`SubmitEvent` when all cells
            are filled.
    """

    event_schemas: ClassVar[dict[str, type[Event]]] = {
        "on_change": TextChangeEvent,
        "on_complete": SubmitEvent,
    }

    #: The PIN cells are always OUTLINE boxes; the field variant is fixed.
    field_variant: FieldVariant = Field(
        default=FieldVariant.OUTLINE,
        frozen=True,
        description="The field treatment — fixed to OUTLINE for the segmented cells.",
    )
    length: int = Field(default=6, description="The number of single-character cells.")
    value: str = Field(default="", description="The current concatenated value.")
    secure: bool = Field(
        default=False,
        description="Whether each cell masks its character (PIN rather than OTP).",
    )
    on_change: TextChangeHandler | None = Field(
        default=None,
        description="Handler invoked with a :class:`TextChangeEvent` on each edit.",
    )
    on_complete: SubmitHandler | None = Field(
        default=None,
        description="Handler invoked with a :class:`SubmitEvent` when all cells are "
        "filled.",
    )


class MaskedInput(_FieldWidget):
    """A text field that enforces an input mask while typing (H2 field API).

    The mask uses ``9`` for a required digit and ``A`` for a required letter; any
    other character is a fixed literal (e.g. ``"999.999.999-99"`` for a CPF). The
    renderer translates the mask to its native notation.

    Attributes:
        mask: The input mask pattern (``9`` digit, ``A`` letter, else literal).
        value: The current text value.
        placeholder: The hint shown when the field is empty.
        keyboard: The soft-keyboard variant the field requests.
        field_variant: The field treatment (outline/filled/flushed).
        size: The density size — a single :class:`~tempest_core.style.Size` or a
            per-breakpoint map.
        color_scheme: The Material 3 role family the focus tint paints with.
        theme: The design-system theme whose tokens resolve the variant.
        media: Optional viewport snapshot used to resolve a responsive ``size``.
        on_change: Handler invoked with a :class:`TextChangeEvent` on each edit.
    """

    event_schemas: ClassVar[dict[str, type[Event]]] = {"on_change": TextChangeEvent}

    mask: str = Field(
        default="",
        description="The input mask pattern (``9`` digit, ``A`` letter, else literal).",
    )
    value: str = Field(default="", description="The current text value.")
    placeholder: str = Field(
        default="", description="The hint shown when the field is empty."
    )
    keyboard: KeyboardType = Field(
        default=KeyboardType.TEXT,
        description="The soft-keyboard variant the field requests.",
    )
    on_change: TextChangeHandler | None = Field(
        default=None,
        description="Handler invoked with a :class:`TextChangeEvent` on each edit.",
    )
