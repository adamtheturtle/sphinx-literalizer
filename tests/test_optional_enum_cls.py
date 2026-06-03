# pyright: reportPrivateUsage=false
"""Unit tests for ``sphinx_literalizer._optional_enum_cls``."""

import enum

from literalizer._language import LanguageCls
from literalizer.languages import Python

from sphinx_literalizer import _optional_enum_cls


def test_optional_enum_cls_returns_empty_when_attribute_missing() -> None:
    """``_optional_enum_cls`` returns an empty iterable for unknown
    names.
    """
    assert list(_optional_enum_cls(cls=Python, name="NoSuchEnum")) == []


def test_optional_enum_cls_walks_mro() -> None:
    """``_optional_enum_cls`` finds enums defined on base classes."""

    class _Base(metaclass=LanguageCls):
        """Base language stub with an enum on the class dict."""

        class TargetEnum(enum.Enum):
            """Enum defined on the base class."""

            A = "a"

    class _Child(_Base):
        """Child language stub without its own ``TargetEnum``."""

    enum_cls = _optional_enum_cls(cls=_Child, name="TargetEnum")
    assert enum_cls is _Base.TargetEnum
    assert enum_cls.A.value == "a"
