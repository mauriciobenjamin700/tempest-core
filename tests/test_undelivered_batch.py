"""A batch the renderer never receives must not corrupt what comes after it.

Both halves of tempestweb issue #160 live here, because they are one failure with
two doors. A single non-finite float made a whole patch batch undeliverable, and
the runtime then advanced its baseline as if it had been delivered — so the
visible error arrived one rebuild later, in a widget that had nothing to do with
the value, reading ``patch path out of range``.

Closing one door is not enough. Forbidding ``nan``/``inf`` removes the cause that
was measured; committing the baseline only after delivery removes the amplifier
that turned *any* failed delivery into a permanently desynchronized tree.
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import pkgutil
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

import tempest_core
from tempest_core import (
    App,
    Column,
    ProgressBar,
    Shadow,
    Slider,
    Style,
    Text,
)
from tempest_core.core.ir import Patch

NON_FINITE: list[float] = [float("nan"), float("inf"), float("-inf")]


def _every_model() -> list[type[BaseModel]]:
    """Collect every Pydantic model the package defines.

    Walks the package rather than reading a hand-written list, so a model added
    tomorrow is covered without anyone remembering to register it.

    Returns:
        The model classes, deduplicated and sorted by qualified name.
    """
    found: dict[type[BaseModel], None] = {}
    for module in pkgutil.walk_packages(tempest_core.__path__, "tempest_core."):
        imported = importlib.import_module(module.name)
        for obj in vars(imported).values():
            if (
                inspect.isclass(obj)
                and issubclass(obj, BaseModel)
                and obj is not BaseModel
            ):
                found[obj] = None
    return sorted(found, key=lambda cls: f"{cls.__module__}.{cls.__name__}")


def test_every_model_refuses_non_finite_floats() -> None:
    """No model in the package may accept ``nan``/``inf``, now or later.

    This is the anti-drift guard, and the reason the fix was a shared base rather
    than a config line per class. When the hole was found it was open in 68
    models at once — every one of them had been written by someone who had no
    reason to think about JSON's number grammar. A sweep makes the next model
    inherit the answer instead of rediscovering the bug.
    """
    unguarded = [
        f"{cls.__module__}.{cls.__name__}"
        for cls in _every_model()
        if cls.model_config.get("allow_inf_nan") is not False
    ]
    assert unguarded == [], (
        f"these models still accept nan/inf; they must inherit _CoreModel: {unguarded}"
    )


@pytest.mark.parametrize("value", NON_FINITE)
def test_style_refuses_non_finite_and_names_the_field(value: float) -> None:
    """``Style(width=nan)`` fails at construction, naming ``width``.

    Naming the field is the point of rejecting here rather than at serialization:
    the error lands on the line that built the widget, not on a serializer with a
    thousand nodes and no idea which one carried the value.
    """
    with pytest.raises(ValidationError) as caught:
        Style(width=value)
    error = caught.value.errors()[0]
    assert error["loc"] == ("width",)
    assert "finite" in error["msg"]


@pytest.mark.parametrize(
    ("field", "value"),
    [("text_scale", float("inf")), ("aspect_ratio", float("inf"))],
)
def test_a_one_sided_bound_does_not_stop_infinity(field: str, value: float) -> None:
    """``gt=0.0`` accepted ``inf``, because ``inf > 0.0`` is true.

    The issue reasoned that bounded fields were already safe, citing
    ``Style.opacity``. That holds only because ``opacity`` is bounded on *both*
    ends — ``inf <= 1.0`` is false. ``text_scale`` and ``aspect_ratio`` carry a
    lower bound alone and took ``inf`` happily, which is why the fix is a
    finiteness check and not a sweep for missing bounds.
    """
    with pytest.raises(ValidationError):
        Style(**{field: value})


@pytest.mark.parametrize(
    "make",
    [
        lambda v: Slider(value=v),
        lambda v: ProgressBar(value=v),
        lambda v: Shadow(blur=v),
    ],
    ids=["Slider.value", "ProgressBar.value", "Shadow.blur"],
)
def test_widgets_beyond_style_refuse_non_finite(make: Any) -> None:
    """The guard is not ``Style``-shaped; any float prop would have lost a batch."""
    with pytest.raises(ValidationError):
        make(float("nan"))


def test_finite_values_are_untouched() -> None:
    """Ordinary numbers keep working, including the serialized shape."""
    style = Style(width=12.5, opacity=0.5, gap=8.0)
    assert style.model_dump(exclude_none=True) == {
        "width": 12.5,
        "opacity": 0.5,
        "gap": 8.0,
    }


class _Recorder:
    """A renderer stub that can be told to reject one delivery.

    Attributes:
        batches: Every patch list actually accepted, in order.
        fail_next: Whether the next delivery raises instead of recording.
    """

    def __init__(self) -> None:
        """Initialize an accepting recorder."""
        self.batches: list[list[Patch]] = []
        self.fail_next: bool = False

    def __call__(self, patches: list[Patch]) -> None:
        """Accept a batch, or reject it once when armed.

        Args:
            patches: The patches the runtime is delivering.

        Raises:
            RuntimeError: When ``fail_next`` is set, standing in for anything
                that can break between the runtime and the far side (an encoder
                refusing a payload, a closed socket, a client that cannot decode).
        """
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("renderer refused the batch")
        self.batches.append(patches)


def _text_of(app: App[dict[str, str]]) -> str:
    """Read the label the app's current baseline says is on screen.

    Args:
        app: The app to inspect.

    Returns:
        The ``content`` prop of the single child of the baseline's root.
    """
    scene = app.current_tree
    assert scene is not None
    return str(scene.root.children[0].props["content"])


def _app(recorder: _Recorder) -> App[dict[str, str]]:
    """Build a started one-label app driven by ``recorder``.

    Args:
        recorder: The renderer stub receiving the patches.

    Returns:
        The app, already started (baseline recorded).
    """
    app: App[dict[str, str]] = App(
        state={"label": "a"},
        view=lambda a: Column(children=[Text(content=a.state["label"], key="t")]),
        apply_patches=recorder,
    )
    app.start()
    return app


async def test_a_failed_delivery_leaves_the_baseline_behind() -> None:
    """When applying raises, the baseline keeps describing what the renderer has.

    Committing first is what turned a lost batch into a permanently desynchronized
    tree: the next diff was taken against a scene the renderer had never received.
    """
    recorder = _Recorder()
    app = _app(recorder)
    assert _text_of(app) == "a"

    recorder.fail_next = True
    asyncio.get_running_loop().set_exception_handler(lambda loop, context: None)
    app.set_state(lambda s: s.__setitem__("label", "b"))
    await asyncio.sleep(0)

    assert recorder.batches == []
    assert _text_of(app) == "a"


async def test_the_next_rebuild_re_sends_what_the_failed_delivery_lost() -> None:
    """The baseline staying put is what makes the loss self-healing.

    The lost edit is not replayed from a buffer — it does not need to be. The next
    rebuild diffs from the tree the renderer really has, so the work the failed
    batch carried is regenerated on the spot.

    The shape is the one #160 reported: a container whose children grow (an app
    bar gaining its second action). A lost *insert* is what a later diff cannot
    recover on its own, because with the baseline wrongly advanced the runtime
    believes the child is already on screen and never mentions it again — which
    is how the renderer ended up addressing ``…/appbar-actions/1`` against a node
    that had one child.
    """
    actions: list[str] = ["logout"]
    recorder = _Recorder()
    app: App[dict[str, str]] = App(
        state={"title": "panel"},
        view=lambda a: Column(
            key="bar",
            children=[Text(content=name, key=name) for name in actions],
        ),
        apply_patches=recorder,
    )
    app.start()

    recorder.fail_next = True
    asyncio.get_running_loop().set_exception_handler(lambda loop, context: None)
    actions.insert(0, "search")
    app.set_state()
    await asyncio.sleep(0)
    assert recorder.batches == []

    app.set_state(lambda s: s.__setitem__("title", "dashboard"))
    await asyncio.sleep(0)

    kinds = [type(patch).__name__ for patch in recorder.batches[0]]
    assert "Insert" in kinds, (
        "the insert the failed batch carried was never re-sent; the renderer is "
        f"missing a child forever. delivered: {kinds}"
    )
    scene = app.current_tree
    assert scene is not None
    assert [child.key for child in scene.root.children] == ["search", "logout"]


def test_swap_view_also_holds_the_baseline_when_delivery_fails() -> None:
    """The hot-reload path commits through the same method, so it inherits it.

    Both call sites had the same ordering, and fixing only the scheduled rebuild
    would have left the defect alive behind ``swap_view``.
    """
    recorder = _Recorder()
    app = _app(recorder)

    recorder.fail_next = True
    with pytest.raises(RuntimeError):
        app.swap_view(
            lambda a: Column(children=[Text(content="swapped", key="t")]),
        )

    assert _text_of(app) == "a"
    assert recorder.batches == []
