"""The root re-exports every public name, in the form strict checkers need.

Two things go wrong here, and only one of them shows up in a test run.

**The surface.** ``tempest_core.widgets`` declared 158 public names and the root
re-exported 9 of them, so ``from tempest_core import Menu`` raised while
``from tempest_core.widgets import Menu`` worked. Consumers then imported from
submodules, against the "import from the root" convention, and 50 files in
tempestweb did exactly that.

**The form.** A plain ``from x import Y`` in an ``__init__.py`` re-exports at
runtime but is not a *declared* re-export: basedpyright and Pylance in strict
mode report `Y` as an unknown import symbol in the consumer, even though it
imports fine. The fix is to write the name twice — ``from x import Y as Y``
(PEP 484) **and** ``__all__``. Measured on a strict consumer importing eight
root names: 7 errors before, 0 after.

Neither failure is visible to ``mypy`` or to any test that merely imports the
package, which is why they survived. These pin both.
"""

from __future__ import annotations

import re
from pathlib import Path

import tempest_core

ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "tempest_core" / "__init__.py"

#: A declared re-export: the name written twice, as PEP 484 requires. Matches
#: both the one-per-line form inside a parenthesised block and the single-name
#: form written inline after import.
_AS_FORM = re.compile(r"(\w+) as (\w+)")

#: Subpackages whose public surface the root is expected to carry whole.
_FACADES: tuple[str, ...] = ("tempest_core.widgets", "tempest_core.components")


def _declared_reexports() -> set[str]:
    """Return every name the root re-exports in the ``as`` form.

    Returns:
        set[str]: The names written as ``X as X`` in the root ``__init__``.
    """
    source = INIT.read_text()
    return {name for name, alias in _AS_FORM.findall(source) if name == alias}


def test_every_exported_name_uses_the_as_form() -> None:
    """A plain import re-exports at runtime and not to a strict checker."""
    declared = _declared_reexports()

    plain = sorted(set(tempest_core.__all__) - declared)

    assert plain == [], (
        "these are in __all__ but not re-exported as `X as X`, so basedpyright "
        f"and Pylance strict call them unknown import symbols: {plain}"
    )


def test_every_exported_name_resolves() -> None:
    """``__all__`` promising a name the module does not have is a broken import."""
    missing = [name for name in tempest_core.__all__ if not hasattr(tempest_core, name)]

    assert missing == [], missing


def test_the_root_carries_each_facade_whole() -> None:
    """A name public in a facade but absent from the root sends consumers inward."""
    root = set(tempest_core.__all__)
    gaps: dict[str, list[str]] = {}
    for facade in _FACADES:
        module = __import__(facade, fromlist=["__all__"])
        public = {name for name in module.__all__ if not name.startswith("_")}
        absent = sorted(public - root)
        if absent:
            gaps[facade] = absent

    assert gaps == {}, (
        "public in a facade, missing at the root — a consumer following the "
        f"import-from-the-root convention cannot reach these: {gaps}"
    )
