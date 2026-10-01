"""Compatibilita degli enum fra PyQt5/QGIS 3 e PyQt6/QGIS 4."""

from qgis.PyQt.QtCore import QMetaType, Qt, QVariant
from qgis.PyQt.QtWidgets import QAbstractItemView, QHeaderView


def _scoped(owner, legacy_name, scope_name):
    if hasattr(owner, legacy_name):
        return getattr(owner, legacy_name)
    return getattr(getattr(owner, scope_name), legacy_name)


WINDOW = _scoped(Qt, "Window", "WindowType")
WINDOW_MINIMIZE = _scoped(Qt, "WindowMinimizeButtonHint", "WindowType")
WINDOW_MAXIMIZE = _scoped(Qt, "WindowMaximizeButtonHint", "WindowType")
WINDOW_CLOSE = _scoped(Qt, "WindowCloseButtonHint", "WindowType")
NON_MODAL = _scoped(Qt, "NonModal", "WindowModality")
ALIGN_CENTER = _scoped(Qt, "AlignCenter", "AlignmentFlag")
NO_EDIT_TRIGGERS = _scoped(QAbstractItemView, "NoEditTriggers", "EditTrigger")
HEADER_STRETCH = _scoped(QHeaderView, "Stretch", "ResizeMode")
HEADER_CONTENTS = _scoped(QHeaderView, "ResizeToContents", "ResizeMode")


def _variant_type(legacy_name, qt6_name):
    """Tipo QgsField compatibile con QVariant (Qt5) e QMetaType (Qt6)."""
    if hasattr(QVariant, legacy_name):
        return getattr(QVariant, legacy_name)
    return getattr(QMetaType.Type, qt6_name)


FIELD_STRING = _variant_type("String", "QString")
FIELD_DOUBLE = _variant_type("Double", "Double")
FIELD_INT = _variant_type("Int", "Int")
