"""Fenêtre d'accueil — Dashboard intermédiaire entre login et notes.

Même style que MainWindow : QSS via _STYLE + theme_manager.palette.
Layout avec espacement Fibonacci via phi_theme.spacing.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from common.database import db, DBMode
from common.session import session
from common.theme import theme_manager
from common.sync import sync as sync_manager
from common.sqlite_init import BUSINESS_TABLES

from phibuilder.phi.scale import SpacingToken


_STAT_TABLE_LABELS = {
    'larcauth_evaluation': 'Évaluations',
    'larcauth_learnerpei_has_termsubjectpei': 'Notes PEI',
    'larcauth_learnerdp_has_termsubjectdp': 'Notes DP',
    'larcauth_classroom_termothersubject': 'Autres matières',
    'larcauth_learner_has_termothersubject': 'Notes autres',
}

_PEI_BUTTONS = [
    ('pei_grp_matieres', "Unité de groupes\nde matières"),
    ('pei_interdisc', "Unités\ninterdisciplinaires"),
    ('pei_pp', "Projet Personnel"),
]

_DP_BUTTONS = [
    ('dp_grp_matieres', "Unité de groupes\nde matières"),
    ('dp_tdc', "TDC"),
    ('dp_cas', "CAS"),
    ('dp_memoire', "Mémoire"),
]

# Mapping bouton → vue cible
_BTN_VIEW = {
    'pei_grp_matieres': 'college_notes_0',
    'pei_interdisc': 'college_notes_opt1',
    'pei_pp': 'college_notes_opt2',
    'pei_mes_classes': 'colleges_eleves',
    'dp_grp_matieres': 'lycee_notes_0',
    'dp_memoire': 'lycee_notes_opt1',
    'dp_tdc': 'lycee_notes_opt2',
    'dp_cas': 'lycee_notes_opt3',
    'dp_mes_classes': 'lycee_eleves',
    'pei_prof_principal': 'college_bulletin',
    'dp_prof_principal': 'lycee_bulletin',
}


class HomeWindow(QMainWindow):

    @property
    def _STYLE(self) -> str:
        p = theme_manager.theme.palette
        fs = theme_manager.font_size
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
                border-radius: 8px;
            }}
            QLabel.section-title {{
                font-size: {fs(13)}px;
                font-weight: bold;
                color: {p.text_strong};
            }}
            QLabel.profile-name {{
                font-size: {fs(15)}px;
                font-weight: bold;
                color: {p.text_strong};
            }}
            QLabel.meta {{
                font-size: {fs(11)}px;
                color: {p.text_soft};
            }}
            QLabel.meta-warn {{
                font-size: {fs(11)}px;
                color: {p.error};
                font-weight: bold;
            }}
            QLabel.stat-big {{
                font-size: {fs(24)}px;
                font-weight: bold;
                color: {p.primary};
            }}
            QLabel.pgm-title {{
                font-size: {fs(12)}px;
                font-weight: bold;
                color: {p.primary};
                padding: 2px 0;
            }}
            QPushButton.pgm-btn {{
                background: {p.primary_light};
                color: {p.primary};
                border: 1px solid {p.primary};
                border-radius: 8px;
                padding: 13px 12px;
                font-size: {fs(12)}px;
                font-weight: bold;
            }}
            QPushButton.pgm-btn:hover {{
                background: {p.primary};
                color: {p.on_primary};
            }}
            QPushButton.sync-btn {{
                background: {p.success};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 13px;
                font-size: {fs(12)}px;
                font-weight: bold;
            }}
            QPushButton.sync-btn:hover {{
                background: {p.button_success};
            }}
            QPushButton.logout-btn {{
                background: transparent;
                color: {p.error};
                border: 2px solid {p.error};
                border-radius: 6px;
                padding: 8px 13px;
                font-size: {fs(12)}px;
                font-weight: bold;
            }}
            QPushButton.logout-btn:hover {{
                background: {p.error};
                color: white;
            }}
            QPushButton.classes-btn {{
                background: {p.primary};
                color: {p.on_primary};
                border: none;
                border-radius: 6px;
                padding: 8px 13px;
                font-size: {fs(12)}px;
                font-weight: bold;
            }}
            QPushButton.classes-btn:hover {{
                background: {p.primary_dark};
            }}
            QPushButton.pp-btn {{
                background: {p.button_accent};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                font-size: {fs(13)}px;
                font-weight: bold;
            }}
            QPushButton.pp-btn:hover {{
                background: {p.accent};
            }}
            QFrame#sep {{
                border: none;
                border-top: 1px solid {p.border_light};
            }}
        """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle('LarcProf — Tableau de bord')
        self.resize(1060, 680)
        self.setMinimumSize(820, 520)
        self.setStyleSheet(self._STYLE)

        self._sp = theme_manager.phi_theme.spacing.spacing

        self._main_window = None
        self._poll_main_visible = None
        self._pgm_buttons: dict[str, QPushButton] = {}
        self._pgm_sections: dict[str, QWidget] = {}

        self._setup_ui()
        self._load_data()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        sp = self._sp
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(sp(SpacingToken.SM), sp(SpacingToken.SM),
                                 sp(SpacingToken.SM), sp(SpacingToken.SM))
        outer.setSpacing(sp(SpacingToken.SM))

        outer.addWidget(self._build_header())

        content = QHBoxLayout()
        content.setSpacing(sp(SpacingToken.SM))

        left = QVBoxLayout()
        left.setSpacing(sp(SpacingToken.SM))
        left.addWidget(self._build_profile_card(), 5)
        left.addWidget(self._build_sync_card(), 5)

        right = QVBoxLayout()
        right.setSpacing(sp(SpacingToken.SM))
        right.addWidget(self._build_pgm_area(), 1)

        content.addLayout(left, 5)
        content.addLayout(right, 5)
        outer.addLayout(content, 1)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage('Prêt')

    # --- Header ---
    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName('header')
        header.setMinimumHeight(55)
        h = QHBoxLayout(header)
        h.setContentsMargins(13, 8, 13, 8)

        title_font = QFont('Segoe UI', theme_manager.font_size(14), QFont.Bold)
        meta_font = QFont('Segoe UI', theme_manager.font_size(11))
        small_font = QFont('Segoe UI', theme_manager.font_size(10))

        self._hdr_title = QLabel()
        self._hdr_title.setFont(title_font)
        h.addWidget(self._hdr_title)
        h.addStretch(1)

        self._hdr_mode = QLabel()
        self._hdr_mode.setFont(meta_font)
        h.addWidget(self._hdr_mode)

        h.addSpacing(13)
        self._hdr_last_login = QLabel()
        self._hdr_last_login.setFont(small_font)
        h.addWidget(self._hdr_last_login)

        return header

    # --- Carte Profil ---
    def _build_profile_card(self) -> QWidget:
        sp = self._sp
        panel = QFrame()
        panel.setProperty('class', 'panel')
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(sp(SpacingToken.MD), sp(SpacingToken.MD),
                                  sp(SpacingToken.MD), sp(SpacingToken.MD))
        layout.setSpacing(sp(SpacingToken.XS))

        title = QLabel('Profil')
        title.setProperty('class', 'section-title')
        layout.addWidget(title)

        self._lbl_name = QLabel()
        self._lbl_name.setProperty('class', 'profile-name')
        self._lbl_name.setWordWrap(True)
        layout.addWidget(self._lbl_name)

        self._lbl_email = QLabel()
        self._lbl_email.setProperty('class', 'meta')
        self._lbl_email.setWordWrap(True)
        layout.addWidget(self._lbl_email)

        self._lbl_role = QLabel()
        self._lbl_role.setProperty('class', 'meta')
        layout.addWidget(self._lbl_role)

        sep = QFrame()
        sep.setObjectName('sep')
        layout.addWidget(sep)

        self._lbl_year = QLabel()
        self._lbl_year.setProperty('class', 'meta')
        layout.addWidget(self._lbl_year)

        self._lbl_term = QLabel()
        self._lbl_term.setProperty('class', 'meta')
        layout.addWidget(self._lbl_term)

        self._lbl_classes_count = QLabel()
        self._lbl_classes_count.setProperty('class', 'meta')
        layout.addWidget(self._lbl_classes_count)

        self._lbl_students_count = QLabel()
        self._lbl_students_count.setProperty('class', 'meta')
        layout.addWidget(self._lbl_students_count)

        layout.addSpacing(sp(SpacingToken.XS))

        # Indicateurs de connexion
        self._profile_intra = QLabel()
        self._profile_intra.setProperty('class', 'meta')
        layout.addWidget(self._profile_intra)

        self._profile_cloud = QLabel()
        self._profile_cloud.setProperty('class', 'meta')
        layout.addWidget(self._profile_cloud)

        self._profile_offline = QLabel()
        self._profile_offline.setProperty('class', 'meta')
        layout.addWidget(self._profile_offline)

        layout.addStretch()
        return panel

    # --- Carte Synchro ---
    def _build_sync_card(self) -> QWidget:
        sp = self._sp
        panel = QFrame()
        panel.setProperty('class', 'panel')
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(sp(SpacingToken.MD), sp(SpacingToken.MD),
                                  sp(SpacingToken.MD), sp(SpacingToken.MD))
        layout.setSpacing(sp(SpacingToken.XS))

        title = QLabel('Synchronisation')
        title.setProperty('class', 'section-title')
        layout.addWidget(title)

        self._lbl_sync_date = QLabel()
        self._lbl_sync_date.setProperty('class', 'meta')
        layout.addWidget(self._lbl_sync_date)

        self._lbl_sync_mode = QLabel()
        self._lbl_sync_mode.setProperty('class', 'meta')
        layout.addWidget(self._lbl_sync_mode)

        layout.addSpacing(sp(SpacingToken.MD))

        self._lbl_unsynced_count = QLabel('0')
        self._lbl_unsynced_count.setProperty('class', 'stat-big')
        layout.addWidget(self._lbl_unsynced_count)

        self._lbl_unsynced_label = QLabel('modifications non synchronisées')
        self._lbl_unsynced_label.setProperty('class', 'meta')
        layout.addWidget(self._lbl_unsynced_label)

        self._lbl_unsynced_detail = QLabel()
        self._lbl_unsynced_detail.setProperty('class', 'meta-warn')
        self._lbl_unsynced_detail.setWordWrap(True)
        layout.addWidget(self._lbl_unsynced_detail)

        layout.addSpacing(sp(SpacingToken.SM))

        btn_sync = QPushButton('Synchroniser')
        btn_sync.setProperty('class', 'sync-btn')
        btn_sync.setMinimumHeight(sp(SpacingToken.LG))
        btn_sync.clicked.connect(self._do_sync)
        layout.addWidget(btn_sync)

        layout.addStretch()
        return panel

    # --- Zone Programmes (droite) ---
    def _build_pgm_area(self) -> QWidget:
        sp = self._sp
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(sp(SpacingToken.SM))

        pei_section = self._build_program_card('PEI', _PEI_BUTTONS)
        self._pgm_sections['PEI'] = pei_section
        layout.addWidget(pei_section, 1)

        dp_section = self._build_program_card('DP', _DP_BUTTONS)
        self._pgm_sections['DP'] = dp_section
        layout.addWidget(dp_section, 1)

        self._btn_prof_principal = QPushButton('Professeur principal')
        self._btn_prof_principal.setProperty('class', 'pp-btn')
        self._btn_prof_principal.setMinimumHeight(sp(SpacingToken.XL))
        self._btn_prof_principal.setCursor(Qt.PointingHandCursor)
        self._btn_prof_principal.clicked.connect(self._open_pp)
        layout.addWidget(self._btn_prof_principal)

        btn_logout = QPushButton('Déconnexion')
        btn_logout.setProperty('class', 'logout-btn')
        btn_logout.setMinimumHeight(sp(SpacingToken.LG))
        btn_logout.clicked.connect(self._logout)
        layout.addWidget(btn_logout)

        return wrapper

    def _build_program_card(self, pgm_label: str, buttons_def: list[tuple[str, str]]) -> QWidget:
        sp = self._sp
        panel = QFrame()
        panel.setProperty('class', 'panel')
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(sp(SpacingToken.MD), sp(SpacingToken.MD),
                                  sp(SpacingToken.MD), sp(SpacingToken.MD))
        layout.setSpacing(sp(SpacingToken.SM))

        title = QLabel(pgm_label)
        title.setProperty('class', 'pgm-title')
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(sp(SpacingToken.SM))

        for idx, (key, text) in enumerate(buttons_def):
            btn = QPushButton(text)
            btn.setProperty('class', 'pgm-btn')
            btn.setMinimumHeight(sp(SpacingToken.XXL))
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(self._on_pgm_btn_clicked(key))
            self._pgm_buttons[key] = btn
            row = idx // 2
            col = idx % 2
            grid.addWidget(btn, row, col)

        layout.addLayout(grid)

        # Bouton Mes classes (visible seulement si serveur connecté)
        pgm_label_short = pgm_label  # "PEI" ou "DP"
        btn_classes = QPushButton(f'Mes classes {pgm_label_short}')
        btn_classes.setProperty('class', 'classes-btn')
        btn_classes.setMinimumHeight(sp(SpacingToken.MD))
        btn_classes.setCursor(Qt.PointingHandCursor)
        btn_classes.clicked.connect(self._on_classes_btn(pgm_label_short))
        self._pgm_buttons[f'{pgm_label_short.lower()}_mes_classes'] = btn_classes
        layout.addWidget(btn_classes)

        layout.addStretch()
        return panel

    def _on_classes_btn(self, pgm: str):
        def handler():
            view = _BTN_VIEW.get(f'{pgm.lower()}_mes_classes', f'{pgm.lower()}_classes')
            self._open_main_window(focus=view)
        return handler

    def _open_pp(self) -> None:
        detected = self._detect_programs()
        if detected.get('PEI'):
            view = 'college_Bulletin'
        elif detected.get('DP'):
            view = 'lycee_bulletin'
        else:
            view = 'prof_principal'
        self._open_main_window(focus=view)

    def _on_pgm_btn_clicked(self, key: str):
        def handler():
            view = _BTN_VIEW.get(key, key)
            self._open_main_window(focus=view)
        return handler

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def _load_data(self) -> None:
        self._load_profile()
        self._load_sync()
        self._apply_program_visibility()
        QTimer.singleShot(50, self._load_counts)

    def _load_profile(self) -> None:
        conn = db.local_conn

        full_name = session.full_name or '—'
        email = session.email or '—'
        role_label = session.role.value if session.role else '—'
        mode = session.conn_mode
        mode_str = mode.value if mode else 'Hors connexion'

        self._hdr_title.setText(f'Bienvenue, {full_name}')
        self._hdr_mode.setText(f'Mode : {mode_str}')
        self._lbl_name.setText(full_name)
        self._lbl_email.setText(email)
        self._lbl_role.setText(f'Rôle : {role_label}')

        # Indicateurs de connexion
        server_ok = db.server_conn is not None
        if server_ok:
            server_mode = db.server_mode
            intra_active = server_mode == DBMode.INTRANET
            cloud_active = server_mode == DBMode.CLOUD
            self._profile_intra.setText(f'Intranet : {"●" if intra_active else "○"}')
            self._profile_cloud.setText(f'Cloud : {"●" if cloud_active else "○"}')
            self._profile_offline.setText('')
        else:
            self._profile_intra.setText('Intranet : ○')
            self._profile_cloud.setText('Cloud : ○')
            self._profile_offline.setText('Hors connexion')

        if conn is None:
            return

        try:
            row = conn.execute(
                "SELECT updated_at FROM session_cache WHERE user_id = ?",
                (session.user_id,)
            ).fetchone()
            if row and row[0]:
                self._hdr_last_login.setText(f'Dernière connexion : {row[0]}')
        except Exception:
            pass

        try:
            row = conn.execute(
                "SELECT annee_scolaire, trimestre_courant FROM module_config WHERE id = 1"
            ).fetchone()
            if row:
                self._lbl_year.setText(f'Année scolaire : {row[0]}')
                self._lbl_term.setText(f'Trimestre : {row[1]}')
            else:
                self._lbl_year.setText('Année scolaire : —')
                self._lbl_term.setText('Trimestre : —')
        except Exception:
            self._lbl_year.setText('Année scolaire : —')
            self._lbl_term.setText('Trimestre : —')

    def _load_counts(self) -> None:
        conn = db.local_conn
        if conn is None:
            return

        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM larcauth_classroom_termsubject WHERE fk_teacher_id = ?",
                (session.user_id,)
            ).fetchone()
            count_cts = row[0] if row else 0
            self._lbl_classes_count.setText(f'Classes-Matières : {count_cts}')
        except Exception:
            pass

        try:
            row = conn.execute(
                """SELECT COUNT(DISTINCT s.aecuser_ptr_id)
                   FROM larcauth_classroom_termsubject cts
                   JOIN larcauth_classroom c ON c.id = cts.fk_classroom_id
                   JOIN larcauth_student s ON s.s_classroom_id = c.id
                   WHERE cts.fk_teacher_id = ?""",
                (session.user_id,)
            ).fetchone()
            count_students = row[0] if row else 0
            self._lbl_students_count.setText(f'Élèves : {count_students}')
        except Exception:
            pass

    def _load_sync(self) -> None:
        conn = db.local_conn
        if conn is None:
            return

        try:
            row = conn.execute(
                "SELECT derniere_synchronisation FROM module_config WHERE id = 1"
            ).fetchone()
            if row and row[0]:
                self._lbl_sync_date.setText(f'Dernière synchronisation : {row[0]}')
            else:
                self._lbl_sync_date.setText('Dernière synchronisation : jamais')
        except Exception:
            self._lbl_sync_date.setText('Dernière synchronisation : —')

        try:
            row = conn.execute(
                "SELECT last_source FROM sync_state LIMIT 1"
            ).fetchone()
            src = row[0] if row and row[0] else 'inconnu'
            self._lbl_sync_mode.setText(f'Source : {src}')
        except Exception:
            self._lbl_sync_mode.setText('Source : —')

        total_unsynced = 0
        detail_parts = []

        for table in BUSINESS_TABLES:
            count = self._count_unsynced_rows(table)
            if count > 0:
                label = _STAT_TABLE_LABELS.get(table, table)
                detail_parts.append(f'{label} : {count}')
                total_unsynced += count

        self._lbl_unsynced_count.setText(str(total_unsynced))

        if total_unsynced == 0:
            self._lbl_unsynced_label.setText('Aucune modification en attente')
            self._lbl_unsynced_detail.setText('Toutes les données sont à jour.')
        else:
            self._lbl_unsynced_label.setText('modifications non synchronisées')
            self._lbl_unsynced_detail.setText(' | '.join(detail_parts))

    def _count_unsynced_rows(self, table: str) -> int:
        conn = db.local_conn
        if conn is None:
            return 0
        ref_table = f'{table}_ref'
        try:
            cols = [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")').fetchall()]
            if not cols:
                return 0
            conditions = ' OR '.join(
                f'(w."{c}" IS NOT r."{c}") OR (w."{c}" IS NULL AND r."{c}" IS NOT NULL) OR (w."{c}" IS NOT NULL AND r."{c}" IS NULL)'
                for c in cols
            )
            sql = f'SELECT COUNT(*) FROM "{table}" w JOIN "{ref_table}" r ON w.id = r.id WHERE ({conditions})'
            row = conn.execute(sql).fetchone()
            return row[0] if row else 0
        except Exception:
            return 0

    # ------------------------------------------------------------------
    # Détection programmes
    # ------------------------------------------------------------------
    def _detect_programs(self) -> dict[str, bool]:
        conn = db.local_conn
        if conn is None:
            return {'PEI': False, 'DP': False}

        has_pei = False
        has_dp = False

        try:
            rows = conn.execute("""
                SELECT DISTINCT p.sigle
                FROM larcauth_classroom_termsubject cts
                JOIN larcauth_classroom c ON c.id = cts.fk_classroom_id
                JOIN larcauth_level l ON l.id = c.fk_level_id
                JOIN larcauth_program p ON p.id = l.fk_program_id
                WHERE cts.fk_teacher_id = ?
            """, (session.user_id,)).fetchall()

            for r in rows:
                sigle = (r[0] or '').upper()
                if sigle in ('PEI', 'MYP'):
                    has_pei = True
                if sigle in ('DPFR', 'DPEN', 'DP'):
                    has_dp = True
        except Exception:
            pass

        return {'PEI': has_pei, 'DP': has_dp}

    def _detect_button_visibility(self, pgm: str, btn_key: str) -> bool:
        conn = db.local_conn
        if conn is None:
            return False
        uid = session.user_id
        tid = session.active_term_id
        if not uid or not tid:
            return False

        try:
            if btn_key == 'pei_grp_matieres' or btn_key == 'dp_grp_matieres':
                pids = '(12, 22)' if pgm == 'PEI' else '(13, 23)'
                row = conn.execute(f"""
                    SELECT 1 FROM larcauth_classroom_termsubject cts
                    JOIN larcauth_classroom c ON c.id = cts.fk_classroom_id
                    JOIN larcauth_level l ON l.id = c.fk_level_id
                    WHERE cts.fk_teacher_id = ? AND cts.fk_term_id = ?
                      AND (cts.enabled = 1 OR cts.enabled = 'true')
                      AND l.fk_program_id IN {pids}
                    LIMIT 1
                """, (uid, tid)).fetchone()
                return row is not None

            if btn_key == 'pei_interdisc':
                row = conn.execute("""
                    SELECT 1 FROM larcauth_classroom_termothersubject cto
                    JOIN larcauth_classroom c ON c.id = cto.fk_classroom_id
                    JOIN larcauth_level l ON l.id = c.fk_level_id
                    WHERE cto.fk_supervisor_id = ? AND cto.fk_term_id = ?
                      AND (cto.enabled = 1 OR cto.enabled = 'true')
                      AND l.fk_program_id IN (12, 22)
                      AND (cto.unit_multisubjects = 1 OR cto.unit_multisubjects = 'true')
                    LIMIT 1
                """, (uid, tid)).fetchone()
                return row is not None

            if btn_key == 'pei_pp':
                row = conn.execute("""
                    SELECT 1 FROM larcauth_classroom_termothersubject cto
                    JOIN larcauth_classroom c ON c.id = cto.fk_classroom_id
                    JOIN larcauth_level l ON l.id = c.fk_level_id
                    WHERE cto.fk_supervisor_id = ? AND cto.fk_term_id = ?
                      AND (cto.enabled = 1 OR cto.enabled = 'true')
                      AND l.fk_program_id IN (12, 22)
                      AND (cto.label LIKE 'Personal%' OR cto.label LIKE 'Projet%')
                    LIMIT 1
                """, (uid, tid)).fetchone()
                return row is not None

            if btn_key == 'pei_mes_classes':
                return db.server_conn is not None and self._detect_button_visibility(pgm, 'pei_grp_matieres')

            if btn_key == 'dp_mes_classes':
                return db.server_conn is not None and self._detect_button_visibility(pgm, 'dp_grp_matieres')

            if btn_key in ('dp_tdc', 'dp_cas', 'dp_memoire'):
                patterns = {'dp_tdc': ['Th%'], 'dp_cas': ['Cr%'], 'dp_memoire': ['Mé%', 'Ext%']}.get(btn_key, [])
                clauses = ' OR '.join(['cto.label LIKE ?' for _ in patterns])
                params = [uid, tid] + patterns
                row = conn.execute(f"""
                    SELECT 1 FROM larcauth_classroom_termothersubject cto
                    WHERE cto.fk_supervisor_id = ? AND cto.fk_term_id = ?
                      AND (cto.enabled = 1 OR cto.enabled = 'true')
                      AND ({clauses})
                    LIMIT 1
                """, params).fetchone()
                return row is not None

        except Exception:
            return False

        return True

    def _apply_program_visibility(self) -> None:
        detected = self._detect_programs()
        server_ok = db.server_conn is not None

        for pgm_key, section in self._pgm_sections.items():
            section.setVisible(detected.get(pgm_key, False))

        for btn_key, btn in self._pgm_buttons.items():
            pgm = 'PEI' if btn_key.startswith('pei_') else 'DP' if btn_key.startswith('dp_') else ''
            if not detected.get(pgm, False):
                btn.setVisible(False)
            elif btn_key.endswith('_mes_classes'):
                btn.setVisible(server_ok and self._detect_button_visibility(pgm, btn_key))
            else:
                btn.setVisible(self._detect_button_visibility(pgm, btn_key))

        # Professeur principal visible si le prof est headteacher d'au moins une classe
        pp_visible = False
        conn = db.local_conn
        if conn is not None:
            try:
                row = conn.execute(
                    "SELECT 1 FROM larcauth_classroom WHERE fk_headteacher_id = ? LIMIT 1",
                    (session.user_id,)
                ).fetchone()
                pp_visible = row is not None
            except Exception:
                pass
        self._btn_prof_principal.setVisible(pp_visible)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _open_main_window(self, focus: str = 'notes') -> None:
        from views.main_window import MainWindow
        self._main_window = MainWindow()
        self._main_window.show()
        self.hide()
        self._poll_main_visible = QTimer(self)
        self._poll_main_visible.timeout.connect(self._check_main_visible)
        self._poll_main_visible.start(500)

    def _check_main_visible(self) -> None:
        if self._main_window is None or not self._main_window.isVisible():
            if self._poll_main_visible is not None:
                self._poll_main_visible.stop()
                self._poll_main_visible = None
            self._main_window = None
            self.show()
            self._load_sync()

    def _do_sync(self) -> None:
        self.statusBar().showMessage('Synchronisation en cours...')
        QApplication.processEvents()

        try:
            if db.server_conn is None:
                if not db.connect_intranet():
                    if not db.connect_cloud():
                        self.statusBar().showMessage(
                            'Aucun serveur disponible (Intranet/Cloud).', 5000
                        )
                        return

            report = sync_manager.pull_push()
            if report.has_errors:
                self.statusBar().showMessage(
                    f'Sync terminée avec {len(report.errors)} erreur(s).', 8000
                )
            elif report.has_conflicts:
                self.statusBar().showMessage(
                    f'Sync terminée — {len(report.conflicts)} conflit(s) à résoudre.', 8000
                )
            else:
                self.statusBar().showMessage(
                    f'Sync réussie — {report.summary()}', 5000
                )
            self._load_sync()
        except Exception as e:
            self.statusBar().showMessage(f'Erreur de synchronisation : {e}', 8000)

    def _logout(self) -> None:
        session.is_authenticated = False
        db.disconnect_all()
        if self._poll_main_visible is not None:
            self._poll_main_visible.stop()
            self._poll_main_visible = None
        self._main_window = None
        login = self.parentWidget()
        if login is not None:
            login.show()
        else:
            from views.login import LoginWindow
            login = LoginWindow()
            login.show()
        self.close()
