"""Système de thèmes Material Design + échelle de polices ajustable.

Usage:
    from common.theme import theme_manager

    theme_manager.set_active('material_light')
    theme_manager.apply(app)  # QApplication.setStyleSheet(...)

    # Pour une taille dynamique :
    from common.theme import theme_manager as tm
    btn.setFont(QFont('Segoe UI', tm.font_size(13)))
"""

from dataclasses import dataclass, field
from typing import Optional
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication


@dataclass
class Palette:
    primary: str = '#1565C0'
    primary_light: str = '#E3F2FD'
    primary_dark: str = '#0D47A1'
    on_primary: str = '#FFFFFF'
    surface: str = '#FFFFFF'
    background: str = '#F5F5F5'
    text_strong: str = '#212121'
    text_soft: str = '#757575'
    text_secondary: str = '#555555'
    text_on_primary: str = '#FFFFFF'
    active: str = '#43A047'
    selection: str = '#1565C0'
    border: str = '#E0E0E0'
    border_light: str = '#EEEEEE'
    header_bg: str = '#1A237E'
    header_text: str = '#FFFFFF'
    error: str = '#D32F2F'
    danger: str = '#D32F2F'
    accent: str = '#9B59B6'
    success: str = '#2ECC71'
    inactive: str = '#BDBDBD'
    button_primary: str = '#2980B9'
    button_danger: str = '#C0392B'
    button_accent: str = '#8E44AD'
    button_success: str = '#27AE60'


@dataclass
class FontScale:
    base: int = 11        # texte grille, labels
    small: int = 11       # natures, critères
    title: int = 11       # titres de section
    header: int = 15      # nom du prof
    button: int = 11      # boutons
    multiplier: float = 1.0


@dataclass
class Theme:
    name: str
    label: str
    palette: Palette = field(default_factory=Palette)
    fonts: FontScale = field(default_factory=FontScale)


def _hex(r: int, g: int, b: int) -> str:
    return f'#{r:02x}{g:02x}{b:02x}'


_BUILTIN_THEMES: dict[str, Theme] = {}


def _init_themes():
    if _BUILTIN_THEMES:
        return

    # Default — proche de l'existant
    _BUILTIN_THEMES['default'] = Theme(
        name='default',
        label='Défaut',
        palette=Palette(
            primary='#2980b9',
            primary_light='#D6EAF8',
            primary_dark='#1F618D',
            surface='#FFFFFF',
            background='#f5f6fa',
            text_strong='#2c3e50',
            text_soft='#7f8c8d',
            text_secondary='#555555',
            active='#27ae60',
            selection='#2980b9',
            border='#dcdde1',
            border_light='#ecf0f1',
            header_bg='#2c3e50',
            error='#c0392b',
            danger='#c0392b',
            accent='#9b59b6',
            success='#2ecc71',
            inactive='#bdc3c7',
            button_primary='#2980b9',
            button_danger='#c0392b',
            button_accent='#8e44ad',
            button_success='#27ae60',
        ),
        fonts=FontScale(base=13, small=11, title=15, header=18, button=12),
    )

    # Material Light — recommandé par défaut
    _BUILTIN_THEMES['material_light'] = Theme(
        name='material_light',
        label='Material Light',
        palette=Palette(
            primary='#1565C0',
            primary_light='#E3F2FD',
            primary_dark='#0D47A1',
            surface='#FFFFFF',
            background='#F5F5F5',
            text_strong='#212121',
            text_soft='#757575',
            text_secondary='#555555',
            active='#43A047',
            selection='#1565C0',
            border='#E0E0E0',
            border_light='#EEEEEE',
            header_bg='#1565C0',
            inactive='#BDBDBD',
            error='#D32F2F',
            danger='#D32F2F',
            accent='#9B59B6',
            success='#2ECC71',
            button_primary='#1976D2',
            button_danger='#D32F2F',
            button_accent='#8E44AD',
            button_success='#388E3C',
        ),
        fonts=FontScale(base=13, small=11, title=15, header=18, button=12),
    )

    # Material Dark
    _BUILTIN_THEMES['material_dark'] = Theme(
        name='material_dark',
        label='Material Dark',
        palette=Palette(
            primary='#90CAF9',
            primary_light='#1E3A5F',
            primary_dark='#42A5F5',
            surface='#2D2D2D',
            background='#1E1E1E',
            text_strong='#E0E0E0',
            text_soft='#9E9E9E',
            text_secondary='#AAAAAA',
            active='#81C784',
            selection='#90CAF9',
            border='#424242',
            border_light='#333333',
            header_bg='#0D47A1',
            text_on_primary='#000000',
            on_primary='#000000',
            error='#EF5350',
            danger='#EF5350',
            accent='#CE93D8',
            success='#81C784',
            inactive='#616161',
            button_primary='#1565C0',
            button_danger='#C62828',
            button_accent='#6A1B9A',
            button_success='#2E7D32',
        ),
        fonts=FontScale(base=13, small=11, title=15, header=18, button=12),
    )

    # Nature — vert apaisant
    _BUILTIN_THEMES['nature'] = Theme(
        name='nature',
        label='Nature',
        palette=Palette(
            primary='#2E7D32',
            primary_light='#E8F5E9',
            primary_dark='#1B5E20',
            surface='#FFF8E1',
            background='#F1F8E9',
            text_strong='#33691E',
            text_soft='#689F38',
            text_secondary='#558B2F',
            active='#558B2F',
            selection='#2E7D32',
            border='#C5E1A5',
            border_light='#DCEDC8',
            header_bg='#1B5E20',
            error='#C62828',
            danger='#C62828',
            accent='#6A1B9A',
            success='#558B2F',
            inactive='#A5D6A7',
            button_primary='#2E7D32',
            button_danger='#C62828',
            button_accent='#7B1FA2',
            button_success='#33691E',
        ),
        fonts=FontScale(base=13, small=11, title=15, header=18, button=12),
    )


class ThemeManager:
    """Singleton global gérant le thème actif et le font scaling."""

    def __init__(self):
        _init_themes()
        self._themes = _BUILTIN_THEMES
        self._active: str = 'material_light'
        self._theme: Theme = self._themes[self._active]
        self._app: Optional[QApplication] = None

    @property
    def theme(self) -> Theme:
        return self._theme

    def names(self) -> list[tuple[str, str]]:
        return [(k, v.label) for k, v in self._themes.items()]

    def set_active(self, name: str) -> bool:
        if name in self._themes:
            self._active = name
            self._theme = self._themes[name]
            self._reapply()
            return True
        return False

    def get(self, name: str) -> Theme:
        return self._themes.get(name, self._theme)

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
        self._reapply()

    def _reapply(self):
        if self._app is not None:
            self._app.setStyleSheet(self._generate_qss())

    @staticmethod
    def _btn_toggle_qss(p: Palette, checked: bool, height: int = 22) -> str:
        if checked:
            return (
                f"QPushButton {{ background: {p.primary}; color: {p.on_primary}; "
                f"border: none; border-radius: {height // 2}px; "
                f"font-size: 12px; font-weight: bold; padding: 1px 8px; }}"
                f"QPushButton:hover {{ background: {p.primary_dark}; }}"
            )
        return (
            f"QPushButton {{ background: transparent; color: {p.text_soft}; "
            f"border: 1px solid {p.border}; border-radius: {height // 2}px; "
            f"font-size: 12px; padding: 1px 8px; }}"
            f"QPushButton:hover {{ background: {p.primary_light}; }}"
        )

    @staticmethod
    def _btn_crit_qss(p: Palette, checked: bool) -> str:
        if checked:
            return (
                f"QPushButton {{ background: {p.primary}; color: {p.on_primary}; "
                f"border: none; border-radius: 3px; font-size: 11px; "
                f"font-weight: bold; padding: 2px 6px; }}"
                f"QPushButton:hover {{ background: {p.primary_dark}; }}"
            )
        return (
            f"QPushButton {{ background: transparent; color: {p.inactive}; "
            f"border: 1px solid {p.border}; border-radius: 3px; "
            f"font-size: 11px; padding: 2px 6px; }}"
            f"QPushButton:hover {{ background: {p.primary_light}; }}"
        )

    def btn_toggle_style(self, checked: bool, height: int = 22) -> str:
        return self._btn_toggle_qss(self._theme.palette, checked, height)

    def btn_crit_style(self, checked: bool) -> str:
        return self._btn_crit_qss(self._theme.palette, checked)

    def _generate_qss(self) -> str:
        p = self._theme.palette
        f = self._theme.fonts
        fs = self.font_size
        return f"""
            /* Fond général */
            QMainWindow, QWidget#central {{
                background: {p.background};
                color: {p.text_strong};
            }}

            /* Header */
            QFrame#header {{
                background: {p.header_bg};
                color: {p.header_text};
                border-radius: 6px;
            }}
            QFrame#header QLabel {{
                color: {p.header_text};
            }}

            /* Panneaux */
            QFrame.panel {{
                background: {p.surface};
                border: 1px solid {p.border};
                border-radius: 6px;
            }}

            /* Labels */
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

            /* ComboBox */
            QComboBox {{
                background: {p.surface};
                border: 1px solid {p.border};
                border-radius: 4px;
                padding: 2px 4px;
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

            /* Grille */
            QTableWidget {{
                background: {p.surface};
                gridline-color: {p.border};
                font-size: {fs(f.base)}px;
                border: 1px solid {p.border};
                border-radius: 6px;
                color: {p.text_strong};
            }}
            QTableWidget::item {{
                padding: 3px 6px;
            }}
            QHeaderView::section {{
                background: {p.primary_light};
                color: {p.primary};
                border: 1px solid {p.border};
                padding: 4px 6px;
                font-size: {fs(f.small)}px;
                font-weight: bold;
            }}

            /* ScrollArea */
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: {p.background};
                width: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {p.inactive};
                border-radius: 3px;
                min-height: 20px;
            }}

            /* StatusBar */
            QStatusBar {{
                background: {p.surface};
                border-top: 1px solid {p.border};
                color: {p.text_soft};
                font-size: {fs(f.small)}px;
            }}

            /* Separator */
            QFrame#sep {{
                border: none;
                border-top: 1px solid {p.border};
            }}
        """


theme_manager = ThemeManager()
