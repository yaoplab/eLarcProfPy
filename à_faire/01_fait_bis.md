# Déjà fait — eLarcProfPy (bis)

_Inventaire de l'existant fonctionnel au 31 mai 2026 (vérifié dans le code et `elarc.db`)._
_Dernière mise à jour : 31 mai 2026 (Tables termothersubject ajoutées)._
_Fichier compagnon : `02_reste_a_faire_bis.md`._

Légende : ✅ Terminé et vérifié · 🟡 Fait mais fragile · ❌ Documenté mais non implémenté

---

## Phase 1 — Connexion & Infrastructure (TERMINÉE)

### Point d'entrée & CLI (`main.py`)
- ✅ Lancement normal, `--mode4`, `--test-create-db`

### Détection réseau (`common/network.py`)
- ✅ `detect_network()`, timer 30s, pas de connexion auto

### Connexions DB (`common/database.py`)
- ✅ Singleton `db`, INTRANET/CLOUD/SQLITE, `before_update()`, `config.ini`

### Authentification (`common/auth.py`)
- ✅ Intranet (SHA-256), PIN (hash), OAuth2 PKCE Google
- ✅ `check_teacher_exists()`
- ✅ **Bug 5.1 corrigé :** `larcib_term` → `larcauth_term`
- ✅ **Bug 5.2 corrigé :** `enabled = TRUE` supprimé

### Fenêtre de connexion (`views/login.py`)
- ✅ 4 onglets, workers, indicateurs, boutons password/PIN
- ✅ Vérification email module, flux post-auth complet, spinner

### Changement credentials (`views/password.py`)
- ✅ `ChangePasswordDialog`, `ChangePinDialog`

### Session (`common/session.py`)
- ✅ `UserRole`, `ConnMode`, `AuthResult`, `Session` + singleton

### Logger (`common/logger.py`)
- ✅ `log()` vers `elarc.log`

### Initialisation SQLite (`common/sqlite_init.py`)
- ✅ `init()`, `save_session()`, `init_module_config()`, `take_teacher_data()`
- ✅ `read_cursor()/update_cursor()`, `verify_tables()`, `BUSINESS_TABLES`
- ✅ **Bug 1.1 corrigé :** `_DDL` réécrit
- ✅ **Bug 1.2 corrigé :** `source TEXT` ajouté
- ✅ **Bug 1.3 corrigé :** `larcauth_criteria_of_levelsubject` ajoutée
- ✅ **Bug 1.4 corrigé :** Duplications DDL nettoyées
- ✅ **Nouvelles tables :** `larcauth_classroom_termothersubject` + `_ref`
- ✅ **Nouvelles tables :** `larcauth_learner_has_termothersubject` + `_ref`
- ✅ **Seed étendu :** `fk_supervisor_id` pour les termothersubjects

### Export PostgreSQL → SQLite (`export_to_sqlite.py`)
- ✅ Export complet via SQLAlchemy + pandas

### Création d'instance (`views/login.py::_on_create`)
- ✅ Vérification, auth, copie, `config.ini`, `elarc.db`, `instance.ini`, `lancer.bat`

---

## Phase 2 — Espace de travail (EN COURS)

### Fenêtre principale (`views/main_window.py`)
- ✅ Header, sélecteur Matière-Classe, `_determine_cycle()`
- ✅ Panneaux F/S + `EvalManagerWindow`
- ✅ **Synchroniser** → `sync.pull_push()` avec feedback
- ✅ **Enregistrer et quitter** → synchro + fermeture
- ❌ Grille élèves×notes : **Placeholder**
- ❌ Panneau Filtres : **Placeholder**

### Panneaux d'évaluation (`views/evaluation_panel.py`)
- ✅ `EvaluationPanel`, `_SlotButton`, indicateurs, légende
- ✅ `EvaluationDetailWidget` : Label (QLabel), Nature, Source (QTextEdit Markdown)
- ✅ Barre d'outils B/I/H/•/🔗, grille 4×2, `_SpellHighlighter`
- ✅ **Bug 4.2 corrigé :** `_save_criteria()` et `load_evaluations()` — `source` retiré des requêtes

### Fenêtre de gestion (`views/eval_manager.py`)
- ✅ `EvalManagerWindow`, `_SlotBar`, tabs, affichage progressif
- ✅ **Bug 4.1 corrigé :** `_on_save_slot()` — `source` retiré, statusBar ajoutée
- ✅ **Renommé :** "Enregistrer cette évaluation", titre "Gestion des Évaluations"

---

## SyncManager (`common/sync.py`) — IMPLÉMENTÉ

- ✅ Toutes les méthodes implémentées
- ✅ Boutons **Synchroniser** et **Enregistrer et quitter** branchés

---

## Architecture & Décisions
- ✅ Gabarit pré-alloué, shadow-table `_ref`, `sync_state`
- ✅ Matrice de décision, scope trimestre courant, notation PEI/DP

## Documentation existante
- ✅ 21 fichiers dans `docs/`, `CONTEXT.md`, `historique_construction.md`
- ⚠️ README, 16, 19, 18 à corriger
