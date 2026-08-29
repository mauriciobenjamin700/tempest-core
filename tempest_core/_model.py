"""The shared Pydantic base every model in the core is built on.

The core's models are not ordinary data classes: each one describes a piece of UI
that is serialized and handed to a renderer in another language (a DOM client, a
Compose device, a Qt window). What a model accepts is therefore what crosses a
process boundary, and a value the far side cannot represent is not a rendering
bug — it is a lost frame.

This module exists so that guarantee has one home. Before it, every model
subclassed :class:`pydantic.BaseModel` directly and configuration was re-declared
per class, so a rule could only ever be applied to the classes someone remembered
to visit. That is exactly how the non-finite hole below stayed open in 68 models
at once.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__: list[str] = []


class _CoreModel(BaseModel):
    """Base for every model the core serializes to a renderer.

    Subclasses declare their own ``model_config`` freely — Pydantic merges a
    subclass's config over its bases', so ``frozen``, ``extra`` and
    ``arbitrary_types_allowed`` keep working unchanged while the settings below
    survive.
    """

    #: ``allow_inf_nan=False`` because ``nan``, ``inf`` and ``-inf`` have no JSON
    #: token, and every renderer this core feeds is reached through JSON. Python's
    #: encoder writes the bare words ``NaN``/``Infinity`` by default and no
    #: browser's ``JSON.parse`` accepts them, so a single non-finite float does
    #: not corrupt one prop — it destroys the whole batch carrying it.
    #:
    #: Measured, in tempestweb issue #160: a backend metric arriving as the string
    #: ``"NaN"`` reached ``Style.width``. The batch died inside the client's
    #: decode — before the transport, before the renderer, before any diagnostic —
    #: and because the runtime had already advanced its baseline past it, the
    #: error surfaced one tick later as ``patch path out of range``, in a widget
    #: unrelated to the value. Three of seven reproductions logged nothing at all.
    #:
    #: A bound is not a substitute. ``Style.opacity`` (``ge=0.0, le=1.0``) rejects
    #: ``nan`` and ``inf`` only because ``inf <= 1.0`` is false; ``text_scale`` and
    #: ``aspect_ratio`` carry ``gt=0.0`` and accepted ``inf`` happily, since
    #: ``inf > 0.0`` is true. Only a finiteness check catches both ends.
    #:
    #: Rejecting at construction is the point: the ``ValidationError`` names the
    #: field (``width``, ``Input should be a finite number``) at the line that
    #: built the widget, instead of a serializer failing later with no idea which
    #: of a thousand nodes carried the value.
    model_config = ConfigDict(allow_inf_nan=False)
