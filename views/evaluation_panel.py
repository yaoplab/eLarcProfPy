"""Panneau d'évaluations (Formatives F01-F12 / Sommatives S01-S12)
avec slots cliquables ouvrant une fenêtre de détail."""
from __future__ import annotations

import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import (
    QCheckBox,
    QSizePolicy,
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from common.database import db

try:
    import enchant
    HAS_ENCHANT = True
except ImportError:
    HAS_ENCHANT = False


# ---------------------------------------------------------------------------
# Surligneur orthographique
# ---------------------------------------------------------------------------

class _SpellHighlighter(QSyntaxHighlighter):
    """Surligne les mots mal orthographiés en rouge (si enchant disponible)."""

    def __init__(self, parent, lang='fr_FR'):
        super().__init__(parent)
        self._fmt = QTextCharFormat()
        self._fmt.setUnderlineColor(Qt.red)
        self._fmt.setUnderlineStyle(QTextCharFormat.SpellCheckUnderline)
        self._dict = None
        if HAS_ENCHANT:
            try:
                self._dict = enchant.Dict(lang)
            except Exception:
                pass

    def highlightBlock(self, text: str):
        if self._dict is None:
            return
        for m in re.finditer(r'\b\w+\b', text):
            word = m.group()
            if word.isdigit() or len(word) <= 1:
                continue
            if not self._dict.check(word):
                self.setFormat(m.start(), m.end() - m.start(), self._fmt)


# ---------------------------------------------------------------------------
# Widget formulaire réutilisable (détail d'une évaluation)
# ---------------------------------------------------------------------------

class EvaluationDetailWidget(QWidget):
    """Formulaire d'édition d'un slot d'évaluation (label, nature, source, critères)."""

    def __init__(self, slot_index: int, eval_type: str, eval_data: dict | None = None,
                 termsubject_id: int | None = None, subject_label: str = '',
                 parent=None):
        super().__init__(parent)
        self.slot_index = slot_index
        self.eval_type = eval_type
        self._data = eval_data
        self._termsubject_id = termsubject_id
        self._subject_label = subject_label

        self._build_ui()
        self._load_data()
        self._load_criteria_labels()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        self.setStyleSheet("font-family: Roboto;")

        title = QLabel(f'{self.eval_type}{self.slot_index:02d}')
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title)

        if self._subject_label:
            sl = QLabel(self._subject_label)
            sl.setStyleSheet("font-size: 11px; color: #7f8c8d; margin-top: -6px;")
            sl.setWordWrap(True)
            layout.addWidget(sl)

        form = QFormLayout()
        form.setSpacing(4)
        self._label_display = QLabel('')
        self._label_display.setStyleSheet("font-size: 11px; color: #555; padding: 4px 0;")
        self._label_display.setWordWrap(True)
        self._nature_edit = QLineEdit()
        self._nature_edit.setPlaceholderText('Nature (ex: Devoir, Interrogation, Projet...)')
        self._nature_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        form.addRow('Label :', self._label_display)
        form.addRow('Nature :', self._nature_edit)
        layout.addLayout(form)

        src_label = QLabel('Source / Texte de l\'évaluation :')
        src_label.setStyleSheet("font-size: 10px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(src_label)

        # Barre d'outils formatage
        tb = QHBoxLayout()
        tb.setSpacing(2)
        tb.setContentsMargins(0, 0, 0, 0)
        for icon, tip, md_insert in [
            ('B', 'Gras', '**texte**'),
            ('I', 'Italique', '*texte*'),
            ('H', 'Titre', '## '),
            ('•', 'Liste', '- '),
            ('🔗', 'Lien', '[texte](url)'),
        ]:
            btn = QPushButton(icon)
            btn.setFixedSize(26, 26)
            btn.setToolTip(tip)
            btn.setStyleSheet("""
                QPushButton { font-weight: bold; font-size: 11px;
                              background: #ecf0f1; border: 1px solid #bdc3c7;
                              border-radius: 3px; padding: 0; }
                QPushButton:hover { background: #d5dbdb; }
            """)
            btn.clicked.connect(lambda checked, s=md_insert: self._insert_md(s))
            tb.addWidget(btn)
        tb.addStretch()
        layout.addLayout(tb)

        self._source_edit = QTextEdit()
        self._source_edit.setPlaceholderText('Saisir le texte (Markdown supporté)')
        self._source_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._source_edit.setMinimumHeight(60)
        self._source_edit.setAcceptRichText(False)
        self._spell = _SpellHighlighter(self._source_edit.document(), 'fr_FR')
        layout.addWidget(self._source_edit)

        crit_label = QLabel('Critères :')
        crit_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #2c3e50; margin-top: 4px;")
        layout.addWidget(crit_label)

        crit_grid = QFrame()
        crit_grid.setFrameShape(QFrame.StyledPanel)
        crit_grid.setStyleSheet("""
            QFrame { background: #f8f9fa; border: 1px solid #e9ecef;
                     border-radius: 3px; padding: 4px; }
        """)
        grid = QGridLayout(crit_grid)
        grid.setContentsMargins(4, 2, 4, 2)
        grid.setSpacing(4)

        self._crit_widgets = {}
        for i, letter in enumerate(['a', 'b', 'c', 'd']):
            cb = QCheckBox(letter.upper())
            cb.setStyleSheet("font-weight: bold; font-size: 13px;")
            grid.addWidget(cb, 0, i, Qt.AlignCenter)

            cl = QLabel('')
            cl.setStyleSheet("color: #555; font-size: 10px;")
            cl.setWordWrap(True)
            cl.setAlignment(Qt.AlignCenter)
            grid.addWidget(cl, 1, i)

            self._crit_widgets[letter] = {'check': cb, 'label': cl, 'aspects_widget': None}
        layout.addWidget(crit_grid)

    def _load_data(self):
        if self._data is None:
            return
        self._label_display.setText(self._data.get('label', ''))
        self._nature_edit.setText(self._data.get('nature', '') or '')
        md = (self._data.get('source', '') or '').strip()
        if md:
            self._source_edit.setMarkdown(md)
        else:
            self._source_edit.clear()
        for letter, w in self._crit_widgets.items():
            val = self._data.get(f'crit_{letter}', '0')
            w['check'].setChecked(val in ('1', 1, True))

    def _load_criteria_labels(self):
        if self._termsubject_id is None:
            return
        conn = db.local_conn
        if conn is None:
            return
        try:
            row = conn.execute("""
                SELECT fk_levelsubject_id FROM larcauth_classroom_termsubject
                WHERE id = ?
            """, (str(self._termsubject_id),)).fetchone()
            if row is None:
                return
            ls_id = row[0]
            rows = conn.execute("""
                SELECT criteria_letter, criteria_label
                FROM larcauth_criteria_of_levelsubject
                WHERE fk_levelsubject_id = ?
                  AND criteria_letter IN ('A','B','C','D')
                ORDER BY criteria_letter
            """, (ls_id,)).fetchall()
            for r in rows:
                letter = r[0].lower()
                w = self._crit_widgets.get(letter)
                if w is None:
                    continue
                label_txt = (r[1] or '').replace('\n', ' ').replace('\r', '')
                w['label'].setText(label_txt)
        except Exception as e:
            print(f"Erreur chargement critères: {e}")

    def get_form_data(self) -> dict:
        crits = {letter: w['check'].isChecked() for letter, w in self._crit_widgets.items()}
        return {
            'nature': self._nature_edit.text().strip(),
            'source': self._source_edit.toMarkdown().strip(),
            'crit_a': '1' if crits['a'] else '0',
            'crit_b': '1' if crits['b'] else '0',
            'crit_c': '1' if crits['c'] else '0',
            'crit_d': '1' if crits['d'] else '0',
        }

    def set_data(self, data: dict | None):
        self._data = data
        if data is None:
            self._label_display.clear()
            self._nature_edit.clear()
            self._source_edit.clear()
            for w in self._crit_widgets.values():
                w['check'].setChecked(False)
        else:
            self._load_data()

    def set_slot_info(self, slot_index: int, eval_type: str):
        self.slot_index = slot_index
        self.eval_type = eval_type
        layout = self.layout()
        if layout and layout.count() > 0:
            item = layout.itemAt(0)
            if item and item.widget():
                item.widget().setText(f'{eval_type}{slot_index:02d}')

    def _insert_md(self, snippet: str):
        cursor = self._source_edit.textCursor()
        cursor.insertText(snippet)
        self._source_edit.setTextCursor(cursor)
        self._source_edit.setFocus()


# ---------------------------------------------------------------------------
# Dialogue modal (quick-edit depuis l'écran principal)
# ---------------------------------------------------------------------------

class EvaluationDetailDialog(QDialog):
    """Fenêtre modale d'édition rapide d'un slot d'évaluation."""

    def __init__(self, slot_index: int, eval_type: str, eval_data: dict | None,
                 termsubject_id: int | None = None, subject_label: str = '',
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'{eval_type}{slot_index:02d} — Détails')
        self.setMinimumWidth(540)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._form = EvaluationDetailWidget(slot_index, eval_type, eval_data,
                                             termsubject_id, subject_label, self)
        layout.addWidget(self._form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        save_btn = QPushButton("Enregistrer")
        save_btn.setStyleSheet("""
            QPushButton { background: #27ae60; color: white; font-weight: bold;
                          padding: 6px 24px; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #219a52; }
        """)
        cancel_btn = QPushButton("Annuler")
        cancel_btn.setStyleSheet("""
            QPushButton { background: #bdc3c7; color: #2c3e50;
                          padding: 6px 24px; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #a0a6ab; }
        """)
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def get_form_data(self) -> dict:
        return self._form.get_form_data()


# ---------------------------------------------------------------------------
# Slot cliquable
# ---------------------------------------------------------------------------

class _SlotButton(QFrame):
    """Bouton représentant un slot d'évaluation cliquable compact.

    Affiche le titre, le label, et les 4 critères sous forme compacte (☑A ☐B ☐C ☑D).
    """

    clicked = Signal(int)  # slot_index

    _STYLE_INACTIF = """
        background: #f0f0f0; border: 1px solid #e0e0e0;
        border-radius: 4px; padding: 3px;
    """
    _STYLE_ACTIF = """
        background: white; border: 1px solid #27ae60;
        border-radius: 4px; padding: 3px;
    """

    def __init__(self, slot_index: int, eval_type: str, parent=None):
        super().__init__(parent)
        self.slot_index = slot_index
        self.eval_type = eval_type
        self.eval_id = None
        self._active = False
        self._data: dict | None = None

        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(self._STYLE_INACTIF)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(1)

        # Titre
        self._title = QLabel(f"{self.eval_type}{self.slot_index:02d}")
        self._title.setAlignment(Qt.AlignCenter)
        self._title.setStyleSheet("font-weight: bold; font-size: 11px; font-family: Roboto; color: #2c3e50; border: none; padding: 0;")
        layout.addWidget(self._title)

        # Label (titre descriptif) — toujours visible
        self._label_info = QLabel('')
        self._label_info.setAlignment(Qt.AlignCenter)
        self._label_info.setStyleSheet("font-size: 9px; font-family: Roboto; color: #555; border: none; padding: 0;")
        self._label_info.setWordWrap(True)
        self._label_info.setMaximumHeight(16)
        layout.addWidget(self._label_info)

        # Critères : une ligne compacte "☑A  ☐B  ☑C  ☐D"
        self._crit_label = QLabel('')
        self._crit_label.setAlignment(Qt.AlignCenter)
        self._crit_label.setStyleSheet("font-size: 12px; font-family: Roboto; border: none; padding: 0; letter-spacing: 3px;")
        layout.addWidget(self._crit_label)

    def mousePressEvent(self, event):
        self.clicked.emit(self.slot_index)

    def set_data(self, eval_id: str, data: dict, subject_label: str = ''):
        self.eval_id = eval_id
        self._data = data
        self._subject_label = subject_label

        # Label — toujours affiché entre le titre et les critères
        lbl = data.get('label', '')
        if lbl:
            self._label_info.setText(lbl)
            self._label_info.show()
        else:
            self._label_info.setText('')
            self._label_info.hide()

        # Critères : construire "☑A ☐B ☑C ☐D"
        parts = []
        crits = []
        for letter in ['a', 'b', 'c', 'd']:
            val = data.get(f'crit_{letter}', '0')
            checked = val in ('1', 1, True)
            if checked:
                parts.append(f'☑{letter.upper()}')
                crits.append(letter.upper())
            else:
                parts.append(f'☐{letter.upper()}')
        self._crit_label.setText(' '.join(parts))
        self._active = len(crits) > 0

        if self._active:
            self._crit_label.setStyleSheet("font-size: 12px; font-family: Roboto; color: #27ae60; border: none; padding: 0; letter-spacing: 3px;")
            self._title.setStyleSheet("font-weight: bold; font-size: 11px; font-family: Roboto; color: #2c3e50; border: none; padding: 0;")
            self.setStyleSheet(self._STYLE_ACTIF)
        else:
            self._crit_label.setStyleSheet("font-size: 12px; font-family: Roboto; color: #bbb; border: none; padding: 0; letter-spacing: 3px;")
            self._title.setStyleSheet("font-weight: bold; font-size: 11px; font-family: Roboto; color: #666; border: none; padding: 0;")
            self.setStyleSheet(self._STYLE_INACTIF)

    def clear(self):
        self.eval_id = None
        self._data = None
        self._active = False
        self._label_info.hide()
        self._crit_label.setText('☐A  ☐B  ☐C  ☐D')
        self._crit_label.setStyleSheet("font-size: 12px; font-family: Roboto; color: #ddd; border: none; padding: 0; letter-spacing: 3px;")
        self._title.setStyleSheet("font-weight: bold; font-size: 11px; font-family: Roboto; color: #999; border: none; padding: 0;")
        self.setStyleSheet(self._STYLE_INACTIF)


# ---------------------------------------------------------------------------
# Panneau d'évaluations
# ---------------------------------------------------------------------------

class EvaluationPanel(QFrame):
    """Panneau d'évaluations avec grille de slots.

    Modes :
    - compact=True (défaut) : seuls les slots actifs sont visibles + bouton Gérer
    - compact=False : les 12 slots sont affichés (pour le manager)
    """

    def __init__(self, eval_type: str, title: str, compact: bool = True, parent=None):
        super().__init__(parent)
        self.eval_type = eval_type
        self.compact = compact
        self._termsubject_id = None

        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame { background: white; border: 1px solid #dcdde1;
                     border-radius: 4px; }
        """)

        self._build_ui(title)

        self._slots: list[_SlotButton] = []
        for i in range(12):
            slot = _SlotButton(i + 1, eval_type)
            slot.clicked.connect(self._on_slot_clicked)
            self._slots.append(slot)

        self._connect_manager_mode()
        self._cols = 3
        self._update_layout()

    def _build_ui(self, title: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 6)
        layout.setSpacing(2)

        # Header row: title + indicators + Gérer button
        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        hdr = QLabel(title)
        hdr.setStyleSheet(
            "font-weight: bold; font-size: 10px; font-family: Roboto; "
            "color: #2c3e50; border: none; padding: 0;"
        )
        header_row.addWidget(hdr)
        header_row.addStretch()

        self._indicators: list[QLabel] = []
        for i in range(12):
            lbl = QLabel(f'{self.eval_type}{i+1:02d}')
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFixedSize(22, 12)
            lbl.setStyleSheet(
                "background: #e0e0e0; color: #666; font-size: 6px; "
                "font-family: Roboto; font-weight: bold; border-radius: 2px;"
            )
            self._indicators.append(lbl)
            header_row.addWidget(lbl)
        header_row.addStretch()

        if self.compact:
            self._manage_btn = QPushButton("Gérer")
            self._manage_btn.setFixedHeight(22)
            self._manage_btn.setStyleSheet("""
                QPushButton { background: #3498db; color: white; font-weight: bold;
                              font-size: 9px; padding: 2px 12px; border-radius: 3px; }
                QPushButton:hover { background: #2980b9; }
            """)
            self._manage_btn.clicked.connect(self.manage_requested.emit)
            header_row.addWidget(self._manage_btn)

        layout.addLayout(header_row)

        # Légende des critères
        self._legend = QLabel('')
        self._legend.setStyleSheet(
            "font-size: 7px; font-family: Roboto; color: #777; "
            "border: none; padding: 0;"
        )
        self._legend.hide()
        layout.addWidget(self._legend)

        # Zone des slots
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll.setStyleSheet("QScrollArea { border: none; }")

        self._container = QWidget()
        self._grid = QGridLayout(self._container)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(2)

        # Placeholder visible uniquement quand aucun slot actif en mode compact
        self._empty_placeholder = QLabel("Aucune évaluation active — cliquer sur Gérer")
        self._empty_placeholder.setAlignment(Qt.AlignCenter)
        self._empty_placeholder.setStyleSheet(
            "color: #95a5a6; font-size: 10px; font-family: Roboto; "
            "border: none; padding: 0;"
        )
        self._empty_placeholder.hide()
        self._grid.addWidget(self._empty_placeholder, 0, 0)

        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll)

    def _connect_manager_mode(self):
        """En mode non-compact, connexion au clic pour le manager."""
        if not self.compact:
            for slot in self._slots:
                slot.clicked.disconnect()
                slot.clicked.connect(self._on_slot_clicked_manager)

    def _on_slot_clicked(self, slot_index: int):
        """Ouvre la boîte de dialogue modale pour ce slot (mode compact)."""
        if self._termsubject_id is None:
            return
        slot = self._slots[slot_index - 1]
        dlg = EvaluationDetailDialog(slot_index, self.eval_type, slot._data,
                                     self._termsubject_id, slot._subject_label,
                                     self)
        if dlg.exec() == QDialog.Accepted:
            form_data = dlg.get_form_data()
            self._save_criteria(slot, form_data)

    def _on_slot_clicked_manager(self, slot_index: int):
        """Signal émis quand le manager veut afficher ce slot dans le détail."""
        self.slot_selected.emit(slot_index)

    def _calc_cols(self) -> int:
        w = self.width() - 16  # margins 8+8
        if w <= 0:
            w = 400
        return max(1, w // 100)

    def showEvent(self, event):
        super().showEvent(event)
        self._cols = self._calc_cols()
        self._update_layout()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        new_cols = self._calc_cols()
        if new_cols != self._cols:
            self._cols = new_cols
            self._update_layout()

    def _update_layout(self):
        """Reconstruit la grille avec un nombre de colonnes adaptatif."""
        cols = self._cols
        # Vider la grille
        for i in reversed(range(self._grid.count())):
            item = self._grid.itemAt(i)
            if item and item.widget():
                w = item.widget()
                self._grid.removeWidget(w)
                w.setParent(None)

        if self.compact:
            active_slots = [s for s in self._slots if s._active and s.eval_id is not None]
            n = len(active_slots)
            if n > 0:
                for idx, slot in enumerate(active_slots):
                    row, col = divmod(idx, cols)
                    self._grid.addWidget(slot, row, col)
                rows_used = (n + cols - 1) // cols
                self._empty_placeholder.hide()
            else:
                self._grid.addWidget(self._empty_placeholder, 0, 0)
                self._empty_placeholder.show()
                rows_used = 1
        else:
            n = 12
            for i, slot in enumerate(self._slots):
                row, col = divmod(i, cols)
                self._grid.addWidget(slot, row, col)
            rows_used = (n + cols - 1) // cols

        slot_h = 50
        if self._slots and self._slots[0].minimumSizeHint().height() > 0:
            slot_h = self._slots[0].minimumSizeHint().height()
        scroll_h = slot_h * rows_used + self._grid.spacing() * (rows_used - 1) + 4
        self._scroll.setMinimumHeight(scroll_h)
        self._scroll.setMaximumHeight(scroll_h)

    # -- Signaux --
    slot_selected = Signal(int)  # émis en mode !compact (pour le manager)
    manage_requested = Signal()  # émis en mode compact (clic Gérer)

    def _load_criteria_legend(self, termsubject_id: int):
        """Charge les labels des critères et remplit la légende."""
        conn = db.local_conn
        if conn is None:
            return
        try:
            row = conn.execute("""
                SELECT fk_levelsubject_id FROM larcauth_classroom_termsubject
                WHERE id = ?
            """, (str(termsubject_id),)).fetchone()
            if row is None:
                return
            ls_id = row[0]
            rows = conn.execute("""
                SELECT criteria_letter, criteria_label
                FROM larcauth_criteria_of_levelsubject
                WHERE fk_levelsubject_id = ?
                  AND criteria_letter IN ('A','B','C','D')
                ORDER BY criteria_letter
            """, (ls_id,)).fetchall()
            if not rows:
                return
            parts = []
            for r in rows:
                label = (r[1] or '').replace('\n', ' ')
                parts.append(f'{r[0]}: {label}')
            self._legend.setText(' | '.join(parts))
            self._legend.show()
        except Exception:
            pass

    def _update_indicators(self):
        """Met à jour la barre d'indicateurs selon l'état actif de chaque slot."""
        for i, slot in enumerate(self._slots):
            active = slot._active and slot.eval_id is not None
            if active:
                self._indicators[i].setStyleSheet(
                    "background: #27ae60; color: white; font-size: 6px; "
                    "font-family: Roboto; font-weight: bold; border-radius: 2px;"
                )
            else:
                self._indicators[i].setStyleSheet(
                    "background: #e0e0e0; color: #666; font-size: 6px; "
                    "font-family: Roboto; font-weight: bold; border-radius: 2px;"
                )

    def _save_criteria(self, slot: _SlotButton, data: dict):
        """Sauvegarde nature, source et critères dans la base."""
        conn = db.local_conn
        if conn is None or slot.eval_id is None:
            return
        try:
            label_val = (slot._data or {}).get('label', '')
            conn.execute("""
                UPDATE larcauth_evaluation
                SET label=?, nature=?, source=?,
                    crit_a=?, crit_b=?, crit_c=?, crit_d=?
                WHERE id=?
            """, (
                label_val,
                data.get('nature', ''),
                data.get('source', ''),
                data.get('crit_a', '0'),
                data.get('crit_b', '0'),
                data.get('crit_c', '0'),
                data.get('crit_d', '0'),
                slot.eval_id,
            ))
            conn.commit()
            if slot._data:
                slot._data['nature'] = data.get('nature', '')
                slot._data['source'] = data.get('source', '')
                for k in ('crit_a', 'crit_b', 'crit_c', 'crit_d'):
                    slot._data[k] = data.get(k, '0')
            slot.set_data(slot.eval_id, slot._data or {})
            self._update_indicators()
            self._update_layout()
        except Exception as e:
            print(f"Erreur sauvegarde évaluation {slot.eval_id}: {e}")

    def load_evaluations(self, termsubject_id: int):
        """Charge les évaluations depuis SQLite pour ce termsubject_id."""
        print(f"[TRACE] EvaluationPanel({self.eval_type}).load_evaluations(ts_id={termsubject_id})")
        self._termsubject_id = termsubject_id
        conn = db.local_conn
        if conn is None:
            print("[TRACE]   conn is None -> clear_panel")
            self.clear_panel()
            return
        try:
            row = conn.execute("""
                SELECT label FROM larcauth_classroom_termsubject WHERE id = ?
            """, (str(termsubject_id),)).fetchone()
            subject_label = row[0] if row else ''
            print(f"[TRACE]   subject_label='{subject_label}'")

            self._load_criteria_legend(termsubject_id)

            rows = conn.execute("""
                SELECT id, index_eval,
                       crit_a, crit_b, crit_c, crit_d,
                       label, nature, source
                FROM larcauth_evaluation
                WHERE fk_classroom_termsubject_id = ?
                  AND type_evaluation = ?
                  AND CAST(index_eval AS INTEGER) BETWEEN 1 AND 12
                ORDER BY CAST(index_eval AS INTEGER)
            """, (str(termsubject_id), self.eval_type)).fetchall()
            print(f"[TRACE]   {len(rows)} evaluations found")

            loaded = {int(r[1]): r for r in rows}
            for slot in self._slots:
                r = loaded.get(slot.slot_index)
                if r:
                    data = {
                        'crit_a': r[2], 'crit_b': r[3], 'crit_c': r[4], 'crit_d': r[5],
                        'label': r[6] or '', 'nature': r[7] or '', 'source': r[8] or '',
                    }
                    slot.set_data(r[0], data, subject_label)
                else:
                    slot.clear()
            self._update_indicators()
            self._update_layout()
            print(f"[TRACE]   done, _termsubject_id={self._termsubject_id}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[TRACE]   Exception dans load_evaluations: {e}")
            self.clear_panel()

    def clear_panel(self):
        """Vide tous les slots et réinitialise le panneau."""
        self._termsubject_id = None
        self._legend.hide()
        for slot in self._slots:
            slot.clear()
        self._update_indicators()
        self._update_layout()



