"""Barre de filtres pour l'espace de travail du professeur.

Contrôle la visibilité des colonnes dans la grille élèves × notes.
3 sections indépendantes : Formatives, Sommatives, Jugements.
Chaque section est un widget autonome placement libre.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from common.database import db


class FilterSection(QFrame):
    """Section de filtres (Formatives, Sommatives ou Jugements).

    Args:
        hide_inactive: si True, les cases inactives sont masquées (pour F/S).
                       si False, toutes les cases restent visibles (pour Jugements).
    """

    filter_changed = Signal()

    _STYLE = """
        QFrame#section {
            background: white;
            border: 1px solid #dcdde1;
            border-radius: 3px;
        }
        QPushButton {
            font-size: 8px;
            padding: 1px 3px;
            border: 1px solid #bdc3c7;
            border-radius: 2px;
            background: #ecf0f1;
            color: #2c3e50;
            min-height: 13px;
        }
        QPushButton:hover { background: #d5dbdb; }
        QCheckBox { font-size: 9px; spacing: 2px; }
        QCheckBox::indicator {
            width: 13px; height: 13px;
            border: 1px solid #95a5a6;
            border-radius: 2px;
            background: #f0f0f0;
        }
        QCheckBox::indicator:checked { background: #2980b9; border-color: #1a5276; }
        QCheckBox:disabled { color: #b0b0b0; }
        QCheckBox:disabled::indicator { background: #e0e0e0; border-color: #ccc; }
    """

    def __init__(self, title: str, hide_inactive: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName('section')
        self.setStyleSheet(self._STYLE)
        self._hide_inactive = hide_inactive

        self._checkboxes: dict[str, QCheckBox] = {}
        self._active_slots: set[str] = set()
        self._slots_with_comments: set[str] = set()

        root = QVBoxLayout(self)
        root.setContentsMargins(3, 3, 3, 3)
        root.setSpacing(3)

        header = QHBoxLayout()
        header.setSpacing(3)
        lbl = QLabel(title)
        lbl.setFont(QFont('Segoe UI', 8, QFont.Bold))
        lbl.setStyleSheet('color: #2c3e50; border: none;')
        header.addWidget(lbl)
        header.addStretch(1)
        self._build_action_buttons(header)
        root.addLayout(header)

        self._checkboxes_row = QHBoxLayout()
        self._checkboxes_row.setSpacing(3)
        self._checkboxes_row.setContentsMargins(0, 0, 0, 0)
        root.addLayout(self._checkboxes_row)

    def _build_action_buttons(self, layout: QHBoxLayout) -> None:
        self._btn_toggle = QPushButton('Toutes')
        self._btn_toggle.setCheckable(True)
        self._btn_toggle.setChecked(True)
        self._btn_toggle.clicked.connect(self._on_toggle_all)

        self._btn_comments = QPushButton('Commentaires')
        self._comments_state = 0  # 0=off, 1=avec, 2=sans
        self._btn_comments.clicked.connect(self._on_toggle_comments)

        for btn in (self._btn_toggle, self._btn_comments):
            layout.addWidget(btn)

    def add_checkbox(self, key: str, label: str) -> QCheckBox:
        cb = QCheckBox(label)
        cb.setChecked(True)
        cb.stateChanged.connect(self._on_checkbox_changed)
        self._checkboxes[key] = cb
        self._checkboxes_row.addWidget(cb)
        return cb

    def set_slot_active(self, key: str, active: bool) -> None:
        cb = self._checkboxes.get(key)
        if cb is None:
            return
        if active:
            self._active_slots.add(key)
            cb.setStyleSheet('color: #2980b9; font-weight: bold;')
            cb.setVisible(True)
        else:
            self._active_slots.discard(key)
            cb.setStyleSheet('color: #95a5a6;')
            if self._hide_inactive:
                cb.setVisible(False)

    def set_slot_has_comment(self, key: str, has: bool) -> None:
        if has:
            self._slots_with_comments.add(key)
        else:
            self._slots_with_comments.discard(key)

    def _on_checkbox_changed(self) -> None:
        self._update_toggle_label()
        self.filter_changed.emit()

    def _update_toggle_label(self) -> None:
        if not self._active_slots:
            self._btn_toggle.setText('Toutes')
            self._btn_toggle.setChecked(True)
            return
        checked = self.get_checked_keys() & self._active_slots
        all_checked = checked == self._active_slots
        self._btn_toggle.setText('Aucunes' if all_checked else 'Toutes')
        self._btn_toggle.setChecked(all_checked)

    def _on_toggle_all(self) -> None:
        all_checked = (self.get_checked_keys() & self._active_slots) == self._active_slots
        new_state = not all_checked
        for key, cb in self._checkboxes.items():
            if key in self._active_slots:
                cb.setChecked(new_state)
        self._update_toggle_label()
        self.filter_changed.emit()

    def get_checked_keys(self) -> set[str]:
        return {k for k, cb in self._checkboxes.items() if cb.isChecked()}

    def get_active_keys(self) -> set[str]:
        return set(self._active_slots)

    def _on_toggle_comments(self) -> None:
        """Cycle : off → avec → sans → off."""
        self._comments_state = (self._comments_state + 1) % 3
        if self._comments_state == 0:
            self._btn_comments.setText('Commentaires')
            for key, cb in self._checkboxes.items():
                if key in self._active_slots:
                    cb.setChecked(True)
        elif self._comments_state == 1:
            self._btn_comments.setText('→ Sans')
            for key, cb in self._checkboxes.items():
                if key in self._active_slots:
                    cb.setChecked(key in self._slots_with_comments)
        else:
            self._btn_comments.setText('→ Toutes')
            for key, cb in self._checkboxes.items():
                if key in self._active_slots:
                    cb.setChecked(key not in self._slots_with_comments)
        self._update_toggle_label()
        self.filter_changed.emit()


class FilterBar(QWidget):
    """Contrôleur de filtres. Gère les 3 sections + logique données.

    Les sections sont exposées comme attributs publics pour placement libre :
      filter_bar.section_f  → sous le panneau Formatives
      filter_bar.section_s  → sous le panneau Sommatives
      filter_bar.section_jgt → en bas, pleine largeur
    """

    filter_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._termsubject_id: int | None = None
        self._cycle: str = 'PEI'

        self.section_f = FilterSection('Formatives', hide_inactive=True)
        self.section_f.filter_changed.connect(self.filter_changed.emit)

        self.section_s = FilterSection('Sommatives', hide_inactive=True)
        self.section_s.filter_changed.connect(self.filter_changed.emit)

        self.section_jgt = FilterSection('Jugements / Note sur 7', hide_inactive=False)
        self.section_jgt.filter_changed.connect(self.filter_changed.emit)

        self._build_checkboxes()

    def _build_checkboxes(self) -> None:
        for n in range(1, 13):
            self.section_f.add_checkbox(f'F{n:02d}', f'F{n:02d}')
        for n in range(1, 13):
            self.section_s.add_checkbox(f'S{n:02d}', f'S{n:02d}')
        for letter in ('a', 'b', 'c', 'd'):
            self.section_jgt.add_checkbox(f'Jgt_{letter}', f'Jgt {letter.upper()}')
        self.section_jgt.add_checkbox('Note7', 'Note/7')

    def load_data(self, termsubject_id: int, cycle: str) -> None:
        self._termsubject_id = termsubject_id
        self._cycle = cycle
        conn = db.local_conn
        if conn is None:
            return
        try:
            self._load_evaluations(conn, termsubject_id)
            self._load_observations(conn, termsubject_id, cycle)
        except Exception as e:
            print(f"[FilterBar] Erreur chargement : {e}")

    def _load_evaluations(self, conn, termsubject_id: int) -> None:
        cur = conn.cursor()
        cur.execute("""
            SELECT index_eval, type_evaluation, crit_a, crit_b, crit_c, crit_d
            FROM larcauth_evaluation
            WHERE fk_classroom_termsubject_id = ?
              AND CAST(index_eval AS INTEGER) BETWEEN 1 AND 12
        """, (termsubject_id,))

        for n in range(1, 13):
            self.section_f.set_slot_active(f'F{n:02d}', False)
            self.section_s.set_slot_active(f'S{n:02d}', False)

        for row in cur.fetchall():
            idx = int(row[0])
            eval_type = str(row[1]).strip().upper()
            crits = row[2:6]
            has_criteria = any(
                str(c).strip() in ('1', 'TRUE', 'ON') for c in crits if c is not None
            )
            if eval_type in ('F', 'FORMATIVES'):
                section = self.section_f
                key = f'F{idx:02d}'
            elif eval_type in ('S', 'SOMMATIVES'):
                section = self.section_s
                key = f'S{idx:02d}'
            else:
                continue
            section.set_slot_active(key, has_criteria)

        self.section_f._update_toggle_label()
        self.section_s._update_toggle_label()

    def _load_observations(self, conn, termsubject_id: int, cycle: str) -> None:
        table = ('larcauth_learnerpei_has_termsubjectpei' if cycle == 'PEI'
                 else 'larcauth_learnerdp_has_termsubjectdp')
        cur = conn.cursor()
        for prefix in ('f', 's'):
            section = self.section_f if prefix == 'f' else self.section_s
            for n in range(1, 13):
                col = f'{prefix}{n:02d}_observation'
                key = f'{prefix.upper()}{n:02d}'
                try:
                    cur.execute(
                        f'SELECT COUNT(*) FROM {table} '
                        f'WHERE {col} IS NOT NULL AND {col} != "" LIMIT 1'
                    )
                    section.set_slot_has_comment(key, cur.fetchone()[0] > 0)
                except Exception:
                    section.set_slot_has_comment(key, False)
        try:
            cur.execute(
                f'SELECT COUNT(*) FROM {table} '
                f'WHERE term_observation IS NOT NULL AND term_observation != "" LIMIT 1'
            )
            self.section_jgt.set_slot_has_comment('Note7', cur.fetchone()[0] > 0)
        except Exception:
            self.section_jgt.set_slot_has_comment('Note7', False)

    def get_filter_state(self) -> dict:
        return {
            'formatives': {f'F{n:02d}': f'F{n:02d}' in self.section_f.get_checked_keys()
                           for n in range(1, 13)},
            'sommatives': {f'S{n:02d}': f'S{n:02d}' in self.section_s.get_checked_keys()
                           for n in range(1, 13)},
            'jugements': {f'Jgt_{l}': f'Jgt_{l}' in self.section_jgt.get_checked_keys()
                          for l in ('a', 'b', 'c', 'd')}
                         | {'Note7': 'Note7' in self.section_jgt.get_checked_keys()},
        }

    def get_checked_columns(self) -> list[str]:
        conn = db.local_conn
        if conn is None:
            return []
        columns = []
        filter_state = self.get_filter_state()

        if self._termsubject_id is not None:
            cur = conn.cursor()
            cur.execute("""
                SELECT index_eval, type_evaluation, crit_a, crit_b, crit_c, crit_d
                FROM larcauth_evaluation
                WHERE fk_classroom_termsubject_id = ?
                  AND CAST(index_eval AS INTEGER) BETWEEN 1 AND 12
            """, (self._termsubject_id,))
            for row in cur.fetchall():
                idx = int(row[0])
                eval_type = str(row[1]).strip().upper()
                crits = row[2:6]
                if eval_type in ('F', 'FORMATIVES'):
                    checked = filter_state['formatives'].get(f'F{idx:02d}', False)
                    prefix = 'F'
                elif eval_type in ('S', 'SOMMATIVES'):
                    checked = filter_state['sommatives'].get(f'S{idx:02d}', False)
                    prefix = 'S'
                else:
                    continue
                if not checked:
                    continue
                for i, letter in enumerate(('a', 'b', 'c', 'd')):
                    if str(crits[i]).strip() in ('1', 'TRUE', 'ON'):
                        columns.append(f'{prefix}{idx:02d}_{letter}')

        jgt = filter_state['jugements']
        for letter in ('a', 'b', 'c', 'd'):
            if jgt.get(f'Jgt_{letter}', False):
                columns.append(f'jgt_{letter}')
        if jgt.get('Note7', False):
            columns.append('note_on_7' if self._cycle == 'PEI' else 'moy_on_20')

        return columns
