"""Système de thèmes — s'appuie sur larccommon.theme pour Palette/FontScale/DesignTokens.

Usage:
    from common.theme import theme_manager

    theme_manager.set_active('material_light')
    theme_manager.bind(app)
    theme_manager.btn_toggle_style(checked)
"""

from dataclasses import dataclass, field
from typing import Optional
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from phibuilder import PhiBuilder
from larccommon.theme import (
    Palette as BasePalette,
    FontScale,
    DesignTokens,
)


@dataclass
class Palette(BasePalette):
    """Étend BasePalette avec les champs spécifiques eLarcProfPy."""
    primary_light: str = '#E3F2FD'
    primary_dark: str = '#0D47A1'
    selection: str = '#1565C0'


@dataclass
class Theme:
    name: str
    label: str
    palette: Palette = field(default_factory=Palette)
    fonts: FontScale = field(default_factory=FontScale)
    design: DesignTokens = field(default_factory=DesignTokens)


_BUILTIN_THEMES: dict[str, Theme] = {}
_SEED_MAP: dict[str, str] = {}
_IS_DARK_MAP: dict[str, bool] = {}


def _init_themes():
    if _BUILTIN_THEMES:
        return

    _SEED_MAP['default'] = '#2980b9'
    _IS_DARK_MAP['default'] = False
    _BUILTIN_THEMES['default'] = Theme('default', 'Défaut', Palette(
        primary='#2980b9', primary_light='#D6EAF8', primary_dark='#1F618D',
        on_primary='#FFFFFF', surface='#FFFFFF', background='#f5f6fa',
        text_strong='#2c3e50', text_soft='#7f8c8d', text_secondary='#555555',
        active='#27ae60', selection='#2980b9', header_bg='#2c3e50',
        border='#dcdde1', border_light='#ecf0f1',
        error='#c0392b', danger='#c0392b', accent='#9b59b6',
        success='#2ecc71', inactive='#bdc3c7',
        button_primary='#2980b9', button_danger='#c0392b',
        button_accent='#8e44ad', button_success='#27ae60',
    ), fonts=FontScale(base=13, small=11, title=15, header=18, button=12))

    _SEED_MAP['material_light'] = '#1565C0'
    _IS_DARK_MAP['material_light'] = False
    _BUILTIN_THEMES['material_light'] = Theme('material_light', 'Material Light', Palette(
        primary='#1565C0', primary_light='#E3F2FD', primary_dark='#0D47A1',
        on_primary='#FFFFFF', surface='#FFFFFF', background='#F5F5F5',
        text_strong='#212121', text_soft='#757575', text_secondary='#555555',
        active='#43A047', selection='#1565C0', header_bg='#1565C0',
        border='#E0E0E0', border_light='#EEEEEE',
        inactive='#BDBDBD', error='#D32F2F', danger='#D32F2F',
        accent='#9B59B6', success='#2ECC71',
        button_primary='#1976D2', button_danger='#D32F2F',
        button_accent='#8E44AD', button_success='#388E3C',
    ), fonts=FontScale(base=13, small=11, title=15, header=18, button=12))

    _SEED_MAP['material_dark'] = '#212121'
    _IS_DARK_MAP['material_dark'] = True
    _BUILTIN_THEMES['material_dark'] = Theme('material_dark', 'Material Dark', Palette(
        primary='#90CAF9', primary_light='#1E3A5F', primary_dark='#42A5F5',
        surface='#2D2D2D', background='#1E1E1E',
        text_strong='#E0E0E0', text_soft='#9E9E9E', text_secondary='#AAAAAA',
        active='#81C784', selection='#90CAF9', header_bg='#0D47A1',
        border='#424242', border_light='#333333',
        on_primary='#000000', error='#EF5350', danger='#EF5350',
        accent='#CE93D8', success='#81C784', inactive='#616161',
        button_primary='#1565C0', button_danger='#C62828',
        button_accent='#6A1B9A', button_success='#2E7D32',
    ), fonts=FontScale(base=13, small=11, title=15, header=18, button=12))

    _SEED_MAP['nature'] = '#2E7D32'
    _IS_DARK_MAP['nature'] = False
    _BUILTIN_THEMES['nature'] = Theme('nature', 'Nature', Palette(
        primary='#2E7D32', primary_light='#E8F5E9', primary_dark='#1B5E20',
        surface='#FFF8E1', background='#F1F8E9',
        text_strong='#33691E', text_soft='#689F38', text_secondary='#558B2F',
        active='#558B2F', selection='#2E7D32', header_bg='#1B5E20',
        border='#C5E1A5', border_light='#DCEDC8',
        error='#C62828', danger='#C62828', accent='#6A1B9A',
        success='#558B2F', inactive='#A5D6A7',
        button_primary='#2E7D32', button_danger='#C62828',
        button_accent='#7B1FA2', button_success='#33691E',
    ), fonts=FontScale(base=13, small=11, title=15, header=18, button=12))


class ThemeManager:
    def __init__(self):
        _init_themes()
        self._themes = _BUILTIN_THEMES
        self._active: str = 'material_light'
        self._theme: Theme = self._themes[self._active]
        self._app: Optional[QApplication] = None
        self._phibuilder: Optional[PhiBuilder] = None

    @property
    def theme(self) -> Theme:
        return self._theme

    @property
    def palette(self) -> Palette:
        return self._theme.palette

    @property
    def design(self) -> DesignTokens:
        return self._theme.design

    def names(self) -> list[tuple[str, str]]:
        return [(k, v.label) for k, v in self._themes.items()]

    def get(self, name: str) -> Theme:
        return self._themes.get(name, self._theme)

    def set_active(self, name: str) -> bool:
        if name in self._themes:
            self._active = name
            self._theme = self._themes[name]
            self._sync_phibuilder()
            self._reapply()
            return True
        return False

    def set_font_multiplier(self, m: float) -> None:
        m = max(0.5, min(2.0, m))
        self._theme.fonts.multiplier = m
        self._reapply()

    def font_multiplier(self) -> float:
        return self._theme.fonts.multiplier

    def font_size(self, base: int) -> int:
        return max(7, int(base * self._theme.fonts.multiplier))

    def font(self, base: int, weight=QFont.Normal, family='Segoe UI') -> QFont:
        return QFont(family, self.font_size(base), weight)

    def bind(self, app: QApplication) -> None:
        self._app = app
        self._phibuilder = PhiBuilder(
            seed_color=_SEED_MAP.get(self._active, '#1565C0'),
            is_dark=_IS_DARK_MAP.get(self._active, False),
        )
        self._reapply()

    def _sync_phibuilder(self):
        if self._phibuilder is None:
            return
        self._phibuilder.set_seed_color(_SEED_MAP.get(self._active, '#1565C0'))
        self._phibuilder.set_dark_mode(_IS_DARK_MAP.get(self._active, False))

    def _reapply(self):
        if self._app is None:
            return
        combined = ''
        if self._phibuilder is not None:
            combined += self._phibuilder.qss + '\n'
        combined += self._generate_qss()
        self._app.setStyleSheet(combined)

    def _btn_toggle_qss(self, checked: bool, height: int = 22) -> str:
        p = self._theme.palette
        fs = self.font_size
        if checked:
            return (
                f"QPushButton {{ background: {p.primary}; color: {p.on_primary}; "
                f"border: none; border-radius: {height // 2}px; "
                f"font-size: {fs(12)}px; font-weight: bold; padding: 2px 8px; }}"
                f"QPushButton:hover {{ background: {p.primary_dark}; }}"
            )
        return (
            f"QPushButton {{ background: transparent; color: {p.text_soft}; "
            f"border: 1px solid {p.border}; border-radius: {height // 2}px; "
            f"font-size: {fs(12)}px; padding: 2px 8px; }}"
            f"QPushButton:hover {{ background: {p.primary_light}; }}"
        )

    def _btn_crit_qss(self, checked: bool) -> str:
        p = self._theme.palette
        fs = self.font_size
        if checked:
            return (
                f"QPushButton {{ background: {p.primary}; color: {p.on_primary}; "
                f"border: none; border-radius: 3px; font-size: {fs(11)}px; "
                f"font-weight: bold; padding: 2px 5px; }}"
                f"QPushButton:hover {{ background: {p.primary_dark}; }}"
            )
        return (
            f"QPushButton {{ background: transparent; color: {p.inactive}; "
            f"border: 1px solid {p.border}; border-radius: 3px; "
            f"font-size: {fs(11)}px; padding: 2px 5px; }}"
            f"QPushButton:hover {{ background: {p.primary_light}; }}"
        )

    def btn_toggle_style(self, checked: bool, height: int = 22) -> str:
        return self._btn_toggle_qss(checked, height)

    def btn_crit_style(self, checked: bool) -> str:
        return self._btn_crit_qss(checked)

    def _generate_qss(self) -> str:
        p = self._theme.palette
        d = self._theme.design
        f = self._theme.fonts
        fs = self.font_size
        return f"""
            QMainWindow, QWidget#central {{
                background: {p.background};
                color: {p.text_strong};
            }}
            QFrame#header {{
                background: {p.header_bg};
                color: {p.header_text};
                border-radius: {d.radius_lg}px;
            }}
            QFrame#header QLabel {{
                color: {p.header_text};
            }}
            QFrame.panel {{
                background: {p.surface};
                border: 1px solid {p.border};
                border-radius: {d.radius_lg}px;
            }}
            QLabel {{
                color: {p.text_strong};
            }}
            QLabel.soft {{
                color: {p.text_soft};
                font-size: {fs(f.small)}px;
            }}
            QLabel.placeholder {{
                color: {p.inactive};
                font-style: italic;
            }}
            QComboBox {{
                background: {p.surface};
                border: 1px solid {p.border};
                border-radius: {d.radius}px;
                padding: {d.spacing//3}px {d.spacing}px;
                font-size: {fs(f.small)}px;
                color: {p.text_strong};
            }}
            QComboBox:hover {{
                border-color: {p.primary};
            }}
            QComboBox QAbstractItemView {{
                background: {p.surface};
                selection-background-color: {p.primary_light};
                selection-color: {p.text_strong};
            }}
            QTableWidget {{
                background: {p.surface};
                gridline-color: {p.border};
                font-size: {fs(f.base)}px;
                border: 1px solid {p.border};
                border-radius: {d.radius_lg}px;
                color: {p.text_strong};
            }}
            QTableWidget::item {{
                padding: {d.spacing//2}px {d.spacing}px;
            }}
            QHeaderView::section {{
                background: {p.primary_light};
                color: {p.primary};
                border: 1px solid {p.border};
                padding: {d.spacing}px {d.spacing}px;
                font-size: {fs(f.small)}px;
                font-weight: bold;
            }}
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: {p.background};
                width: {d.spacing}px;
                border-radius: {d.spacing//2}px;
            }}
            QScrollBar::handle:vertical {{
                background: {p.inactive};
                border-radius: {d.spacing//2}px;
                min-height: 21px;
            }}
            QStatusBar {{
                background: {p.surface};
                border-top: 1px solid {p.border};
                color: {p.text_soft};
                font-size: {fs(f.small)}px;
            }}
            QFrame#sep {{
                border: none;
                border-top: 1px solid {p.border};
            }}
        """


theme_manager = ThemeManager()
