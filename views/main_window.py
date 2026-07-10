"""Fenêtre principale — Espace de travail du professeur.

Top bar (toujours visible) : matière-classe, formatives, sommatives, jugements.
Workspace (après sélection) : grille élèves × notes + barre actions.
"""
from __future__ import annotations

from functools import partial

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor, QAction, QKeySequence, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStatusBar,
    QStyle,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from larccommon.design_system import ds



from common.database import db
from common.session import session
from common.theme import theme_manager
from common.grid_config import pei_config
from views.eval_manager import EvalManagerWindow




class ColorItem(QTableWidgetItem):
    """QTableWidgetItem qui stocke une couleur de fond accessible via UserRole+3."""
    def __init__(self, text: str, bg: QColor | None = None):
        super().__init__(text)
        self._bg = bg

    def set_bg(self, bg: QColor | None):
        self._bg = bg

    def data(self, role: int):
        if role == Qt.UserRole + 3 and self._bg is not None:
            return self._bg
        return super().data(role)


class ColorDelegate(QStyledItemDelegate):
    """Delegate: fond depuis UserRole+3, texte centré par-dessus."""
    def paint(self, painter, option, index):
        self.initStyleOption(option, index)

        # Fond
        painter.save()
        custom_bg = index.data(Qt.UserRole + 3)
        if custom_bg:
            painter.fillRect(option.rect, custom_bg)
        else:
            painter.fillRect(option.rect, QColor(245, 245, 245))
        painter.restore()

        # Sélection
        if option.state & QStyle.State_Selected:
            painter.save()
            c = option.palette.highlight().color()
            c.setAlpha(80)
            painter.fillRect(option.rect, c)
            painter.restore()

        # Texte centré avec padding design system
        painter.save()
        painter.setFont(option.font)
        painter.setPen(option.palette.color(QPalette.Text))
        trect = option.rect.adjusted(8, 4, -8, -4)
        painter.drawText(trect, Qt.AlignCenter, option.text)
        painter.restore()


class ClipboardTable(QTableWidget):
    """QTableWidget avec support Ctrl+C / Ctrl+V (formats Excel)."""

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Copy):
            self._copy_selection()
            return
        if event.matches(QKeySequence.Paste):
            self._paste_clipboard()
            return
        super().keyPressEvent(event)

    def _copy_selection(self) -> None:
        rows = sorted(set(item.row() for item in self.selectedItems()))
        cols = sorted(set(item.column() for item in self.selectedItems()))
        if not rows or not cols:
            return
        col_range = range(cols[0], cols[-1] + 1)
        lines = []
        for r in rows:
            cells = []
            for c in col_range:
                it = self.item(r, c)
                cells.append(it.text() if it else '')
            lines.append('\t'.join(cells))
        QApplication.clipboard().setText('\n'.join(lines))

    def _paste_clipboard(self) -> None:
        text = QApplication.clipboard().text()
        if not text.strip():
            return
        lines = text.split('\n')
        rows_data = [line.split('\t') for line in lines if line.strip()]
        if not rows_data:
            return
        cur_row = self.currentRow()
        cur_col = self.currentColumn()
        parent = self.window()

        has_dp = getattr(parent, '_current_table', '').endswith('dp')
        max_val = 20 if has_dp else 8

        self.blockSignals(True)
        errors = []
        paste_count = 0
        for ri, row_cells in enumerate(rows_data):
            for ci, val in enumerate(row_cells):
                r = cur_row + ri
                c = cur_col + ci
                if r >= self.rowCount() or c >= self.columnCount():
                    continue
                if c == 0:
                    continue  # colonne 0 = élève, pas de collage
                val = val.strip()
                item = self.item(r, c)
                if item is None:
                    item = QTableWidgetItem()
                    self.setItem(r, c, item)
                item.setText(val)
                paste_count += 1

                if val:
                    try:
                        f = float(val)
                        if f < 0 or f > max_val:
                            errors.append(f"L{ri+1}C{ci+1} ({f}) hors {0}-{max_val}")
                    except ValueError:
                        pass

        self.blockSignals(False)

        from functools import partial
        for ri, row_cells in enumerate(rows_data):
            for ci in range(len(row_cells)):
                r = cur_row + ri
                c = cur_col + ci
                if r >= self.rowCount() or c >= self.columnCount():
                    continue
                QTimer.singleShot(0, partial(self._mark_dirty, r, c))

        if errors:
            QApplication.beep()
            parent.statusBar().showMessage(
                f"Collé — {paste_count} cellules, {len(errors)} hors plage: "
                f"{', '.join(errors[:5])}", 10000
            )
        else:
            parent.statusBar().showMessage(
                f"Collé — {paste_count} cellule(s)"
            )

    def _mark_dirty(self, row: int, col: int) -> None:
        parent = self.window()
        if not hasattr(parent, '_on_cell_changed'):
            return
        parent._on_cell_changed(row, col)


class MainWindow(QMainWindow):
    """Espace de travail du professeur."""

    @property
    def _STYLE(self) -> str:
        p = theme_manager.theme.palette
        return f"""
            QFrame#header {{
                background: {p.header_bg};
                color: {p.header_text};
                border-radius: 6px;
            }}
            QFrame#header QLabel {{ color: {p.header_text}; }}
            QFrame.panel {{
                background: {p.surface};
                border: 1px solid {p.border};
                border-radius: 6px;
            }}
            QLabel.placeholder {{
                color: {p.inactive};
                font-style: italic;
            }}
        """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        QApplication.setStyle('Fusion')
        self.setWindowTitle('LarcProf — College Notes')
        self.resize(1200, 800)
        self.setStyleSheet(self._STYLE)

        # Data cache
        self._items: list[dict] = []
        self._eleves_par_classe: dict[int, list[dict]] = {}
        self._cycle_par_classe: dict[int, str] = {}
        self._items_other: list[dict] = []
        self._manager_f: EvalManagerWindow | None = None
        self._manager_s: EvalManagerWindow | None = None
        self._grille: QTableWidget | None = None
        self._current_item: dict | None = None

        # État courant
        self._current_ts_id: int | None = None
        self._current_cycle: str = 'PEI'
        self._evals_f: list[dict] = []  # index_eval, label, nature, crit_a..d, is_active
        self._evals_s: list[dict] = []
        self._visible_f: set[int] = set()  # slots indices actuellement affichés dans la grille
        self._visible_s: set[int] = set()
        self._show_f_comment: bool = False
        self._show_s_comment: bool = False
        self._last_clicked_f: int | None = None  # dernier slot cliqué pour détail
        self._last_clicked_s: int | None = None
        self._show_jgt_comment: bool = False
        self._visible_crits: dict[str, bool] = {'a': True, 'b': True, 'c': True, 'd': True}
        self._name_format_prenom_first: bool = False  # True = "Prenom Nom"
        self._grille:         QTableWidget | None = None
        self._row_ids: dict[int, int] = {}  # student_id → learner table row id
        self._dirty_cells: dict[tuple[int, str], str] = {}  # (student_id, col_db_name) → new value
        self._current_table: str = ''
        self._current_col_names: list[str] = ['Élève']
        self._current_student_ids: list[int] = []

        # Widgets top bar (références pour mise à jour)
        self._top_bar: QWidget | None = None
        self._workspace_widget: QWidget | None = None
        self._fwidgets: dict = {}  # widgets section formatives
        self._swidgets: dict = {}  # widgets section sommatives
        self._jwidgets: dict = {}  # widgets section jugements

        self._setup_ui()
        self._load_combined_data()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)

        layout.addWidget(self._build_header())

        # Top bar (toujours visible) : 4 sections
        self._top_bar = self._build_top_bar()
        layout.addWidget(self._top_bar)

        # Workspace (grille + actions) — toujours en layout, vide si pas de sélection
        self._workspace_widget = QWidget()
        self._workspace_widget.setMinimumHeight(144)
        ws_layout = QVBoxLayout(self._workspace_widget)
        ws_layout.setContentsMargins(0, 0, 0, 0)
        ws_layout.setSpacing(3)
        ws_layout.addWidget(self._build_students_grid(), 1)
        ws_layout.addWidget(self._build_actions_bar())
        layout.addWidget(self._workspace_widget, 1)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage('Prêt')

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName('header')
        header.setMinimumHeight(55)
        h = QHBoxLayout(header)
        h.setContentsMargins(13, 8, 13, 8)

        prof_name = session.full_name or '—'
        annee = self._read_annee_scolaire()
        trim = session.active_term_label or '—'

        title_font = QFont('Segoe UI', theme_manager.font_size(14), QFont.Bold)
        meta_font = QFont('Segoe UI', theme_manager.font_size(11))

        prof_lbl = QLabel(prof_name)
        prof_lbl.setFont(title_font)
        annee_lbl = QLabel(f'Année  {annee}')
        annee_lbl.setFont(meta_font)
        trim_lbl = QLabel(f'Trimestre  {trim}')
        trim_lbl.setFont(meta_font)

        h.addWidget(prof_lbl)
        h.addStretch(1)
        h.addWidget(annee_lbl)
        h.addSpacing(21)
        h.addWidget(trim_lbl)

        h.addSpacing(13)

        # Bouton palette de thèmes
        palette_btn = QPushButton('🎨')
        palette_btn.setFixedSize(30, 30)
        palette_btn.setToolTip('Changer le thème')
        palette_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: 1px solid {theme_manager.theme.palette.header_text}; "
            f"border-radius: 13px; font-size: {theme_manager.font_size(14)}px; color: {theme_manager.theme.palette.header_text}; }}"
            f"QPushButton:hover {{ background: rgba(255,255,255,0.2); }}"
        )
        palette_menu = QMenu()
        for key, label in theme_manager.names():
            act = QAction(label, self)
            act.setData(key)
            act.triggered.connect(lambda checked=False, k=key: self._set_theme(k))
            palette_menu.addAction(act)
        palette_btn.setMenu(palette_menu)
        h.addWidget(palette_btn)

        # Bouton échelle de police
        font_btn = QPushButton('Aa')
        font_btn.setFixedSize(36, 30)
        font_btn.setToolTip('Taille du texte')
        font_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: 1px solid {theme_manager.theme.palette.header_text}; "
            f"border-radius: 13px; font-size: {theme_manager.font_size(11)}px; font-weight: bold; "
            f"color: {theme_manager.theme.palette.header_text}; }}"
            f"QPushButton:hover {{ background: rgba(255,255,255,0.2); }}"
        )
        font_menu = QMenu()
        for label, val in [('100%', 1.0), ('125%', 1.25), ('150%', 1.5)]:
            act = QAction(label, self)
            act.setData(val)
            act.triggered.connect(lambda checked=False, v=val: self._set_font_scale(v))
            font_menu.addAction(act)
        font_btn.setMenu(font_menu)
        h.addWidget(font_btn)

        return header

    def _set_theme(self, name: str):
        theme_manager.set_active(name)
        self.setStyleSheet(self._STYLE)
        self.statusBar().showMessage(f'Thème : {theme_manager.theme.label}')

    def _set_font_scale(self, mult: float):
        theme_manager.set_font_multiplier(mult)
        # Recharger l'UI complète pour appliquer les nouvelles tailles
        self._on_selection_changed()
        # Mettre à jour le header (polices + boutons)
        self._rebuild_header()
        self.statusBar().showMessage(
            f'Échelle : {int(mult * 100)}%'
        )

    def _rebuild_header(self):
        """Remplace le header pour actualiser les polices."""
        old = self.centralWidget().layout().takeAt(0)
        if old and old.widget():
            old.widget().deleteLater()
        new_header = self._build_header()
        self.centralWidget().layout().insertWidget(0, new_header)

    def _build_top_bar(self) -> QWidget:
        """Top bar 4 sections : matière-classe | formatives | sommatives | jugements."""
        container = QWidget()
        h = QHBoxLayout(container)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(3)

        # Section 1 : Matière-Classe
        h.addWidget(self._build_matiere_section(), 0)

        # Section 2 : Formatives
        f_panel = self._build_eval_section('F')
        self._fwidgets = f_panel['widgets']
        h.addWidget(f_panel['frame'], 1)

        # Section 3 : Sommatives
        s_panel = self._build_eval_section('S')
        self._swidgets = s_panel['widgets']
        h.addWidget(s_panel['frame'], 1)

        # Section 4 : Jugements
        j_panel = self._build_jugements_section()
        self._jwidgets = j_panel['widgets']
        h.addWidget(j_panel['frame'], 0)

        return container

    def _build_matiere_section(self) -> QFrame:
        """Section 1 : combo matière-classe + boutons critères."""
        f = QFrame()
        f.setProperty('class', 'panel')
        f.setFrameShape(QFrame.StyledPanel)
        f.setFixedWidth(233)
        v = QVBoxLayout(f)
        v.setContentsMargins(8, 5, 8, 5)
        v.setSpacing(3)

        lbl = QLabel('Matière - Classe')
        lbl.setFont(theme_manager.font(theme_manager.theme.fonts.title, QFont.Bold))
        lbl.setStyleSheet(f'color: {theme_manager.theme.palette.text_strong};')
        v.addWidget(lbl)

        self._items_combo = QComboBox()
        self._items_combo.setPlaceholderText('Choisir matière - classe')
        self._items_combo.setFont(theme_manager.font(theme_manager.theme.fonts.small))
        self._items_combo.currentIndexChanged.connect(self._on_item_selected)
        v.addWidget(self._items_combo)

        lbl_other = QLabel('Autre Matière - Classe')
        lbl_other.setFont(QFont('Segoe UI', theme_manager.font_size(9), QFont.Bold))
        lbl_other.setStyleSheet(f'color: {theme_manager.theme.palette.text_soft};')
        v.addWidget(lbl_other)

        self._items_other_combo = QComboBox()
        self._items_other_combo.setPlaceholderText('Choisir autre matière - classe')
        self._items_other_combo.setFont(theme_manager.font(theme_manager.theme.fonts.small))
        self._items_other_combo.setStyleSheet(
            f"background: {theme_manager.theme.palette.primary_light};"
        )
        self._items_other_combo.currentIndexChanged.connect(self._on_other_item_selected)
        v.addWidget(self._items_other_combo)

        v.addSpacing(5)

        v.addStretch()
        return f

    @staticmethod
    def _btn_crit_style(checked: bool) -> str:
        return theme_manager.btn_crit_style(checked)

    def _build_eval_section(self, eval_type: str) -> dict:
        """Construit une section formatives (F) ou sommatives (S) du top bar."""
        is_f = eval_type == 'F'
        f = QFrame()
        f.setProperty('class', 'panel')
        f.setFrameShape(QFrame.StyledPanel)
        v = QVBoxLayout(f)
        v.setContentsMargins(8, 5, 8, 5)
        v.setSpacing(3)

        # Titre + Gérer
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel('Formatives' if is_f else 'Sommatives')
        lbl.setFont(theme_manager.font(theme_manager.theme.fonts.title, QFont.Bold))
        lbl.setStyleSheet(f'color: {theme_manager.theme.palette.text_strong};')
        title_row.addWidget(lbl)
        title_row.addStretch()
        gerer_btn = QPushButton('Gérer')
        gerer_btn.setFixedHeight(21)
        gerer_btn.setFont(theme_manager.font(theme_manager.theme.fonts.button, QFont.Bold))
        gerer_btn.setStyleSheet(
            f"QPushButton {{ background: {theme_manager.theme.palette.primary}; "
            f"color: {theme_manager.theme.palette.on_primary}; border: none; "
            f"border-radius: 13px; font-weight: bold; padding: 2px 13px; }}"
            f"QPushButton:hover {{ background: {theme_manager.theme.palette.primary_dark}; }}"
        )
        if is_f:
            gerer_btn.clicked.connect(self._open_manager_f)
        else:
            gerer_btn.clicked.connect(self._open_manager_s)
        title_row.addWidget(gerer_btn)
        v.addLayout(title_row)

        # Zone scrollable des slots actifs
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMaximumHeight(144)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: transparent; }}")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        slot_layout = QVBoxLayout(scroll_content)
        slot_layout.setContentsMargins(0, 0, 0, 0)
        slot_layout.setSpacing(3)

        scroll.setWidget(scroll_content)
        v.addWidget(scroll, 1)

        # Boutons Toute / Aucune / Commentaire
        btn_row = QHBoxLayout()
        btn_row.setSpacing(3)
        tout_btn = QPushButton('Toute')
        tout_btn.setCheckable(True)
        tout_btn.setFixedHeight(21)
        tout_btn.setStyleSheet(self._btn_toggle_style(False))
        tout_btn.clicked.connect(partial(self._on_toggle_all, eval_type))
        btn_row.addWidget(tout_btn)

        aucune_btn = QPushButton('Aucune')
        aucune_btn.setCheckable(True)
        aucune_btn.setFixedHeight(21)
        aucune_btn.setStyleSheet(self._btn_toggle_style(False))
        aucune_btn.clicked.connect(partial(self._on_toggle_none, eval_type))
        btn_row.addWidget(aucune_btn)

        comm_btn = QPushButton('Commentaire')
        comm_btn.setCheckable(True)
        comm_btn.setFixedHeight(21)
        comm_btn.setStyleSheet(self._btn_toggle_style(False))
        comm_btn.clicked.connect(partial(self._on_toggle_comment, eval_type))
        btn_row.addWidget(comm_btn)

        v.addLayout(btn_row)

        return {
            'frame': f,
            'widgets': {
                'scroll_content': scroll_content,
                'tout_btn': tout_btn,
                'aucune_btn': aucune_btn,
                'comm_btn': comm_btn,
                'slot_rows': {},  # index -> QFrame
            }
        }

    def _build_jugements_section(self) -> dict:
        """Section 4 : 3 boutons + légende critères."""
        f = QFrame()
        f.setProperty('class', 'panel')
        f.setFrameShape(QFrame.StyledPanel)
        f.setFixedWidth(144)
        v = QVBoxLayout(f)
        v.setContentsMargins(8, 5, 8, 5)
        v.setSpacing(3)

        lbl = QLabel('Jugements')
        lbl.setFont(theme_manager.font(theme_manager.theme.fonts.title, QFont.Bold))
        lbl.setStyleSheet(f'color: {theme_manager.theme.palette.text_strong};')
        v.addWidget(lbl)

        jgt_btn = QPushButton('Jugement')
        jgt_btn.setCheckable(True)
        jgt_btn.setFixedHeight(21)
        jgt_btn.setFont(theme_manager.font(theme_manager.theme.fonts.button))
        jgt_btn.setStyleSheet(self._btn_toggle_style(True))
        jgt_btn.clicked.connect(self._on_jgt_toggle)
        v.addWidget(jgt_btn)

        note_btn = QPushButton('Note sur 7')
        note_btn.setCheckable(True)
        note_btn.setFixedHeight(21)
        note_btn.setFont(theme_manager.font(theme_manager.theme.fonts.button))
        note_btn.setStyleSheet(self._btn_toggle_style(True))
        note_btn.clicked.connect(self._on_jgt_note_toggle)
        v.addWidget(note_btn)

        comm_btn = QPushButton('Commentaire')
        comm_btn.setCheckable(True)
        comm_btn.setFixedHeight(21)
        comm_btn.setFont(theme_manager.font(theme_manager.theme.fonts.button))
        comm_btn.setStyleSheet(self._btn_toggle_style(False))
        comm_btn.clicked.connect(self._on_jgt_comment_toggle)
        v.addWidget(comm_btn)

        v.addSpacing(3)

        sep = QFrame()
        sep.setObjectName('sep')
        sep.setFrameShape(QFrame.HLine)
        v.addWidget(sep)

        self._crit_btns = {}
        for letter in ('a', 'b', 'c', 'd'):
            btn = QPushButton(f'Critère {letter.upper()}')
            btn.setCheckable(True)
            btn.setChecked(self._visible_crits[letter])
            btn.setFixedHeight(21)
            btn.setFont(theme_manager.font(theme_manager.theme.fonts.small))
            btn.setStyleSheet(self._btn_crit_style(True))
            btn.clicked.connect(partial(self._on_toggle_crit, letter))
            v.addWidget(btn)
            self._crit_btns[letter] = btn

        v.addStretch()
        return {
            'frame': f,
            'widgets': {
                'jgt_btn': jgt_btn,
                'note_btn': note_btn,
                'comm_btn': comm_btn,
            }
        }

    @staticmethod
    def _btn_toggle_style(checked: bool) -> str:
        return theme_manager.btn_toggle_style(checked, height=22)

    def _build_students_grid(self) -> QWidget:
        container = QWidget()
        h = QHBoxLayout(container)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        # Grille unique — colonne 0 = élève, colonnes 1..N = notes
        self._grille = ClipboardTable()
        self._grille.setSelectionBehavior(QTableWidget.SelectItems)
        self._grille.setSelectionMode(QTableWidget.ContiguousSelection)
        self._grille.setEditTriggers(
            QTableWidget.SelectedClicked | QTableWidget.EditKeyPressed | QTableWidget.AnyKeyPressed
        )
        self._grille.setSortingEnabled(True)
        self._grille.verticalHeader().setVisible(False)
        self._grille.horizontalHeader().sectionClicked.connect(self._on_header_section_clicked)
        self._grille.setItemDelegate(ColorDelegate())

        h.addWidget(self._grille, 1)

        return container

    def _build_actions_bar(self) -> QWidget:
        bar = QFrame()
        h = QHBoxLayout(bar)
        h.setContentsMargins(0, 0, 0, 0)
        h.addStretch(1)
        online = db.is_server_connected
        self._sync_btn = QPushButton('Synchroniser' if online else 'Enregistrer')
        self._sync_btn.setToolTip(
            'Synchronise avec le serveur' if online else 'Enregistre les modifications en local')
        self._sync_btn.clicked.connect(self._on_sync)
        self._save_btn = QPushButton('Enregistrer et quitter')
        self._save_btn.setToolTip('Enregistre les modifications et quitte'
                                  + (' (synchronise avant)' if online else ' (hors ligne)'))
        self._save_btn.clicked.connect(self._on_save_and_quit)
        h.addWidget(self._sync_btn)
        h.addWidget(self._save_btn)
        return bar

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _on_sync(self) -> None:
        """Synchronise avec le serveur, ou sauvegarde locale si hors ligne."""
        saved = self._save_grid_edits()
        from common.sync import sync
        from common.database import db as _db
        if not _db.is_server_connected:
            self.statusBar().showMessage(f'{saved} modification(s) enregistrée(s) en local')
            return
        self.statusBar().showMessage('Synchronisation en cours...')
        QApplication.processEvents()
        try:
            report = sync.pull_push()
            if report.has_errors:
                self.statusBar().showMessage(f'Synchro terminée avec erreurs: {report.summary()}')
            elif report.has_conflicts:
                self.statusBar().showMessage(f'Synchro terminée avec conflits: {report.summary()}')
            else:
                self.statusBar().showMessage(f'Synchro terminée: {report.summary()}')
        except Exception as e:
            self.statusBar().showMessage(f'Erreur de synchronisation: {e}')

    def _on_save_and_quit(self) -> None:
        """Enregistre les notes, synchronise et quitte."""
        self._save_grid_edits()
        from common.sync import sync
        from common.database import db as _db
        if _db.is_server_connected:
            self.statusBar().showMessage('Synchronisation avant fermeture...')
            QApplication.processEvents()
            try:
                report = sync.pull_push()
                self.statusBar().showMessage(f'Synchro: {report.summary()}')
            except Exception as e:
                self.statusBar().showMessage(f'Erreur synchro: {e}')
        self.close()

    # ------------------------------------------------------------------
    # Data access
    # ------------------------------------------------------------------
    def _read_annee_scolaire(self) -> str:
        conn = db.local_conn
        if conn is None:
            return '—'
        row = conn.execute(
            'SELECT annee_scolaire FROM module_config WHERE id = 1'
        ).fetchone()
        return row[0] if row else '—'

    # ------------------------------------------------------------------
    # Combined data loader
    # ------------------------------------------------------------------
    def _load_combined_data(self) -> None:
        """Charge les items Matière-Classe et les élèves depuis SQLite."""
        conn = db.local_conn
        if conn is None:
            self.statusBar().showMessage('Aucune base locale disponible')
            return

        try:
            user_id = session.user_id
            term_id = session.active_term_id
        except Exception:
            self.statusBar().showMessage('Session non disponible')
            return

        if not user_id or not term_id:
            self.statusBar().showMessage('Session incomplète')
            return

        try:
            cur = conn.cursor()

            # 1. Items Matière-Classe (une seule requête)
            cur.execute("""
                SELECT cts.id AS termsubject_id,
                       ls.label AS matiere,
                       c.id AS class_id,
                       c.label AS classe,
                       c.fk_level_id
                FROM larcauth_classroom_termsubject cts
                JOIN larcauth_levelsubject ls ON ls.id = cts.fk_levelsubject_id
                JOIN larcauth_classroom c ON c.id = cts.fk_classroom_id
                WHERE cts.fk_teacher_id = ?
                  AND cts.fk_term_id = ?
                  AND cts.enabled = 1
                  AND c.enabled = 1
                ORDER BY ls.label, c.label
            """, (user_id, term_id))
            rows = cur.fetchall()

            self._items = []
            self._cycle_par_classe.clear()
            for r in rows:
                termsubject_id = r[0]
                matiere = r[1]
                class_id = r[2]
                classe = r[3]
                level_id = r[4]
                if class_id not in self._cycle_par_classe:
                    self._cycle_par_classe[class_id] = self._determine_cycle(conn, level_id)
                cycle = self._cycle_par_classe[class_id]
                self._items.append({
                    'termsubject_id': termsubject_id,
                    'matiere_label': matiere,
                    'class_id': class_id,
                    'class_label': classe,
                    'cycle': cycle,
                })

            # 1b. Items Autre Matière-Classe (termothersubject)
            cur.execute("""
                SELECT cto.id AS termothersubject_id,
                       cto.label AS matiere,
                       c.id AS class_id,
                       c.label AS classe
                FROM larcauth_classroom_termothersubject cto
                JOIN larcauth_classroom c ON c.id = cto.fk_classroom_id
                WHERE cto.fk_supervisor_id = ?
                  AND cto.fk_term_id = ?
                  AND cto.enabled = 1
                  AND c.enabled = 1
                ORDER BY cto.label, c.label
            """, (user_id, term_id))
            other_rows = cur.fetchall()

            self._items_other = []
            for r in other_rows:
                self._items_other.append({
                    'termothersubject_id': r[0],
                    'matiere_label': r[1],
                    'class_id': r[2],
                    'class_label': r[3],
                })

            # 2. Élèves par classe
            self._eleves_par_classe.clear()
            all_class_ids = {item['class_id'] for item in self._items}
            for class_id in all_class_ids:
                cur.execute("""
                    SELECT s.aecuser_ptr_id, u.last_name, u.first_name
                    FROM larcauth_student s
                    JOIN larcauth_aecuser u ON u.id = s.aecuser_ptr_id
                    WHERE s.s_classroom_id = ?
                      AND s.enabled = 1
                    ORDER BY u.last_name, u.first_name
                """, (class_id,))
                self._eleves_par_classe[class_id] = [
                    {'id': r[0], 'nom': r[1], 'prenom': r[2]} for r in cur.fetchall()
                ]

            # 3. Peupler le combo
            self._items_combo.blockSignals(True)
            self._items_combo.clear()
            self._items_combo.addItem('— Sélectionnez —', None)
            for item in self._items:
                label = f"{item['matiere_label']} - {item['class_label']}"
                self._items_combo.addItem(label, item['class_id'])
            self._items_combo.blockSignals(False)

            # 3b. Peupler le combo Autre Matière-Classe
            self._items_other_combo.blockSignals(True)
            self._items_other_combo.clear()
            self._items_other_combo.addItem('— Sélectionnez —', None)
            for item in self._items_other:
                label = f"{item['matiere_label']} - {item['class_label']}"
                self._items_other_combo.addItem(label, item['termothersubject_id'])
            self._items_other_combo.blockSignals(False)

            if len(self._items) == 1:
                self._items_combo.setCurrentIndex(1)

            n_elv = sum(len(v) for v in self._eleves_par_classe.values())
            self.statusBar().showMessage(
                f'{len(self._items)} matière(s)-classe(s) · {n_elv} élève(s)'
            )

        except Exception as e:
            self.statusBar().showMessage(f'Erreur chargement données : {e}')

    def _determine_cycle(self, conn, level_id: int) -> str:
        """Retourne 'PEI' ou 'DP' selon le programme du niveau."""
        try:
            row = conn.execute("""
                SELECT p.sigle
                FROM larcauth_program p
                JOIN larcauth_level l ON l.fk_program_id = p.id
                WHERE l.id = ?
            """, (level_id,)).fetchone()
            if row:
                sigle = row[0].upper()
                if sigle in ('DP', 'IBDP', 'DIPLOMA'):
                    return 'DP'
            return 'PEI'
        except Exception:
            return 'PEI'

    def _on_item_selected(self, idx: int) -> None:
        """Item Matière-Classe sélectionné → charge évaluations + grille."""
        class_id = self._items_combo.itemData(idx) if idx >= 0 else None
        if class_id is None:
            self._clear_top_bar()
            self._clear_grille()
            self.statusBar().showMessage(
                f'{len(self._items)} matière(s)-classe(s) · sélectionnez un item'
            )
            return

        item = None
        for i in self._items:
            if i['class_id'] == class_id:
                item = i
                break
        if item is None:
            self._clear_grille()
            return

        ts_id = item['termsubject_id']
        cycle = item['cycle']
        eleves = self._eleves_par_classe.get(class_id, [])
        label = f"{item['matiere_label']} - {item['class_label']}"

        self._current_ts_id = ts_id
        self._current_cycle = cycle
        self._current_item = item

        self._load_evaluations_from_db(ts_id)
        # Auto-sélectionner le premier slot actif de chaque type
        self._visible_f.clear()
        for e in self._evals_f:
            if e['is_active']:
                self._visible_f.add(e['index'])
                self._last_clicked_f = e['index']
                break
        self._visible_s.clear()
        for e in self._evals_s:
            if e['is_active']:
                self._visible_s.add(e['index'])
                self._last_clicked_s = e['index']
                break
        self._update_top_bar()

        self._fill_grille(item, cycle, eleves)
        self.statusBar().showMessage(
            f'{label} · {cycle} · {len(eleves)} élève(s)'
        )

    def _load_evaluations_from_db(self, ts_id: int):
        """Charge les évaluations F et S depuis SQLite."""
        conn = db.local_conn
        if conn is None:
            return
        try:
            self._evals_f = []
            self._evals_s = []
            for eval_type in ('F', 'S'):
                rows = conn.execute("""
                    SELECT id, index_eval, label, nature, source,
                           crit_a, crit_b, crit_c, crit_d
                    FROM larcauth_evaluation
                    WHERE fk_classroom_termsubject_id = ?
                      AND type_evaluation = ?
                      AND CAST(index_eval AS INTEGER) BETWEEN 1 AND 12
                    ORDER BY CAST(index_eval AS INTEGER)
                """, (str(ts_id), eval_type)).fetchall()
                evals_list = []
                for r in rows:
                    crits_active = any((r[i] or '0') == '1' for i in (5, 6, 7, 8))
                    evals_list.append({
                        'id': r[0],
                        'index': int(r[1]),
                        'label': r[2] or '',
                        'nature': r[3] or '',
                        'source': r[4] or '',
                        'crit_a': r[5] or '0',
                        'crit_b': r[6] or '0',
                        'crit_c': r[7] or '0',
                        'crit_d': r[8] or '0',
                        'is_active': crits_active,
                    })
                if eval_type == 'F':
                    self._evals_f = evals_list
                else:
                    self._evals_s = evals_list
        except Exception as e:
            print(f"Erreur chargement évaluations: {e}")

    def _clear_top_bar(self):
        """Vide les détails du top bar quand aucune matière-classe sélectionnée."""
        self._last_clicked_f = None
        self._last_clicked_s = None
        for widgets in (self._fwidgets, self._swidgets):
            layout = widgets['scroll_content'].layout()
            if layout:
                while layout.count():
                    item = layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()

    def _update_top_bar(self):
        """Met à jour les icônes et détails du top bar avec les données chargées."""
        self._update_icons('F', self._evals_f, self._fwidgets)
        self._update_icons('S', self._evals_s, self._swidgets)

    def _update_icons(self, eval_type: str, evals: list[dict], widgets: dict):
        """Construit la liste scrollable des slots actifs."""
        # Nettoyer les anciennes rangées
        layout = widgets['scroll_content'].layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        visible_set = self._visible_f if eval_type == 'F' else self._visible_s
        active_count = sum(1 for e in evals if e['is_active'])
        new_rows = {}

        for e in evals:
            if not e['is_active']:
                continue
            idx = e['index']
            is_visible = idx in visible_set

            # Rangée cliquable
            row = QFrame()
            row.setFrameShape(QFrame.StyledPanel)
            if is_visible:
                row.setStyleSheet(
                    f"QFrame {{ background: {theme_manager.theme.palette.primary_light}; "
                    f"border: 1px solid {theme_manager.theme.palette.active}; "
                    f"border-left: 3px solid {theme_manager.theme.palette.selection}; "
                    f"border-radius: 3px; }}"
                )
            else:
                row.setStyleSheet(
                    f"QFrame {{ background: {theme_manager.theme.palette.background}; "
                    f"border: 1px solid {theme_manager.theme.palette.border}; "
                    f"border-radius: 3px; }}"
                )
            row.setCursor(Qt.PointingHandCursor)

            rh = QHBoxLayout(row)
            rh.setContentsMargins(3, 1, 3, 1)
            rh.setSpacing(3)

            # Index
            idx_lbl = QLabel(f'{eval_type}{idx:02d}')
            idx_lbl.setFixedWidth(34)
            idx_lbl.setFont(theme_manager.font(theme_manager.theme.fonts.small, QFont.Bold))
            idx_lbl.setStyleSheet(f"color: {theme_manager.theme.palette.text_strong}; border: none;")
            rh.addWidget(idx_lbl)

            # Nature (le label DB est redondant avec idx_lbl, on remplace par nature)
            nature_txt = (e.get('nature') or '')
            if len(nature_txt) > 22:
                nature_txt = nature_txt[:20] + '…'
            lbl_nature = QLabel(nature_txt)
            lbl_nature.setFixedWidth(178)
            lbl_nature.setFont(theme_manager.font(theme_manager.theme.fonts.small))
            lbl_nature.setStyleSheet(f"color: {theme_manager.theme.palette.text_soft}; border: none;")
            rh.addWidget(lbl_nature)

            if e.get('nature', ''):
                rh.addSpacing(8)

            # Critères actifs uniquement
            active_crits = [l.upper() for l in ('a','b','c','d') if e.get(f'crit_{l}', '0') == '1']
            crits_txt = ' '.join(active_crits) if active_crits else ''
            lbl_crits = QLabel(crits_txt)
            lbl_crits.setFont(theme_manager.font(theme_manager.theme.fonts.small, QFont.Bold))
            lbl_crits.setStyleSheet(
                f"font-weight: bold; color: {theme_manager.theme.palette.active}; border: none;"
            )
            rh.addWidget(lbl_crits)

            rh.addStretch()

            # Rendre cliquable
            row.mousePressEvent = lambda event, ev=eval_type, si=idx: self._on_slot_icon_clicked(ev, si)

            layout.addWidget(row)
            new_rows[idx] = row

        # Message si aucun slot actif
        if active_count == 0:
            empty_lbl = QLabel('Aucune évaluation active')
            empty_lbl.setProperty('class', 'placeholder')
            empty_lbl.setFont(theme_manager.font(theme_manager.theme.fonts.small))
            empty_lbl.setStyleSheet(f"color: {theme_manager.theme.palette.inactive}; padding: 3px;")
            layout.addWidget(empty_lbl)

        layout.addStretch()
        widgets['slot_rows'] = new_rows

        # Mise à jour des boutons Toute/Aucune
        all_visible = len(visible_set) == active_count and active_count > 0
        none_visible = len(visible_set) == 0
        widgets['tout_btn'].setChecked(all_visible)
        widgets['tout_btn'].setStyleSheet(self._btn_toggle_style(all_visible))
        widgets['aucune_btn'].setChecked(none_visible)
        widgets['aucune_btn'].setStyleSheet(self._btn_toggle_style(none_visible))
        comment_key = '_show_f_comment' if eval_type == 'F' else '_show_s_comment'
        show_comm = getattr(self, comment_key, False)
        widgets['comm_btn'].setChecked(show_comm)
        widgets['comm_btn'].setStyleSheet(self._btn_toggle_style(show_comm))

    # ------------------------------------------------------------------
    # Gestionnaires des interactions Top bar
    # ------------------------------------------------------------------

    def _on_slot_icon_clicked(self, eval_type: str, slot_index: int):
        """Clic sur une icône de slot : bascule l'affichage dans la grille."""
        evals = self._evals_f if eval_type == 'F' else self._evals_s
        visible_set = self._visible_f if eval_type == 'F' else self._visible_s

        is_active = False
        for e in evals:
            if e['index'] == slot_index and e['is_active']:
                is_active = True
                break
        if not is_active:
            return

        # Mémoriser le dernier clic pour le détail
        if eval_type == 'F':
            self._last_clicked_f = slot_index
        else:
            self._last_clicked_s = slot_index

        if slot_index in visible_set:
            visible_set.discard(slot_index)
        else:
            visible_set.add(slot_index)

        self._on_selection_changed()

    def _on_toggle_all(self, eval_type: str):
        """Bascule : affiche tous les slots actifs ou les masque."""
        evals = self._evals_f if eval_type == 'F' else self._evals_s
        visible_set = self._visible_f if eval_type == 'F' else self._visible_s

        active_indices = {e['index'] for e in evals if e['is_active']}
        if visible_set == active_indices:
            visible_set.clear()
            if eval_type == 'F':
                self._last_clicked_f = None
            else:
                self._last_clicked_s = None
        else:
            visible_set.clear()
            visible_set.update(active_indices)
            # Premier actif comme dernier clic
            for e in evals:
                if e['is_active']:
                    if eval_type == 'F':
                        self._last_clicked_f = e['index']
                    else:
                        self._last_clicked_s = e['index']
                    break
        self._on_selection_changed()

    def _on_toggle_none(self, eval_type: str):
        """Masque tous les slots de ce type."""
        visible_set = self._visible_f if eval_type == 'F' else self._visible_s
        visible_set.clear()
        if eval_type == 'F':
            self._last_clicked_f = None
        else:
            self._last_clicked_s = None
        self._on_selection_changed()

    def _on_toggle_comment(self, eval_type: str):
        """Affiche/masque la colonne commentaire pour ce type."""
        key = '_show_f_comment' if eval_type == 'F' else '_show_s_comment'
        setattr(self, key, not getattr(self, key))
        self._on_selection_changed()

    def _on_toggle_crit(self, letter: str):
        """Affiche/masque une colonne critère dans la grille."""
        self._visible_crits[letter] = not self._visible_crits[letter]
        self._crit_btns[letter].setStyleSheet(self._btn_crit_style(self._visible_crits[letter]))
        self._on_selection_changed()

    def _on_jgt_toggle(self):
        """Bascule l'affichage des 4 colonnes jugement."""
        checked = self._jwidgets['jgt_btn'].isChecked()
        self._jwidgets['jgt_btn'].setStyleSheet(self._btn_toggle_style(checked))
        self._on_selection_changed()

    def _on_jgt_note_toggle(self):
        """Bascule visibilité colonne note sur 7."""
        checked = self._jwidgets['note_btn'].isChecked()
        self._jwidgets['note_btn'].setStyleSheet(self._btn_toggle_style(checked))
        self._on_selection_changed()

    def _on_jgt_comment_toggle(self):
        """Bascule visibilité commentaire jugements."""
        self._show_jgt_comment = not self._show_jgt_comment
        self._jwidgets['comm_btn'].setStyleSheet(
            self._btn_toggle_style(self._show_jgt_comment))
        self._on_selection_changed()

    def _on_selection_changed(self):
        """Recharge la grille après un changement de sélection."""
        self._save_grid_edits()
        if self._current_item is None:
            return
        item = self._current_item
        class_id = item['class_id']
        cycle = item['cycle']
        eleves = self._eleves_par_classe.get(class_id, [])
        self._update_top_bar()
        self._fill_grille(item, cycle, eleves)

    def _clear_grille(self):
        """Vide la grille tout en gardant le layout."""
        if self._grille is not None:
            self._grille.setRowCount(0)
            self._grille.setColumnCount(0)
            self._grille.setRowCount(0)
            self._grille.setColumnCount(0)
        self._visible_f.clear()
        self._visible_s.clear()
        self._current_item = None

    def _fill_grille(self, item: dict, cycle: str, eleves: list[dict]) -> None:
        """Remplit la grille élèves × notes avec les colonnes sélectionnées."""
        if self._grille is None:
            return

        conn = db.local_conn
        if conn is None:
            return

        # --- 1. Déterminer les colonnes à afficher selon les sélections ---
        synth_display = 'note_on_7' if cycle == 'PEI' else 'moy_on_20'
        table = ('larcauth_learnerpei_has_termsubjectpei' if cycle == 'PEI'
                 else 'larcauth_learnerdp_has_termsubjectdp')

        visible_db_cols: list[str] = []

        # Lookup rapide critères par évaluation
        _eval_crits: dict[str, dict[int, dict[str, bool]]] = {'F': {}, 'S': {}}
        for et, evals in (('F', self._evals_f), ('S', self._evals_s)):
            for e in evals:
                _eval_crits[et][e['index']] = {
                    'a': e.get('crit_a', '0') == '1',
                    'b': e.get('crit_b', '0') == '1',
                    'c': e.get('crit_c', '0') == '1',
                    'd': e.get('crit_d', '0') == '1',
                }

        def _crit_visible(eval_type: str, idx: int, crit: str) -> bool:
            if not self._visible_crits.get(crit, False):
                return False
            ec = _eval_crits.get(eval_type, {}).get(idx, {})
            return ec.get(crit, False)

        # Colonnes des slots formatives visibles
        for slot_idx in sorted(self._visible_f):
            for crit in ('a', 'b', 'c', 'd'):
                if _crit_visible('F', slot_idx, crit):
                    db_name = f'f{slot_idx:02d}_note_{crit}'
                    visible_db_cols.append(db_name)
            if self._show_f_comment:
                visible_db_cols.append(f'f{slot_idx:02d}_observation')

        # Colonnes des slots sommatives visibles
        for slot_idx in sorted(self._visible_s):
            for crit in ('a', 'b', 'c', 'd'):
                if _crit_visible('S', slot_idx, crit):
                    db_name = f's{slot_idx:02d}_note_{crit}'
                    visible_db_cols.append(db_name)
            if self._show_s_comment:
                visible_db_cols.append(f's{slot_idx:02d}_observation')

        # Jugements
        if self._jwidgets['jgt_btn'].isChecked():
            for letter in ('a', 'b', 'c', 'd'):
                visible_db_cols.append(f'jgt_{letter}')
        if self._jwidgets['note_btn'].isChecked():
            visible_db_cols.append(synth_display)
        if self._show_jgt_comment:
            visible_db_cols.append('term_observation')

        # --- 2. Vérifier quelles colonnes existent dans la table ---
        existing_db_cols: set[str] = set()
        try:
            cur = conn.execute(f'PRAGMA table_info("{table}")')
            for row in cur.fetchall():
                existing_db_cols.add(row[1])
        except Exception:
            pass

        def _nature_for_prefix(col_name: str, idx: int) -> str:
            evals = self._evals_f if col_name.startswith('f') else self._evals_s
            for e in evals:
                if e['index_eval'] == idx:
                    return e.get('nature', '') or ''
            return ''

        existing_visible = [c for c in visible_db_cols if c in existing_db_cols]

        # --- 3. Noms d'affichage ---
        display_names = []
        for c in existing_visible:
            if c.startswith('f') and '_note_' in c:
                parts = c.split('_')
                if c.endswith('_nature') or 'nature' in c:
                    idx = int(parts[0][1:]) if parts[0][1:].isdigit() else 0
                    nat = _nature_for_prefix(c, idx)
                    display_names.append(nat if nat else 'Nature')
                else:
                    display_names.append(f'F{parts[0][1:]}_{parts[-1].upper()}')
            elif c.startswith('s') and '_note_' in c:
                parts = c.split('_')
                if c.endswith('_nature') or 'nature' in c:
                    idx = int(parts[0][1:]) if parts[0][1:].isdigit() else 0
                    nat = _nature_for_prefix(c, idx)
                    display_names.append(nat if nat else 'Nature')
                else:
                    display_names.append(f'S{parts[0][1:]}_{parts[-1].upper()}')
            elif c.startswith('jgt_'):
                display_names.append(f'Jgt {c[-1].upper()}')
            elif c == synth_display:
                display_names.append('Note' if cycle == 'PEI' else 'Moy.')
            elif c.endswith('_observation'):
                display_names.append(f'{c[0].upper()} Obs.')
            elif c == 'term_observation':
                display_names.append('Obs. Terme')
            else:
                display_names.append(c)

        # Configurer la grille unique
        self._grille.setColumnCount(1 + len(display_names))
        self._grille.setHorizontalHeaderLabels(['Élève'] + display_names)
        row_count = len(eleves)
        self._grille.setRowCount(row_count)

        # --- 4. Charger les notes — scoped par CTS, matchées par fk_student_id ---
        ts_id = item['termsubject_id']
        notes: dict[int, dict[str, str]] = {}
        self._row_ids: dict[int, int] = {}
        if existing_visible:
            has_fk = False
            try:
                cur = conn.execute(f'PRAGMA table_info("{table}")')
                for col in cur.fetchall():
                    if col[1] == 'fk_student_id':
                        has_fk = True
                        break
            except Exception:
                pass

            if has_fk:
                select_list = ['id', 'fk_student_id'] + existing_visible
                try:
                    cols_sql = ', '.join(f'"{c}"' for c in select_list)
                    rows = conn.execute(
                        f'SELECT {cols_sql} FROM "{table}"'
                    ).fetchall()
                    for r in rows:
                        pei_id = int(r[0] or 0)
                        student_id = int(r[1] or 0)
                        if not student_id or not pei_id:
                            continue
                        row_dict: dict[str, str] = {}
                        for ci, cn in enumerate(select_list):
                            row_dict[cn] = r[ci] if r[ci] is not None else ''
                        notes[student_id] = row_dict
                        self._row_ids[student_id] = pei_id
                except Exception as e:
                    print(f"Erreur chargement notes: {e}")
            else:
                self.statusBar().showMessage(
                    'Données ancienne génération — relancez --mode4 pour les notes'
                )

        # --- 5. Remplir la grille ---
        for row_idx, eleve in enumerate(eleves):
            # Colonne 0 : nom élève
            name_txt = (f"{eleve['prenom']} {eleve['nom']}" if self._name_format_prenom_first
                        else f"{eleve['nom']} {eleve['prenom']}")
            item_eleve = QTableWidgetItem(name_txt)
            item_eleve.setFlags(item_eleve.flags() & ~Qt.ItemIsEditable)
            item_eleve.setData(Qt.UserRole, eleve['id'])
            item_eleve.setData(Qt.UserRole + 1, eleve['nom'])
            item_eleve.setData(Qt.UserRole + 2, eleve['prenom'])
            item_eleve.setTextAlignment(Qt.AlignCenter)
            self._grille.setItem(row_idx, 0, item_eleve)

            # Colonnes 1..N : notes
            eleve_notes = notes.get(eleve['id'], {})
            for ci, db_name in enumerate(existing_visible):
                val = eleve_notes.get(db_name, '')

                item_bg: QColor | None = None

                is_synth = (db_name == synth_display)
                is_note_col = '_note_' in db_name or is_synth
                if is_note_col:
                    if val:
                        try:
                            note_val = float(val)
                        except (ValueError, TypeError):
                            item_bg = QColor(255, 255, 255)  # blanc si valeur invalide
                        else:
                            max_note = 8 if cycle == 'PEI' else 20
                            half = max_note / 2
                            clamped = max(0, min(note_val, max_note))
                            if clamped <= half:
                                t = clamped / half
                                r, g, b = 255, int(100 + 155 * t), int(100 + 155 * t)
                            else:
                                t = (clamped - half) / half
                                r, g, b = int(255 - 155 * t), 255, int(255 - 155 * t)
                            item_bg = QColor(r, g, b)
                    else:
                        item_bg = QColor(255, 255, 255)  # blanc si vide

                item = ColorItem(str(val), item_bg)
                item.setTextAlignment(Qt.AlignCenter)
                self._grille.setItem(row_idx, ci + 1, item)

        # --- Diagnostic ---
        sample_cols = ', '.join(existing_visible[:3]) if existing_visible else '(aucune)'
        self.statusBar().showMessage(
            f'{len(eleves)} élèves, {len(existing_visible)} col, cycle={cycle}', 5000)
        if pei_config:
            self._grille.setColumnWidth(0, pei_config.student_width)
            for ci, db_name in enumerate(existing_visible):
                is_obs = '_observation' in db_name or db_name == 'term_observation'
                if is_obs:
                    self._grille.setColumnWidth(ci, pei_config.remark_width)
                else:
                    self._grille.setColumnWidth(ci, pei_config.note_width)

        try:
            self._grille.cellChanged.disconnect(self._on_cell_changed)
        except Exception:
            pass
        # Stocker pour la sauvegarde (sans colonne élève)
        self._current_table = table
        self._current_col_names = existing_visible
        self._current_student_ids = [e['id'] for e in eleves]
        self._grille.cellChanged.connect(self._on_cell_changed)
        # Largeur colonnes notes (décalage de 1 pour la colonne élève)
        if pei_config:
            self._grille.setColumnWidth(0, pei_config.student_width)
            for ci, db_name in enumerate(existing_visible):
                is_obs = '_observation' in db_name or db_name == 'term_observation'
                if is_obs:
                    self._grille.setColumnWidth(ci + 1, pei_config.remark_width)
                else:
                    self._grille.setColumnWidth(ci + 1, pei_config.note_width)

    def _on_cell_changed(self, row: int, col: int) -> None:
        if row < 0 or row >= self._grille.rowCount():
            return
        if col <= 0 or col - 1 >= len(self._current_col_names):
            return  # colonne 0 = nom élève (non-éditable)
        item_name = self._grille.item(row, 0)
        student_id = item_name.data(Qt.UserRole) if item_name else None
        if student_id is None:
            return
        db_name = self._current_col_names[col - 1]
        item = self._grille.item(row, col)
        val = item.text().strip() if item else ''

        # Recalculer le gradient pour cette cellule
        if isinstance(item, ColorItem):
            is_note_col = '_note_' in db_name or db_name in ('note_on_7', 'moy_on_20')
            if is_note_col and val:
                try:
                    note_val = float(val)
                except (ValueError, TypeError):
                    item.set_bg(QColor(255, 255, 255))
                else:
                    cycle = self._current_cycle
                    max_note = 8 if cycle == 'PEI' else 20
                    half = max_note / 2
                    clamped = max(0, min(note_val, max_note))
                    if clamped <= half:
                        t = clamped / half
                        r, g, b = 255, int(100 + 155 * t), int(100 + 155 * t)
                    else:
                        t = (clamped - half) / half
                        r, g, b = int(255 - 155 * t), 255, int(255 - 155 * t)
                    item.set_bg(QColor(r, g, b))
            elif is_note_col:
                item.set_bg(QColor(255, 255, 255))

        self._dirty_cells[(student_id, db_name)] = val
        self.statusBar().showMessage('Modifications non sauvegardées')

    def _on_header_section_clicked(self, col: int) -> None:
        if col != 0:
            return
        self._name_format_prenom_first = not self._name_format_prenom_first
        for row in range(self._grille.rowCount()):
            item = self._grille.item(row, 0)
            if item:
                nom = item.data(Qt.UserRole + 1)
                prenom = item.data(Qt.UserRole + 2)
                if nom and prenom:
                    item.setText(f"{prenom} {nom}" if self._name_format_prenom_first
                                 else f"{nom} {prenom}")

    def _save_grid_edits(self) -> int:
        """Sauvegarde les cellules modifiées dans SQLite. Retourne le nombre de cellules sauvegardées."""
        conn = db.local_conn
        if conn is None or not self._dirty_cells:
            return 0
        table = getattr(self, '_current_table', None)
        if table is None:
            return 0
        saved = 0
        try:
            for (student_id, db_name), val in list(self._dirty_cells.items()):
                pei_id = self._row_ids.get(student_id)
                if pei_id is None:
                    continue
                conn.execute(
                    f'UPDATE "{table}" SET "{db_name}" = ? WHERE id = ?',
                    (val, pei_id)
                )
                saved += 1
            conn.commit()
            self._dirty_cells.clear()
            if saved:
                self.statusBar().showMessage(f'{saved} cellule(s) sauvegardée(s)')
        except Exception as e:
            self.statusBar().showMessage(f'Erreur sauvegarde: {e}')
        return saved

    def _on_other_item_selected(self, idx: int) -> None:
        """Item Autre Matière-Classe sélectionné."""
        termother_id = self._items_other_combo.itemData(idx) if idx >= 0 else None
        if termother_id is None:
            self._clear_grille()
            self.statusBar().showMessage(
                f'{len(self._items)} matière(s)-classe(s)'
            )
            return

        self._clear_grille()
        item = None
        for i in self._items_other:
            if i['termothersubject_id'] == termother_id:
                item = i
                break
        label = f"{item['matiere_label']} - {item['class_label']}" if item else 'Autre matière'
        self.statusBar().showMessage(f'{label} (autre matière)')

    # ------------------------------------------------------------------
    # Manager windows
    # ------------------------------------------------------------------
    def _open_manager_f(self):
        self._open_manager('F')

    def _open_manager_s(self):
        self._open_manager('S')

    def _open_manager(self, eval_type: str):
        if self._current_ts_id is None:
            self.statusBar().showMessage('Sélectionnez d\'abord une matière-classe')
            return
        existing = self._manager_f if eval_type == 'F' else self._manager_s
        if existing is not None:
            existing.close()
        slot_label = ''
        for item in self._items:
            if item['termsubject_id'] == self._current_ts_id:
                slot_label = f"{item['matiere_label']} - {item['class_label']}"
                break
        try:
            w = EvalManagerWindow(eval_type, self._current_ts_id, slot_label, self)
            w.destroyed.connect(lambda: self._on_manager_closed(eval_type))
            w.show()
            if eval_type == 'F':
                self._manager_f = w
            else:
                self._manager_s = w
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.statusBar().showMessage(f'Erreur: {e}')

    def _on_manager_closed(self, eval_type: str):
        try:
            if self._current_ts_id:
                self._load_evaluations_from_db(self._current_ts_id)
                evals = self._evals_f if eval_type == 'F' else self._evals_s
                visible_set = self._visible_f if eval_type == 'F' else self._visible_s
                still_visible = {idx for idx in visible_set if any(e['index'] == idx and e['is_active'] for e in evals)}
                visible_set.clear()
                visible_set.update(still_visible)
                if not visible_set:
                    for e in evals:
                        if e['is_active']:
                            visible_set.add(e['index'])
                            break
                last_key = '_last_clicked_f' if eval_type == 'F' else '_last_clicked_s'
                lc = getattr(self, last_key)
                if lc is not None and not any(e['index'] == lc and e['is_active'] for e in evals):
                    setattr(self, last_key, next((e['index'] for e in evals if e['is_active']), None))
                self._update_top_bar()
                self._on_selection_changed()
        except RuntimeError:
            pass
        if eval_type == 'F':
            self._manager_f = None
        else:
            self._manager_s = None
