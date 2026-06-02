# Déjà fait — eLarcProfPy

_Inventaire de l'existant fonctionnel au 31 mai 2026 (vérifié dans le code, pas seulement dans la doc)._
_Fichier compagnon : `02_reste_a_faire.md`._

Légende : ✅ terminé et vérifié dans le code · 🟡 fait mais fragile/à consolider

---

## Phase 1 — Connexion & infrastructure (TERMINÉE)

### Point d'entrée & CLI (`main.py`)
- ✅ Lancement normal `python main.py` (QApplication Fusion + LoginWindow).
- ✅ Mode `--mode4 [email]` : connexion intranet, `check_teacher_exists`, init SQLite,
  `init_module_config`, `take_teacher_data`, vérif comptes, `save_session`.
- ✅ Mode `--test-create-db` : base temporaire + `verify_tables()`.

### Détection réseau (`common/network.py`)
- ✅ `detect_network()` (test TCP intranet + HTTP internet), couleurs d'état.
- ✅ Pas de connexion automatique au démarrage (test de présence seulement).
- ✅ Timer de re-vérification réseau toutes les 30 s (`login.py`).

### Connexions DB (`common/database.py`)
- ✅ Singleton `db` ; modes INTRANET / CLOUD / SQLITE / NONE.
- ✅ `connect_intranet`, `connect_cloud` (psycopg2), `connect_sqlite` (WAL, `check_same_thread=False`).
- ✅ `before_update()` pose `SET LOCAL app.sync_source` + `app.modified_by`.
- ✅ `get_sqlalchemy_url()`, `server_conn`, `local_conn`, `server_mode`.
- ✅ Lecture `config.ini` avec fallback vers `..\eLarcProf\config.ini`.

### Authentification (`common/auth.py`)
- ✅ Intranet : email + SHA-256 vs `larcauth_aecuser.password`, rôle via `larcauth_teachadm`
  (`is_adm`/`is_coordonator`/`is_secretary`), déduction `UserRole`.
- ✅ PIN hors ligne : `session_cache` (hash SHA-256).
- ✅ OAuth2 PKCE Google `@arc-en-ciel.org` (serveur loopback :8765, échange token, décode JWT, `hd`).
- ✅ `check_teacher_exists()` : identité + teachadm + année/trimestre courant
  (`larcauth_academicyear` + `larcauth_term`).
- 🟡 Deux points à corriger (voir `02_reste_a_faire.md` §B : `larcib_term`, `enabled`).

### Fenêtre de connexion (`views/login.py`)
- ✅ 4 onglets : Intranet, Cloud, Hors connexion (PIN), Nouvelle instance.
- ✅ Workers `QThread` non bloquants, logs thread-safe via `QMetaObject.invokeMethod`.
- ✅ Indicateurs présence Intranet/Cloud (haut) + indicateur d'état large (bas, 4 états).
- ✅ Boutons "Changer le mot de passe" (Intranet) et "Changer le code PIN" (Hors connexion).
- ✅ Vérification que l'email correspond au professeur du module (`_check_email_module`).
- ✅ Flux complet post-auth : init SQLite → `init_module_config` → `take_teacher_data` → session → MainWindow.
- ✅ Proposition de définir un PIN après une auth en ligne.
- ✅ Spinner pendant le téléchargement des données.

### Changement credentials (`views/password.py`)
- ✅ `ChangePasswordDialog` (Intranet, SHA-256, validations).
- ✅ `ChangePinDialog` (PIN 4–8 chiffres, hash, `save_session`).

### Session (`common/session.py`)
- ✅ `UserRole`, `ConnMode`, `AuthResult`, `Session` (dataclasses) + singleton `session`.

### Logger (`common/logger.py`)
- ✅ `log()` vers `elarc.log`, bascule `LOG_TO_FILE`.

### Initialisation SQLite (`common/sqlite_init.py`)
- ✅ `init()/init_intranet()/init_cloud()`, exécution du `_DDL`.
- ✅ `save_session()` (UPSERT `session_cache`), `init_module_config()` (UPSERT `module_config`).
- ✅ `take_teacher_data()` : SELECT serveur (3 tables métier) → DROP/CREATE/INSERT local + `_ref`
  + `_touch_sync_state()`, transaction + rollback, comptes de contrôle.
- ✅ `read_cursor()/update_cursor()`, `verify_tables()`.
- ✅ Constante `BUSINESS_TABLES` (3 tables) partagée avec `sync.py`.
- 🟡 Le `_DDL` est désynchronisé du schéma réel (voir `00_etat_documentation.md` §1 et `02_reste_a_faire.md` §A).

### Export PostgreSQL → SQLite (`export_to_sqlite.py`)
- ✅ Export complet de toutes les tables publiques via SQLAlchemy + pandas (produit le vrai `elarc.db`).
- ✅ Conversions datetime/json, `if_exists='replace'`.

### Création d'instance (`views/login.py::_on_create`)
- ✅ Vérification prof actif (Intranet/Cloud), auth (mot de passe ou OAuth2).
- ✅ Copie du projet vers `eLarcProf_<slug>`, `config.ini` par défaut si absent, copie `elarc.db`.
- ✅ `init` + `verify_tables` + `init_module_config` + `save_session` dans la destination.
- ✅ Génération `instance.ini` et `lancer.bat`.

---

## Phase 2 — Espace de travail (EN COURS)

### Fenêtre principale (`views/main_window.py`)
- ✅ Squelette navigable : header (nom prof / année / trimestre depuis `module_config` + `session`).
- ✅ Sélecteur unique **Matière - Classe** (combo) + chargement combiné des items et élèves (SQLite).
- ✅ `_determine_cycle()` (PEI/DP via `larcauth_program.sigle`).
- ✅ Auto-sélection si un seul item ; statut dans la status bar.
- ✅ Intégration des panneaux F/S + ouverture de `EvalManagerWindow` (boutons "Gérer").
- ✅ Rechargement des panneaux à la fermeture du manager.
- 🟡 Grille élèves×notes, panneau Filtres, boutons Synchroniser/Enregistrer : **placeholders / désactivés**.

### Panneaux d'évaluation (`views/evaluation_panel.py`)
- ✅ `EvaluationPanel` (modes compact / non-compact), grille de slots responsive.
- ✅ `_SlotButton` : titre, label, critères compacts (☑/☐ A/B/C/D), états actif/inactif.
- ✅ Barre d'indicateurs F01..F12 / S01..S12 (vert/gris).
- ✅ Légende des critères (`larcauth_criteria_of_levelsubject`).
- ✅ `load_evaluations()` (lecture par `index_eval`/`type_evaluation`), `clear_panel()`.
- ✅ `EvaluationDetailWidget` : Label (lecture seule), Nature, Source **Markdown** (`QTextEdit`),
  barre d'outils B/I/H/•/🔗, grille critères 4×2.
- ✅ `_SpellHighlighter` (pyenchant fr_FR si installé, sinon inactif sans erreur).
- ✅ `EvaluationDetailDialog` (édition rapide modale) + `_save_criteria()` (UPDATE immédiat).

### Fenêtre de gestion (`views/eval_manager.py`)
- ✅ `EvalManagerWindow` non-modale, `QSplitter` horizontal (tabs+barres / détail).
- ✅ `_SlotBar` horizontale (`[F01] | nature 72c | ☐A☐B☐C☐D`).
- ✅ Tabs F01-F12 (vert si actif), légende critères.
- ✅ Affichage progressif (slots actifs + 1 "suivant" grisé, reste masqué).
- ✅ Réutilisation de `EvaluationDetailWidget` à droite + bouton "Enregistrer ce slot" (UPDATE + refresh).

---

## Architecture & décisions actées (documentées)
- ✅ Philosophie "gabarit" pré-alloué (UPDATE only, jamais INSERT/DELETE).
- ✅ Pattern shadow-table `_ref` (tables créées et seedées au `take_teacher_data`).
- ✅ Table `sync_state` (timestamp + source par table) alimentée au seed.
- ✅ Matrice de décision de synchro **spécifiée** (docs/18 §6, CONTEXT.md, sync.py docstrings).
- ✅ Scope synchro = trimestre courant ; trimestres passés figés (règle documentée).
- ✅ Système de notation PEI (0–8/critère, 0–7 synthèse) / DP (0–20) **documenté**.

## Documentation existante
- ✅ 21 fichiers dans `docs/` (01→20 + historique + README).
- ✅ `CONTEXT.md` riche (architecture, BDD, rôles, sync, règles métier).
- ✅ `historique_construction.md` (itérations 0→16, orienté portage Delphi).
- 🟡 Plusieurs fichiers partiellement obsolètes (voir `00_etat_documentation.md`).
