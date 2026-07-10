import os
import shutil
from typing import Optional

from larccommon.l10n import Translator, _
from phibuilder.phi.scale import SpacingToken
from PySide6.QtCore import Q_ARG, QMetaObject, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from common.auth import AuthManager, OAuth2Manager
from common.database import DBMode, db
from common.network import NetworkMode, detect_network, network_mode_color
from common.session import AuthResult, ConnMode, UserRole, session
from common.sqlite_init import sqlite_init
from common.theme import theme_manager


# ---------------------------------------------------------------------------
# Generic background worker
# ---------------------------------------------------------------------------
class _Worker(QThread):
    done = Signal(object)

    def __init__(self, fn, *args, parent=None):
        super().__init__(parent)
        self._fn = fn
        self._args = args
        self.finished.connect(self.deleteLater)

    def run(self):
        try:
            self.done.emit(self._fn(*self._args))
        except Exception as exc:
            self.done.emit((False, None, str(exc)))


# ---------------------------------------------------------------------------
# Login window
# ---------------------------------------------------------------------------
class LoginWindow(QMainWindow):
    @property
    def _STYLE(self) -> str:
        p = theme_manager.theme.palette
        fs = theme_manager.font_size
        return f"""
            QMainWindow {{ background: {p.background}; }}
            QWidget#root {{ background: {p.background}; }}
            QFrame#header {{
                background: {p.header_bg};
                color: {p.header_text};
                border-radius: 8px;
            }}
            QFrame#header QLabel {{ color: {p.header_text}; }}
            QFrame.panel {{
                background: {p.surface};
                border: 1px solid {p.border};
                border-radius: 8px;
            }}
            QLabel.logo-title {{
                font-size: {fs(22)}px;
                font-weight: bold;
                color: {p.text_strong};
            }}
            QLabel.logo-sub {{
                font-size: {fs(11)}px;
                color: {p.text_soft};
            }}
            QLabel.section-title {{
                font-size: {fs(13)}px;
                font-weight: bold;
                color: {p.text_strong};
            }}
            QLabel.info-text {{
                font-size: {fs(11)}px;
                color: {p.text_soft};
            }}
            QLabel.error-text {{
                color: {p.error};
                font-size: {fs(11)}px;
                font-weight: bold;
            }}
            QLabel.indicator-on {{
                font-size: {fs(12)}px;
                font-weight: bold;
            }}
            QLabel.indicator-off {{
                font-size: {fs(12)}px;
            }}
            QLineEdit {{
                padding: 10px 14px;
                border: 1px solid {p.border};
                border-radius: 6px;
                font-size: {fs(13)}px;
                background: {p.surface};
                color: {p.text_strong};
            }}
            QLineEdit:focus {{ border-color: {p.primary}; }}
            QPushButton.btn-primary {{
                background: {p.button_primary};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 21px;
                font-size: {fs(13)}px;
                font-weight: bold;
            }}
            QPushButton.btn-primary:hover {{ background: {p.primary}; }}
            QPushButton.btn-primary:disabled {{ background: {p.inactive}; }}
            QPushButton.btn-google {{
                background: {p.button_danger};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 21px;
                font-size: {fs(13)}px;
                font-weight: bold;
            }}
            QPushButton.btn-google:hover {{ background: {p.danger}; }}
            QPushButton.btn-google:disabled {{ background: {p.inactive}; }}
            QPushButton.btn-pin {{
                background: {p.button_accent};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 21px;
                font-size: {fs(13)}px;
                font-weight: bold;
            }}
            QPushButton.btn-pin:hover {{ background: {p.accent}; }}
            QPushButton.btn-pin:disabled {{ background: {p.inactive}; }}
            QPushButton.btn-create {{
                background: {p.button_success};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 21px;
                font-size: {fs(13)}px;
                font-weight: bold;
            }}
            QPushButton.btn-create:hover {{ background: {p.success}; }}
            QPushButton.btn-create:disabled {{ background: {p.inactive}; }}
            QPushButton.btn-secondary {{
                background: transparent;
                color: {p.text_soft};
                border: 1px solid {p.border};
                border-radius: 6px;
                padding: 6px 13px;
                font-size: {fs(11)}px;
            }}
            QPushButton.btn-secondary:hover {{ background: {p.primary_light}; color: {p.text_strong}; }}
            QPushButton.btn-browse {{
                background: {p.text_soft};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 13px;
                font-size: {fs(11)}px;
                font-weight: bold;
                min-width: 34px;
            }}
            QPushButton.btn-browse:hover {{ background: {p.inactive}; }}
            QTabWidget::pane {{
                border: 1px solid {p.border};
                background: {p.surface};
                border-radius: 6px;
            }}
            QTabBar::tab {{
                padding: 8px 16px;
                font-size: {fs(11)}px;
            }}
            QTabBar::tab:selected {{
                background: {p.surface};
                border-bottom: 2px solid {p.primary};
                color: {p.text_strong};
                font-weight: bold;
            }}
            QTabBar::tab:!selected {{
                background: {p.border_light};
                color: {p.text_soft};
            }}
            QFrame#sep {{
                border: none;
                border-top: 1px solid {p.border_light};
            }}
        """

    def __init__(self):
        super().__init__()
        import os

        lang = os.environ.get("LARC_LANG", "fr")
        trans = Translator.instance(lang)
        trans.load_dir(Translator.l10n_dir())

        # Charger les préférences
        from PySide6.QtCore import QSettings

        s = QSettings("Larc", "LarcProf")
        saved_theme = s.value("theme_pref", "")
        if saved_theme and saved_theme in (
            "default",
            "material_light",
            "material_dark",
            "nature",
            "blue",
            "dark",
            "sobre",
            "contrast",
        ):
            theme_manager.set_active(saved_theme)

        self._worker: Optional[_Worker] = None
        self._net_mode: Optional[NetworkMode] = None
        self._sp = theme_manager.phi_theme.spacing.spacing

        self._setup_ui()
        self._start_net_detection()

        self._network_timer = QTimer(self)
        self._network_timer.setInterval(30000)
        self._network_timer.timeout.connect(self._check_network)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        sp = self._sp
        self.setWindowTitle(_("prof_login.window_title"))
        self.setMinimumSize(420, 680)
        self.resize(480, 780)
        self.setStyleSheet(self._STYLE)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(
            sp(SpacingToken.SM), sp(SpacingToken.SM), sp(SpacingToken.SM), sp(SpacingToken.SM)
        )
        outer.setSpacing(sp(SpacingToken.SM))

        # Logo
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "img", "logoAEC.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            logo = QLabel()
            logo.setPixmap(pix.scaledToHeight(89, Qt.SmoothTransformation))
            logo.setAlignment(Qt.AlignCenter)
            outer.addWidget(logo)

        outer.addWidget(self._build_header())

        # Indicateurs réseau (entre header et onglets)
        self._net_row = QWidget()
        net_layout = QHBoxLayout(self._net_row)
        net_layout.setContentsMargins(sp(SpacingToken.SM), 2, sp(SpacingToken.SM), 2)
        net_layout.setSpacing(sp(SpacingToken.MD))
        net_layout.addStretch()
        self._intra_indicator = QLabel(_("login.status.intranet"))
        self._intra_indicator.setFont(QFont("Segoe UI", theme_manager.font_size(11)))
        net_layout.addWidget(self._intra_indicator)
        self._cloud_indicator = QLabel(_("login.status.cloud"))
        self._cloud_indicator.setFont(QFont("Segoe UI", theme_manager.font_size(11)))
        net_layout.addWidget(self._cloud_indicator)
        outer.addWidget(self._net_row)

        self._tabs = QTabWidget()
        self._build_intranet_tab()
        self._build_cloud_tab()
        self._build_pin_tab()
        self._build_new_tab()
        outer.addWidget(self._tabs, 1)

        self._err_lbl = QLabel()
        self._err_lbl.setProperty("class", "error-text")
        self._err_lbl.setWordWrap(True)
        self._err_lbl.hide()
        outer.addWidget(self._err_lbl)

        self._log_area = QPlainTextEdit()
        self._log_area.setReadOnly(True)
        self._log_area.setMaximumHeight(70)
        self._log_area.setPlaceholderText("Messages de progression…")
        self._log_area.hide()
        outer.addWidget(self._log_area)

        self._bottom_indicator = QLabel()
        self._bottom_indicator.setAlignment(Qt.AlignCenter)
        self._bottom_indicator.setWordWrap(True)
        p = theme_manager.theme.palette
        self._bottom_indicator.setStyleSheet(
            f"color: {p.text_strong}; font-size: {theme_manager.font_size(13)}px; font-weight: bold;"
            f"padding: {sp(SpacingToken.SM)}px {sp(SpacingToken.MD)}px;"
        )
        outer.addWidget(self._bottom_indicator)

        sb = QStatusBar()
        self.setStatusBar(sb)
        self._net_txt = QLabel("Détection du réseau")
        self._net_txt.setStyleSheet(f"font-size: 11px; color: {p.text_soft};")
        self._net_txt.setContentsMargins(13, 0, 0, 0)
        self._dot_lbl = QLabel("●")
        self._dot_lbl.setStyleSheet(
            f"color: {p.inactive}; font-size: {theme_manager.font_size(14)}px;"
        )
        sb.addWidget(self._net_txt)
        sb.addWidget(self._dot_lbl)

    def _build_header(self) -> QWidget:
        sp = self._sp

        header = QFrame()
        header.setObjectName("header")
        header.setMinimumHeight(55)
        h = QHBoxLayout(header)
        h.setContentsMargins(
            sp(SpacingToken.MD), sp(SpacingToken.SM), sp(SpacingToken.MD), sp(SpacingToken.SM)
        )

        title_font = QFont("Segoe UI", theme_manager.font_size(14), QFont.Bold)
        meta_font = QFont("Segoe UI", theme_manager.font_size(11))

        title = QLabel(_("prof_login.title"))
        title.setFont(title_font)
        sub = QLabel(_("prof_login.subtitle"))
        sub.setFont(meta_font)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        text_col.addWidget(title)
        text_col.addWidget(sub)

        h.addLayout(text_col)
        h.addStretch(1)

        return header

    def _tab_widget(self) -> tuple:
        sp = self._sp
        tab = QWidget()
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(
            sp(SpacingToken.SM), sp(SpacingToken.SM), sp(SpacingToken.SM), sp(SpacingToken.SM)
        )
        outer.setSpacing(sp(SpacingToken.SM))

        panel = QFrame()
        panel.setProperty("class", "panel")
        inner = QVBoxLayout(panel)
        inner.setContentsMargins(
            sp(SpacingToken.MD), sp(SpacingToken.MD), sp(SpacingToken.MD), sp(SpacingToken.MD)
        )
        inner.setSpacing(sp(SpacingToken.SM))

        outer.addWidget(panel)
        return tab, inner, outer

    def _build_intranet_tab(self) -> None:
        sp = self._sp
        tab, layout, _outer = self._tab_widget()

        title = QLabel(_("login.tab_intranet"))
        title.setProperty("class", "section-title")
        layout.addWidget(title)

        self._edt_i_email = QLineEdit()
        self._edt_i_email.setPlaceholderText(_("login.email_placeholder"))
        layout.addWidget(self._edt_i_email)

        self._edt_i_pass = QLineEdit()
        self._edt_i_pass.setEchoMode(QLineEdit.Password)
        self._edt_i_pass.setPlaceholderText(_("login.password_placeholder"))
        layout.addWidget(self._edt_i_pass)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(sp(SpacingToken.SM))

        self._btn_intra = QPushButton(_("login.connect_intranet"))
        self._btn_intra.setProperty("class", "btn-primary")
        self._btn_intra.clicked.connect(self._on_intranet)
        self._edt_i_pass.returnPressed.connect(self._btn_intra.click)
        btn_row.addWidget(self._btn_intra, 1)

        self._btn_change_pwd_intra = QPushButton(_("prof_login.change_password"))
        self._btn_change_pwd_intra.setProperty("class", "btn-secondary")
        self._btn_change_pwd_intra.clicked.connect(self._on_change_password)
        btn_row.addWidget(self._btn_change_pwd_intra)

        layout.addLayout(btn_row)
        layout.addStretch()
        self._tabs.addTab(tab, _("login.tab_intranet"))

    def _build_cloud_tab(self) -> None:
        tab, layout, _outer = self._tab_widget()

        title = QLabel(_("login.tab_cloud"))
        title.setProperty("class", "section-title")
        layout.addWidget(title)

        info = QLabel(_("prof_login.info_cloud"))
        info.setProperty("class", "info-text")
        info.setAlignment(Qt.AlignCenter)
        info.setWordWrap(True)
        layout.addWidget(info)

        self._btn_google = QPushButton(_("login.connect_google"))
        self._btn_google.setProperty("class", "btn-google")
        self._btn_google.clicked.connect(self._on_cloud)
        layout.addWidget(self._btn_google)

        layout.addStretch()
        self._tabs.addTab(tab, _("login.tab_cloud"))

    def _build_pin_tab(self) -> None:
        sp = self._sp
        tab, layout, _outer = self._tab_widget()

        title = QLabel(_("prof_login.pin_title"))
        title.setProperty("class", "section-title")
        layout.addWidget(title)

        self._edt_p_email = QLineEdit()
        self._edt_p_email.setPlaceholderText(_("login.email_placeholder"))
        layout.addWidget(self._edt_p_email)

        self._edt_p_pin = QLineEdit()
        self._edt_p_pin.setEchoMode(QLineEdit.Password)
        self._edt_p_pin.setPlaceholderText(_("prof_login.pin_placeholder"))
        self._edt_p_pin.setMaxLength(8)
        layout.addWidget(self._edt_p_pin)

        note = QLabel(_("prof_login.pin_note"))
        note.setProperty("class", "info-text")
        layout.addWidget(note)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(sp(SpacingToken.SM))

        self._btn_pin = QPushButton(_("prof_login.connect_pin"))
        self._btn_pin.setProperty("class", "btn-pin")
        self._btn_pin.clicked.connect(self._on_pin)
        self._edt_p_pin.returnPressed.connect(self._btn_pin.click)
        btn_row.addWidget(self._btn_pin, 1)

        self._btn_change_pin = QPushButton(_("prof_login.change_pin"))
        self._btn_change_pin.setProperty("class", "btn-secondary")
        self._btn_change_pin.clicked.connect(self._on_change_pin)
        btn_row.addWidget(self._btn_change_pin)

        layout.addLayout(btn_row)
        layout.addStretch()
        self._tabs.addTab(tab, _("prof_login.tab_pin"))

    def _build_new_tab(self) -> None:
        sp = self._sp
        tab, layout, _outer = self._tab_widget()

        title = QLabel(_("prof_login.new_title"))
        title.setProperty("class", "section-title")
        layout.addWidget(title)

        info = QLabel(_("prof_login.new_info"))
        info.setProperty("class", "info-text")
        info.setWordWrap(True)
        layout.addWidget(info)

        self._edt_n_email = QLineEdit()
        self._edt_n_email.setPlaceholderText(_("login.email_placeholder"))
        layout.addWidget(self._edt_n_email)

        dest_row = QHBoxLayout()
        dest_row.setSpacing(sp(SpacingToken.XS))
        self._edt_n_dest = QLineEdit()
        self._edt_n_dest.setPlaceholderText(_("prof_login.new_dest"))
        self._edt_n_dest.setReadOnly(True)
        dest_row.addWidget(self._edt_n_dest)
        btn_browse = QPushButton("…")
        btn_browse.setProperty("class", "btn-browse")
        btn_browse.clicked.connect(self._browse_dest)
        dest_row.addWidget(btn_browse)
        layout.addLayout(dest_row)

        self._btn_create = QPushButton(_("prof_login.create_instance"))
        self._btn_create.setProperty("class", "btn-create")
        self._btn_create.clicked.connect(self._on_create)
        layout.addWidget(self._btn_create)

        layout.addStretch()
        self._tabs.addTab(tab, _("prof_login.tab_new"))

    # ------------------------------------------------------------------
    # Network detection (inchangé)
    # ------------------------------------------------------------------
    def _start_net_detection(self) -> None:
        worker = _Worker(lambda: (True, *detect_network(), ""), parent=self)
        worker.done.connect(self._on_net_detected)
        worker.start()

    def showEvent(self, event):
        super().showEvent(event)
        self._network_timer.start()
        intra_ok, internet_ok = detect_network()
        self._on_net_detected((True, intra_ok, internet_ok, ""))
        self._check_network()
        self._update_indicators(intra_ok, internet_ok)
        try:
            sqlite_init.init()
        except Exception as e:
            self._log(f"Erreur d'initialisation de la base locale : {e}")
        try:
            self._update_status_bar_from_module_config()
        except Exception as e:
            self._log(f"Erreur lors de la mise à jour de la barre d'état : {e}")

    def hideEvent(self, event):
        super().hideEvent(event)
        self._network_timer.stop()

    def _check_network(self) -> None:
        worker = _Worker(lambda: (True, *detect_network(), ""), parent=self)
        worker.done.connect(self._on_net_detected)
        worker.start()

    def _on_net_detected(self, result) -> None:
        ok, intra_ok, internet_ok, _ignored = result
        if not ok:
            return
        self._intranet_ok = intra_ok
        self._internet_ok = internet_ok
        if intra_ok:
            mode = NetworkMode.INTRANET
        elif internet_ok:
            mode = NetworkMode.INTERNET
        else:
            mode = NetworkMode.OFFLINE
        self._net_mode = mode
        color = network_mode_color(mode)
        self._dot_lbl.setStyleSheet(f"color: {color}; font-size: {theme_manager.font_size(14)}px;")
        labels = {
            NetworkMode.INTRANET: _("login.status.intranet").replace(" ●", ""),
            NetworkMode.INTERNET: _("prof_login.status.internet"),
            NetworkMode.OFFLINE: _("prof_login.status.offline"),
        }
        self._net_txt.setText(labels.get(mode, ""))
        self._update_indicators(intra_ok, internet_ok)
        from common.session import session

        if session.is_authenticated:
            self._update_status_bar(
                AuthResult(
                    user_id=session.user_id,
                    email=session.email,
                    full_name=session.full_name,
                    role=session.role,
                    term_id=session.active_term_id,
                    term_label=session.active_term_label,
                ),
                session.conn_mode,
            )
        else:
            self._update_status_bar(
                AuthResult(
                    user_id=0, email="", full_name="", role=UserRole.PROF, term_id=0, term_label=""
                ),
                ConnMode.OFFLINE,
            )

    def _update_indicators(self, intranet: bool, cloud: bool) -> None:
        p = theme_manager.theme.palette
        on_color, off_color = "#27ae60", p.text_soft
        self._intra_indicator.setStyleSheet(
            f"color: {on_color if intranet else off_color}; "
            f"font-size: {theme_manager.font_size(11)}px;"
            f"font-weight: {'bold' if intranet else 'normal'};"
        )
        self._cloud_indicator.setStyleSheet(
            f"color: {on_color if cloud else off_color}; "
            f"font-size: {theme_manager.font_size(11)}px;"
            f"font-weight: {'bold' if cloud else 'normal'};"
        )

    def _on_change_password(self) -> None:
        from views.password import ChangePasswordDialog

        dlg = ChangePasswordDialog(self)
        dlg.exec()

    def _on_change_pin(self) -> None:
        from views.password import ChangePinDialog

        dlg = ChangePinDialog(self)
        dlg.exec()

    # ------------------------------------------------------------------
    # Auth handlers (inchangés)
    # ------------------------------------------------------------------
    def _on_intranet(self) -> None:
        email = self._edt_i_email.text().strip()
        pwd = self._edt_i_pass.text()
        if not email or not pwd:
            self._show_error(_("login.error.required"))
            return
        if not self._check_email_module(email):
            return
        self._hide_error()
        self._set_busy(True)
        self._worker = _Worker(self._connect_then_auth_intranet, email, pwd, parent=self)
        self._worker.done.connect(lambda r: self._on_auth_done(r, ConnMode.INTRANET))
        self._worker.start()

    @staticmethod
    def _connect_then_auth_intranet(email: str, pwd: str):
        if not db.connect_intranet():
            return (False, AuthResult(), "Connexion à l'intranet impossible (vérifier le réseau).")
        return AuthManager.auth_intranet(email, pwd)

    def _on_cloud(self) -> None:
        self._hide_error()
        self._set_busy(True)
        self._worker = _Worker(self._connect_then_auth_cloud, parent=self)
        self._worker.done.connect(lambda r: self._on_auth_done(r, ConnMode.CLOUD))
        self._worker.start()

    @staticmethod
    def _connect_then_auth_cloud():
        if not db.connect_cloud():
            return (
                False,
                AuthResult(),
                "Connexion au cloud impossible (vérifier l'accès internet).",
            )
        return OAuth2Manager.authenticate()

    def _check_email_module(self, email: str) -> bool:
        try:
            conn = db.local_conn
            if conn is None:
                self._show_error(
                    "Aucune base locale. Créez d'abord une instance "
                    'via l\'onglet "Nouvelle instance" ou le mode 4.'
                )
                return False
            cur = conn.cursor()
            cur.execute("SELECT email_professeur FROM module_config WHERE id = 1")
            row = cur.fetchone()
            if not row or not row[0]:
                self._show_error(
                    "Module non instancié. Créez d'abord une instance "
                    'via l\'onglet "Nouvelle instance" ou le mode 4.'
                )
                return False
            if row[0].lower() != email.lower():
                self._show_error(
                    f"Cette instance est liée à {row[0]}. "
                    f"Connectez-vous avec ce compte ou créez votre propre instance."
                )
                return False
        except Exception:
            self._show_error(
                "Erreur de lecture du module. Créez une nouvelle instance "
                'via l\'onglet "Nouvelle instance" ou le mode 4.'
            )
            return False
        return True

    def _on_pin(self) -> None:
        email = self._edt_p_email.text().strip()
        pin = self._edt_p_pin.text()
        if not email or not pin:
            self._show_error("Veuillez saisir votre email et votre PIN.")
            return
        if not sqlite_init.init():
            self._show_error("Impossible d'initialiser la base locale.")
            return
        if not self._check_email_module(email):
            return
        self._hide_error()
        self._set_busy(True)
        self._worker = _Worker(AuthManager.auth_pin, email, pin, parent=self)
        self._worker.done.connect(lambda r: self._on_auth_done(r, ConnMode.OFFLINE))
        self._worker.start()

    def _on_auth_done(self, result, mode: ConnMode) -> None:
        self._set_busy(False)
        ok, res, err = result
        if not ok:
            self._show_error(err or _("login.error.auth_failed"))
            return

        if mode in (ConnMode.INTRANET, ConnMode.CLOUD):
            exists, infos = AuthManager.check_teacher_exists(res.email)
            if not exists:
                self._show_error("Ce compte n'est pas un professeur actif.")
                return
            res.user_id = infos["user_id"]
            res.full_name = f"{infos['first_name']} {infos['last_name']}"
            res.term_id = infos["trimestre_courant"]
            res.term_label = infos["trimestre_label"]

            if not sqlite_init.init():
                self._show_error("Impossible d'initialiser la base locale.")
                return
            sqlite_init.init_module_config(
                annee_scolaire=infos["annee_scolaire"],
                trimestre_courant=infos["trimestre_courant"],
                nom_professeur=res.full_name,
                email_professeur=res.email,
            )
            self._apply_session(res, mode)
            return

        if mode == ConnMode.OFFLINE and db.server_conn is not None:
            exists, infos = AuthManager.check_teacher_exists(res.email)
            if not exists:
                self._show_error("Ce compte n'est pas un professeur actif.")
                return
            res.user_id = infos["user_id"]
            res.full_name = f"{infos['first_name']} {infos['last_name']}"
            res.term_id = infos["trimestre_courant"]
            res.term_label = infos["trimestre_label"]

            if not sqlite_init.init():
                self._show_error("Impossible d'initialiser la base locale.")
                return
            sqlite_init.init_module_config(
                annee_scolaire=infos["annee_scolaire"],
                trimestre_courant=infos["trimestre_courant"],
                nom_professeur=res.full_name,
                email_professeur=res.email,
            )
            self._show_confirmation_dialog(res, mode, infos)
            return

        if mode == ConnMode.OFFLINE and db.server_conn is None:
            if not sqlite_init.init():
                self._show_error("Impossible d'initialiser la base locale.")
                return
            sqlite_init.init_module_config(
                annee_scolaire="",
                trimestre_courant=res.term_id,
                nom_professeur=res.full_name,
                email_professeur=res.email,
            )

        if mode == ConnMode.OFFLINE and db.server_conn is not None:
            if not sqlite_init.init():
                self._show_error("Impossible d'initialiser la base locale.")
                return
            sqlite_init.init_module_config(
                annee_scolaire=infos["annee_scolaire"],
                trimestre_courant=infos["trimestre_courant"],
                nom_professeur=res.full_name,
                email_professeur=res.email,
            )
            self._show_confirmation_dialog(res, mode, infos)
            return

        self._apply_session(res, mode)

    def _show_confirmation_dialog(self, res: AuthResult, mode: ConnMode, infos: dict) -> None:
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

        dlg = QDialog(self)
        dlg.setWindowTitle("Confirmation")
        dlg.setMinimumWidth(377)
        layout = QVBoxLayout(dlg)

        msg = QLabel(
            "Les étapes suivantes vont être exécutées :\n\n"
            "1. Initialisation de la base locale SQLite\n"
            "2. Téléchargement des données du professeur\n"
            "3. Sauvegarde de la session\n\n"
            "Veuillez patienter quelques minutes.\n"
            "L'interface peut sembler figée pendant l'opération."
        )
        msg.setWordWrap(True)
        layout.addWidget(msg)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(lambda: self._execute_steps(res, mode, dlg, infos))
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        dlg.exec()

    def _execute_steps(self, res: AuthResult, mode: ConnMode, dlg, infos: dict) -> None:
        if dlg is not None:
            dlg.accept()
        self._set_busy(True)
        self._log("Début du téléchargement des données du professeur…")
        self._log(
            f"Infos reçues : user_id={infos.get('user_id')}, trimestre={infos.get('trimestre_courant')}"
        )
        QApplication.processEvents()

        if not sqlite_init.init():
            self._show_error("Impossible d'initialiser la base locale.")
            self._set_busy(False)
            return

        self._temp_conn = db.local_conn
        self._show_spinner(True)
        QApplication.processEvents()

        try:
            ok, err_msg = sqlite_init.take_teacher_data(infos, self._log, self._temp_conn, None)
        except Exception as e:
            self._log(f"Exception dans take_teacher_data : {e}")
            self._show_spinner(False)
            self._set_busy(False)
            self._temp_conn = None
            self._show_error(f"Erreur lors du téléchargement : {e}")
            return

        self._show_spinner(False)
        self._set_busy(False)
        self._temp_conn = None

        self._log(f"Résultat du téléchargement : ok={ok}, msg={err_msg}")
        if not ok:
            self._show_error(f"Échec du téléchargement des données du professeur : {err_msg}")
            return
        self._log("Téléchargement terminé avec succès.")
        try:
            conn = db.local_conn
            if conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM larcauth_evaluation")
                count_eval = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM larcauth_learnerpei_has_termsubjectpei")
                count_pei = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM larcauth_learnerdp_has_termsubjectdp")
                count_dp = cur.fetchone()[0]
                self._log(
                    f"Comptes après téléchargement : eval={count_eval}, pei={count_pei}, dp={count_dp}"
                )
        except Exception as e:
            self._log(f"Erreur lors de la vérification des comptes : {e}")
        self._apply_session(res, mode)

    def _apply_session(self, res: AuthResult, mode: ConnMode) -> None:
        session.user_id = res.user_id
        session.email = res.email
        session.full_name = res.full_name
        session.role = res.role
        session.active_term_id = res.term_id
        session.active_term_label = res.term_label
        session.conn_mode = mode
        session.is_authenticated = True

        if mode == ConnMode.INTRANET:
            self._update_indicators(True, False)
        elif mode == ConnMode.CLOUD:
            self._update_indicators(False, True)
        else:
            self._update_indicators(False, False)

        sqlite_init.init()

        local_email = None
        try:
            conn = db.local_conn
            if conn:
                cur = conn.cursor()
                cur.execute("SELECT email_professeur FROM module_config WHERE id = 1")
                row = cur.fetchone()
                if row:
                    local_email = row[0]
        except Exception:
            pass

        skip_pin = local_email is not None and local_email.lower() == res.email.lower()

        if mode in (ConnMode.INTRANET, ConnMode.CLOUD) and not skip_pin:
            pin, ok = self._ask_pin_setup(res.full_name)
            sqlite_init.save_session(res, pin if ok else "")
        else:
            sqlite_init.save_session(res)

        self._update_status_bar(res, mode)
        self._open_main_window(res)

    def _ask_pin_setup(self, name: str):
        from PySide6.QtWidgets import QInputDialog

        return QInputDialog.getText(
            self,
            "PIN hors connexion",
            f"Définissez un PIN pour {name} (laisser vide pour ignorer) :",
            QLineEdit.Password,
        )

    # ------------------------------------------------------------------
    # New instance (inchangé)
    # ------------------------------------------------------------------
    def _browse_dest(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choisir le dossier parent")
        if folder:
            self._edt_n_dest.setText(folder)

    def _on_create(self) -> None:
        self._hide_error()
        email = self._edt_n_email.text().strip()
        parent = self._edt_n_dest.text().strip()
        if not email or not parent:
            self._show_error("Email et dossier de destination requis.")
            return

        if db.server_conn is not None and db.server_mode == DBMode.INTRANET:
            exists, infos = AuthManager.check_teacher_exists(email)
            if not exists:
                self._show_error("Cet email ne correspond à aucun professeur actif.")
                return
        elif db.server_conn is not None and db.server_mode == DBMode.CLOUD:
            exists, infos = AuthManager.check_teacher_exists(email)
            if not exists:
                self._show_error("Cet email ne correspond à aucun professeur actif.")
                return
        else:
            self._log("Tentative de connexion à l'Intranet…")
            if db.connect_intranet():
                exists, infos = AuthManager.check_teacher_exists(email)
                if not exists:
                    self._show_error("Cet email ne correspond à aucun professeur actif.")
                    return
            else:
                self._log("Intranet indisponible, tentative de connexion au Cloud…")
                if db.connect_cloud():
                    exists, infos = AuthManager.check_teacher_exists(email)
                    if not exists:
                        self._show_error("Cet email ne correspond à aucun professeur actif.")
                        return
                else:
                    self._show_error(
                        "Aucune connexion serveur disponible (Intranet ni Cloud). "
                        "La création d'instance est impossible."
                    )
                    return

        if db.server_mode == DBMode.INTRANET:
            from PySide6.QtWidgets import QInputDialog, QLineEdit

            pwd, ok = QInputDialog.getText(
                self,
                "Mot de passe",
                f"Veuillez saisir le mot de passe pour {email} :",
                QLineEdit.Password,
            )
            if not ok or not pwd:
                self._show_error("Mot de passe requis pour créer l'instance.")
                return

            auth_ok, _ignored, err = AuthManager.auth_intranet(email, pwd)
            if not auth_ok:
                self._show_error(f"Mot de passe incorrect : {err}")
                return

        elif db.server_mode == DBMode.CLOUD:
            self._log("Lancement de l'authentification OAuth2 Google…")
            auth_ok, res, err = OAuth2Manager.authenticate()
            if not auth_ok:
                self._show_error(f"Authentification Cloud échouée : {err}")
                return
            if res.email.lower() != email.lower():
                self._show_error("L'email du compte Google ne correspond pas à l'email saisi.")
                return
        else:
            self._show_error("Mode de connexion inconnu.")
            return

        slug = email.split("@")[0].replace(".", "_")
        dest = os.path.normpath(os.path.join(parent, f"eLarcProf_{slug}"))
        try:
            self._show_progress("Création du dossier de destination…")
            os.makedirs(dest, exist_ok=True)
            self._log(f"Dossier créé : {dest}")

            src = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
            self._show_progress("Copie des fichiers du projet…")
            for item in os.listdir(src):
                if item in ("__pycache__", ".git", ".venv"):
                    continue
                s = os.path.join(src, item)
                d = os.path.join(dest, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
            dest_cfg = os.path.join(dest, "config.ini")
            if not os.path.exists(dest_cfg):
                self._log(
                    "config.ini introuvable dans la source, création d'un fichier par défaut."
                )
                with open(dest_cfg, "w", encoding="utf-8") as f:
                    f.write("""[IntranetDatabase]
Host = 127.0.0.1
Port = 5432
DB = NewLarcDB
User = postgres
Pass = postgres

[SupabaseDatabase]
Host = db.xxxxxxxxxxxx.supabase.co
Port = 5432
DB = postgres
User = postgres
Pass = votre_mot_de_passe_supabase
""")
                self._log(f"config.ini par défaut créé : {dest_cfg}")
            src_db = os.path.normpath(os.path.join(src, "elarc.db"))
            if os.path.exists(src_db):
                shutil.copy2(src_db, os.path.join(dest, "elarc.db"))
                self._log("elarc.db copié.")
            else:
                self._log("elarc.db introuvable dans la source.")
            self._log("Copie terminée.")

            dest_db = os.path.join(dest, "elarc.db")
            if not sqlite_init.init(dest_db):
                self._show_error(
                    "Impossible d'initialiser la base locale dans le dossier de destination."
                )
                return

            ok, missing = sqlite_init.verify_tables()
            if not ok:
                self._log(f"ATTENTION : Tables manquantes dans la base locale : {missing}")

            sqlite_init.init_module_config(
                annee_scolaire=infos["annee_scolaire"],
                trimestre_courant=infos["trimestre_courant"],
                nom_professeur=f"{infos['first_name']} {infos['last_name']}",
                email_professeur=email,
            )

            from common.session import AuthResult, UserRole

            res = AuthResult(
                user_id=infos["user_id"],
                email=email,
                full_name=f"{infos['first_name']} {infos['last_name']}",
                role=UserRole.PROF,
                term_id=infos["trimestre_courant"],
                term_label=infos["trimestre_label"],
            )
            sqlite_init.save_session(res)

            self._show_progress("Écriture du fichier instance.ini…")
            cfg_dest = os.path.join(dest, "instance.ini")
            with open(cfg_dest, "w", encoding="utf-8") as f:
                f.write(f"[Instance]\nEmail={email}\nCreated=auto\n")
            self._log(f"instance.ini créé : {cfg_dest}")

            self._show_progress("Création du lanceur lancer.bat…")
            bat = os.path.join(dest, "lancer.bat")
            with open(bat, "w", encoding="utf-8") as f:
                f.write('@echo off\ncd /d "%~dp0"\npython main.py\npause\n')
            self._log(f"lancer.bat créé : {bat}")

            self._show_progress("Instance créée avec succès.")
            QMessageBox.information(
                self,
                "Instance créée",
                f"Instance créée dans :\n{dest}\n\nLancez lancer.bat pour démarrer.",
            )
            self._hide_error()
        except Exception as e:
            self._show_error(f"Erreur de création : {e}")

    # ------------------------------------------------------------------
    # Helpers (inchangés)
    # ------------------------------------------------------------------
    def _set_busy(self, busy: bool) -> None:
        for btn in (self._btn_intra, self._btn_google, self._btn_pin, self._btn_create):
            QMetaObject.invokeMethod(btn, "setEnabled", Qt.QueuedConnection, Q_ARG(bool, not busy))
        text = "Connexion en cours" if busy else "Détection du réseau"
        QMetaObject.invokeMethod(self._net_txt, "setText", Qt.QueuedConnection, Q_ARG(str, text))

    def _show_error(self, msg: str) -> None:
        p = theme_manager.theme.palette
        QMetaObject.invokeMethod(self._err_lbl, "setText", Qt.QueuedConnection, Q_ARG(str, msg))
        QMetaObject.invokeMethod(
            self._err_lbl,
            "setStyleSheet",
            Qt.QueuedConnection,
            Q_ARG(
                str,
                f"color: {p.error}; font-size: {theme_manager.font_size(11)}px; font-weight: bold;",
            ),
        )
        QMetaObject.invokeMethod(self._err_lbl, "show", Qt.QueuedConnection)

    def _log(self, msg: str) -> None:
        QMetaObject.invokeMethod(
            self._log_area, "appendPlainText", Qt.QueuedConnection, Q_ARG(str, msg)
        )
        QMetaObject.invokeMethod(self._log_area, "show", Qt.QueuedConnection)
        sb = self._log_area.verticalScrollBar()
        QMetaObject.invokeMethod(sb, "setValue", Qt.QueuedConnection, Q_ARG(int, sb.maximum()))

    def _show_progress(self, msg: str) -> None:
        p = theme_manager.theme.palette
        self._err_lbl.setText(msg)
        self._err_lbl.setStyleSheet(
            f"color: {p.text_strong}; font-size: {theme_manager.font_size(11)}px;"
        )
        self._err_lbl.show()
        self._log(msg)

    def _show_spinner(self, visible: bool) -> None:
        if not hasattr(self, "_spinner"):
            from PySide6.QtWidgets import QProgressBar

            self._spinner = QProgressBar()
            self._spinner.setRange(0, 0)
            self._spinner.setFixedHeight(21)
            p = theme_manager.theme.palette
            self._spinner.setStyleSheet(
                f"QProgressBar {{ border: 1px solid {p.border}; border-radius: 4px; "
                f"background: {p.surface}; text-align: center; }}"
                f"QProgressBar::chunk {{ background: {p.primary}; }}"
            )
            layout = self.centralWidget().layout()
            layout.insertWidget(layout.indexOf(self._bottom_indicator), self._spinner)
        self._spinner.setVisible(visible)

    def _hide_error(self) -> None:
        self._err_lbl.hide()

    def _get_module_config(self) -> Optional[dict]:
        try:
            conn = db.local_conn
            if conn is None:
                return None
            cur = conn.cursor()
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='module_config'"
            )
            if not cur.fetchone():
                return None
            cur.execute(
                "SELECT nom_professeur, annee_scolaire, trimestre_courant, email_professeur FROM module_config LIMIT 1"
            )
            row = cur.fetchone()
            if row and row[0]:
                return {
                    "nom_professeur": row[0],
                    "annee_scolaire": row[1],
                    "trimestre_courant": row[2],
                    "email_professeur": row[3] if len(row) > 3 else "",
                }
        except Exception as e:
            self._log(f"Erreur dans _get_module_config : {e}")
        return None

    def _get_module_config_dates(self) -> dict:
        try:
            conn = db.local_conn
            if conn is None:
                return {"date_creation_module": "", "derniere_synchronisation": ""}
            cur = conn.cursor()
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='module_config'"
            )
            if not cur.fetchone():
                return {"date_creation_module": "", "derniere_synchronisation": ""}
            cur.execute(
                "SELECT date_creation_module, derniere_synchronisation FROM module_config LIMIT 1"
            )
            row = cur.fetchone()
            if row:
                return {
                    "date_creation_module": row[0] or "",
                    "derniere_synchronisation": row[1] or "",
                }
        except Exception as e:
            self._log(f"Erreur dans _get_module_config_dates : {e}")
        return {"date_creation_module": "", "derniere_synchronisation": ""}

    def _update_status_bar_from_module_config(self) -> None:
        try:
            if db.local_conn is None:
                self._bottom_indicator.setText("Module LarcProf non instanciée")
                return
            config = self._get_module_config()
            if config:
                prof_name = config["nom_professeur"]
                from common.session import session

                mode = session.conn_mode if session.is_authenticated else ConnMode.OFFLINE
                self._update_status_bar(
                    AuthResult(
                        user_id=0,
                        email="",
                        full_name=prof_name,
                        role=UserRole.PROF,
                        term_id=config["trimestre_courant"],
                        term_label="",
                    ),
                    mode,
                )
            else:
                self._bottom_indicator.setText("Module LarcProf non instanciée")
        except Exception as e:
            self._log(f"Erreur dans _update_status_bar_from_module_config : {e}")
            self._bottom_indicator.setText("Module LarcProf non instanciée")

    def _update_status_bar(self, res: AuthResult, mode: ConnMode) -> None:
        sp = self._sp
        p = theme_manager.theme.palette
        prof_name = res.full_name or (self._get_module_config() or {}).get("nom_professeur", "")

        if mode == ConnMode.INTRANET:
            title = f"Module de {prof_name} : Connecté à l'Intranet"
            color = "#27ae60"
        elif mode == ConnMode.CLOUD:
            title = f"Module de {prof_name} : Connecté au Cloud"
            color = "#27ae60"
        elif prof_name:
            title = f"Module de {prof_name} : Non connecté"
            color = p.text_strong
        else:
            title = "Module LarcProf non instanciée"
            color = p.text_strong

        self._bottom_indicator.setText(title)
        self._bottom_indicator.setStyleSheet(
            f"color: {color}; font-size: {theme_manager.font_size(13)}px; font-weight: bold;"
            f"padding: {sp(SpacingToken.SM)}px {sp(SpacingToken.MD)}px;"
        )

    def _open_main_window(self, res: AuthResult) -> None:
        from views.home_window import HomeWindow

        self._main_window = HomeWindow(parent=self)
        self._main_window.show()
        self.hide()
