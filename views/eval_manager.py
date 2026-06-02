"""Fenêtre de gestion complète des évaluations (F ou S).

Gauche : tabs F01-F12 + légende + liste verticale de barres slots
Droite  : formulaire de détail responsive"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from common.database import db
from views.evaluation_panel import EvaluationDetailWidget


# ---------------------------------------------------------------------------
# Barre slot cliquable (horizontale)
# ---------------------------------------------------------------------------

class _SlotBar(QFrame):
    """Barre horizontale représentant un slot (code | titre | checkboxes)."""
    clicked = Signal(int)  # slot_index

    _STYLE_ACTIF = """
        background: white; border: 1px solid #27ae60;
        border-radius: 4px; padding: 2px;
    """
    _STYLE_NEXT = """
        background: #f5f5f5; border: 1px dashed #bbb;
        border-radius: 4px; padding: 2px;
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
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._build_ui()
        self.clear()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(6)

        self._code = QLabel(f"{self.eval_type}{self.slot_index:02d}")
        self._code.setFixedWidth(32)
        self._code.setAlignment(Qt.AlignCenter)
        self._code.setStyleSheet("font-weight: bold; font-size: 10px; border: none; padding: 0;")
        layout.addWidget(self._code)

        self._label = QLabel('')
        self._label.setStyleSheet("font-size: 10px; color: #333; border: none; padding: 0;")
        self._label.setWordWrap(True)
        layout.addWidget(self._label, 1)

        self._crits: dict[str, QCheckBox] = {}
        for letter in ['A', 'B', 'C', 'D']:
            cb = QCheckBox(letter)
            cb.setEnabled(False)
            cb.setStyleSheet("font-size: 9px; border: none; padding: 0;")
            self._crits[letter] = cb
            layout.addWidget(cb)

    def mousePressEvent(self, event):
        self.clicked.emit(self.slot_index)

    def set_data(self, eval_id, data: dict):
        self.eval_id = eval_id
        self._data = data

        nature = (data.get('nature') or '').strip()
        if nature:
            self._label.setText(nature[:72])
        else:
            self._label.setText('')

        active = False
        for letter in ['A', 'B', 'C', 'D']:
            val = data.get(f'crit_{letter.lower()}', '0')
            checked = val in ('1', 1, True)
            self._crits[letter].setChecked(checked)
            if checked:
                active = True
        self._active = active

    def clear(self):
        self.eval_id = None
        self._active = False
        self._data = None
        self._label.setText('')
        for cb in self._crits.values():
            cb.setChecked(False)

    def set_style_active(self):
        self.setStyleSheet(self._STYLE_ACTIF)
        self._code.setStyleSheet("font-weight: bold; font-size: 10px; color: #2c3e50; border: none; padding: 0;")
        self._label.setStyleSheet("font-size: 10px; color: #333; border: none; padding: 0;")

    def set_style_next(self):
        self.setStyleSheet(self._STYLE_NEXT)
        self._code.setStyleSheet("font-weight: bold; font-size: 10px; color: #999; border: none; padding: 0;")
        self._label.setStyleSheet("font-size: 10px; color: #999; border: none; padding: 0;")

    def set_style_hidden(self):
        self.setStyleSheet("background: transparent; border: none;")
        # hide is applied externally via setVisible


# ---------------------------------------------------------------------------
# Fenêtre de gestion
# ---------------------------------------------------------------------------

class EvalManagerWindow(QDialog):
    """Fenêtre non-modale pour gérer toutes les évaluations (F ou S)."""

    def __init__(self, eval_type: str, termsubject_id: int,
                 subject_label: str = '', parent=None):
        super().__init__(parent)
        self.eval_type = eval_type
        self._termsubject_id = termsubject_id
        self._subject_label = subject_label
        self._current_slot_index = 1

        type_label = "Formatives" if eval_type == 'F' else "Sommatives"
        self.setWindowTitle(f"Gestion des Évaluations {type_label} — {subject_label}")
        self.setMinimumSize(900, 600)
        self.setModal(False)

        print(f"[TRACE] EvalManagerWindow.__init__ type={eval_type} ts_id={termsubject_id} label='{subject_label}'")
        self._build_ui()
        print(f"[TRACE]   _build_ui done")
        self._load_data()
        print(f"[TRACE]   _load_data done")
        self._on_slot_selected(1)
        print(f"[TRACE]   init complete")

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([400, 500])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(splitter)

        self._status_lbl = QLabel('')
        self._status_lbl.setStyleSheet("font-size: 9px; color: #7f8c8d; padding: 2px 0;")
        layout.addWidget(self._status_lbl)

    def statusBar(self):
        return self._status_lbl

    def _status_msg(self, msg: str):
        self._status_lbl.setText(msg)

    def _build_left_panel(self) -> QWidget:
        container = QFrame()
        container.setFrameShape(QFrame.StyledPanel)
        container.setStyleSheet("""
            QFrame { background: white; border: 1px solid #dcdde1;
                     border-radius: 4px; }
        """)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)

        # Tabs F01-F12
        self._build_tabs(layout)

        # Légende des critères
        self._legend = QLabel('')
        self._legend.setStyleSheet("font-size: 7px; color: #777; border: none; padding: 0;")
        self._legend.setWordWrap(True)
        self._legend.hide()
        layout.addWidget(self._legend)

        # Liste verticale des barres slots
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        self._list_container = QWidget()
        self._list_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(2)

        self._bars: list[_SlotBar] = []
        for i in range(12):
            bar = _SlotBar(i + 1, self.eval_type)
            bar.clicked.connect(self._on_slot_selected)
            self._bars.append(bar)
            self._list_layout.addWidget(bar)

        self._list_layout.addStretch()
        scroll.setWidget(self._list_container)
        layout.addWidget(scroll, 1)

        return container

    def _build_tabs(self, layout: QVBoxLayout):
        tabs = QWidget()
        tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        th = QHBoxLayout(tabs)
        th.setContentsMargins(0, 0, 0, 0)
        th.setSpacing(2)

        self._tab_btns: list[QPushButton] = []
        for i in range(12):
            btn = QPushButton(f"{self.eval_type}{i+1:02d}")
            btn.setFixedHeight(24)
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton { font-size: 8px; font-weight: bold; padding: 1px 4px;
                              background: #e0e0e0; color: #666; border-radius: 3px; }
                QPushButton:checked { background: #27ae60; color: white; }
                QPushButton:hover { background: #bdc3c7; }
                QPushButton:checked:hover { background: #219a52; }
            """)
            btn.clicked.connect(lambda checked, idx=i+1: self._on_tab_clicked(idx))
            self._tab_btns.append(btn)
            th.addWidget(btn)

        layout.addWidget(tabs)

    def _build_right_panel(self) -> QWidget:
        container = QFrame()
        container.setFrameShape(QFrame.StyledPanel)
        container.setStyleSheet("""
            QFrame { background: white; border: 1px solid #dcdde1;
                     border-radius: 4px; }
        """)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self._detail = EvaluationDetailWidget(
            1, self.eval_type, None,
            self._termsubject_id, self._subject_label
        )
        layout.addWidget(self._detail, 1)

        save_btn = QPushButton("Enregistrer cette évaluation")
        save_btn.setStyleSheet("""
            QPushButton { background: #27ae60; color: white; font-weight: bold;
                          padding: 8px 24px; border-radius: 4px; font-size: 13px; }
            QPushButton:hover { background: #219a52; }
        """)
        save_btn.clicked.connect(self._on_save_slot)
        layout.addWidget(save_btn)

        return container

    # ------------------------------------------------------------------
    # Logique
    # ------------------------------------------------------------------
    def _load_data(self):
        conn = db.local_conn
        if conn is None:
            return

        # Légende critères
        try:
            row = conn.execute("""
                SELECT fk_levelsubject_id FROM larcauth_classroom_termsubject
                WHERE id = ?
            """, (str(self._termsubject_id),)).fetchone()
            if row:
                ls_id = row[0]
                rows = conn.execute("""
                    SELECT criteria_letter, criteria_label
                    FROM larcauth_criteria_of_levelsubject
                    WHERE fk_levelsubject_id = ?
                      AND criteria_letter IN ('A','B','C','D')
                    ORDER BY criteria_letter
                """, (ls_id,)).fetchall()
                if rows:
                    parts = []
                    for r in rows:
                        lbl = (r[1] or '').replace('\n', ' ')
                        parts.append(f'{r[0]}: {lbl}')
                    self._legend.setText(' | '.join(parts))
                    self._legend.show()
        except Exception:
            pass

        # Données des slots
        rows = conn.execute("""
            SELECT id, index_eval,
                   crit_a, crit_b, crit_c, crit_d,
                   label, nature, source
            FROM larcauth_evaluation
            WHERE fk_classroom_termsubject_id = ?
              AND type_evaluation = ?
              AND CAST(index_eval AS INTEGER) BETWEEN 1 AND 12
            ORDER BY CAST(index_eval AS INTEGER)
        """, (str(self._termsubject_id), self.eval_type)).fetchall()

        loaded = {int(r[1]): r for r in rows}
        for bar in self._bars:
            r = loaded.get(bar.slot_index)
            if r:
                data = {
                    'crit_a': r[2], 'crit_b': r[3], 'crit_c': r[4], 'crit_d': r[5],
                    'label': r[6] or '', 'nature': r[7] or '', 'source': r[8] or '',
                }
                bar.set_data(r[0], data)
            else:
                bar.clear()

        self._update_visibility()
        self._update_tabs()

    def _update_visibility(self):
        """Affiche les barres : actives + 1 suivante grisée, le reste masqué."""
        found_next = False
        for bar in self._bars:
            if bar._active and bar.eval_id is not None:
                bar.set_style_active()
                bar.setVisible(True)
            elif not found_next:
                # Première inactive = la "suivante"
                bar.set_style_next()
                bar.setVisible(True)
                found_next = True
            else:
                bar.setVisible(False)

    def _update_tabs(self):
        """Met à jour les tabs : vert si actif, sélectionné si courant."""
        for i, bar in enumerate(self._bars):
            active = bar._active and bar.eval_id is not None
            btn = self._tab_btns[i]
            if active:
                btn.setStyleSheet("""
                    QPushButton { font-size: 8px; font-weight: bold; padding: 1px 4px;
                                  background: #27ae60; color: white; border-radius: 3px; }
                    QPushButton:hover { background: #219a52; }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton { font-size: 8px; font-weight: bold; padding: 1px 4px;
                                  background: #e0e0e0; color: #666; border-radius: 3px; }
                    QPushButton:hover { background: #bdc3c7; }
                """)
            btn.setChecked(i + 1 == self._current_slot_index)

    def _on_tab_clicked(self, slot_index: int):
        self._on_slot_selected(slot_index)

    def _on_slot_selected(self, slot_index: int):
        self._current_slot_index = slot_index
        bar = self._bars[slot_index - 1]
        self._detail.set_slot_info(slot_index, self.eval_type)
        self._detail.set_data(bar._data or {})
        self._detail._load_criteria_labels()
        self._update_tabs()

    def _on_save_slot(self):
        """Sauvegarde le slot actuel et met à jour l'affichage."""
        bar = self._bars[self._current_slot_index - 1]
        form_data = self._detail.get_form_data()
        slot_id = bar.eval_id
        if slot_id is None:
            print(f"Erreur sauvegarde: id d'évaluation est None pour {self.eval_type}{self._current_slot_index:02d}")
            self._status_msg('Impossible d\'enregistrer: évaluation non identifiée')
            return

        conn = db.local_conn
        if conn is None:
            print("Erreur sauvegarde: aucune connexion SQLite")
            self._status_msg('Erreur: base locale non disponible')
            return
        try:
            label_val = (bar._data or {}).get('label', '')
            print(f"DEBUG _on_save_slot: id={slot_id}, nature={form_data.get('nature','')[:30]}, crits={form_data.get('crit_a','0')}{form_data.get('crit_b','0')}{form_data.get('crit_c','0')}{form_data.get('crit_d','0')}")
            conn.execute("""
                UPDATE larcauth_evaluation
                SET label=?, nature=?, source=?,
                    crit_a=?, crit_b=?, crit_c=?, crit_d=?
                WHERE id=?
            """, (
                label_val,
                form_data.get('nature', ''),
                form_data.get('source', ''),
                form_data.get('crit_a', '0'),
                form_data.get('crit_b', '0'),
                form_data.get('crit_c', '0'),
                form_data.get('crit_d', '0'),
                slot_id,
            ))
            conn.commit()

            if bar._data:
                bar._data['nature'] = form_data.get('nature', '')
                bar._data['source'] = form_data.get('source', '')
                for k in ('crit_a', 'crit_b', 'crit_c', 'crit_d'):
                    bar._data[k] = form_data.get(k, '0')
            bar.set_data(slot_id, bar._data or {})
            self._update_visibility()
            self._update_tabs()
            self._status_msg(f'Évaluation {self.eval_type}{self._current_slot_index:02d} enregistrée')
        except Exception as e:
            print(f"Erreur sauvegarde: {e}")
            self._status_msg(f'Erreur lors de la sauvegarde: {e}')
