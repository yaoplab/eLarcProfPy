"""Shim vers larccommon.theme — ajoute btn_toggle_style pour LarcProf."""

from larccommon.theme import (
    DesignTokens,
    FontScale,
    Palette,
    QssHelper,
    Theme,
    ThemeManager,
    theme_manager,
)


def btn_toggle_style(checked: bool, height: int = 22, radius: int = 4) -> str:
    """Style pour boutons toggle type OUI/NON (utilisé dans main_window)."""
    p = theme_manager.palette
    if checked:
        return (
            f"QPushButton {{ background: {p.primary}; color: {p.on_primary}; border: none; "
            f"border-radius: {radius}px; padding: 0 8px; height: {height}px; }}"
        )
    return (
        f"QPushButton {{ background: transparent; color: {p.text_strong}; "
        f"border: 1px solid {p.outline_variant}; border-radius: {radius}px; "
        f"padding: 0 8px; height: {height}px; }}"
        f"QPushButton:hover {{ background: {p.surface_variant}; }}"
    )


class ThemeManagerWrapper:
    """Wrapper compatible avec l'API LarcProf existante."""

    def __init__(self):
        self._original = theme_manager

    @property
    def palette(self):
        return self._original.palette

    @property
    def fonts(self):
        return self._original.fonts

    @property
    def design(self):
        return self._original.design

    @property
    def theme(self):
        return self._original.theme

    @property
    def phi_theme(self):
        return self._original.phi_theme

    @property
    def active_name(self):
        return self._original.active_name

    def set_active(self, name: str) -> bool:
        return self._original.set_active(name)

    def font_size(self, base: int) -> int:
        return self._original.font_size(base)

    def font(self, base: int, weight=QFont.Weight.Normal):
        return self._original.font(base, weight)

    def names(self):
        return self._original.names()

    def bind(self, app):
        self._original.bind(app)

    def btn_toggle_style(self, checked: bool, height: int = 22) -> str:
        return btn_toggle_style(checked, height)


theme_manager = ThemeManagerWrapper()
__all__ = [
    "theme_manager",
    "ThemeManager",
    "Theme",
    "Palette",
    "FontScale",
    "DesignTokens",
    "QssHelper",
    "btn_toggle_style",
]
