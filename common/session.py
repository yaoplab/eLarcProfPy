from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class UserRole(Enum):
    PROF = "PROF"
    COORD = "COORD"
    SECR = "SECR"
    ADMIN = "ADMIN"
    SUPERVISEUR = "SUPERVISEUR"  # alias LarcCommon


class ConnMode(Enum):
    INTRANET = "Intranet"
    CLOUD = "Cloud"
    OFFLINE = "Hors connexion"
    NEW_INSTANCE = "Nouvelle instance"


@dataclass
class AuthResult:
    user_id: int = 0
    email: str = ""
    full_name: str = ""
    role: UserRole = field(default_factory=lambda: UserRole.ADMIN)
    term_id: int = 0
    term_label: str = ""


class Session:
    def __init__(self):
        self.user_id = 0
        self.email = ""
        self.full_name = ""
        self.role = UserRole.ADMIN
        self.conn_mode: Optional[ConnMode] = None
        self.is_authenticated = False
        self.theme_pref: str = "material_light"
        self.card_theme: str = "medium"
        self.instance_dir = os.path.normpath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
        )
        # Champs synchronisés
        self._term_id = 0
        self._term_label = ""
        self._active_term_id = 0
        self._active_term_label = ""

    @property
    def term_id(self) -> int:
        return self._term_id

    @term_id.setter
    def term_id(self, v: int):
        self._term_id = v
        self._active_term_id = v

    @property
    def term_label(self) -> str:
        return self._term_label

    @term_label.setter
    def term_label(self, v: str):
        self._term_label = v
        self._active_term_label = v

    @property
    def active_term_id(self) -> int:
        return self._active_term_id or self._term_id

    @active_term_id.setter
    def active_term_id(self, v: int):
        self._active_term_id = v
        self._term_id = v

    @property
    def active_term_label(self) -> str:
        return self._active_term_label or self._term_label

    @active_term_label.setter
    def active_term_label(self, v: str):
        self._active_term_label = v
        self._term_label = v


session = Session()
