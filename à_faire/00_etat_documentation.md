# État de la documentation, du contexte et de l'historique

_Audit réalisé le 31 mai 2026 — comparaison code réel ↔ docs/ ↔ CONTEXT.md ↔ historique_construction.md_

## Verdict global

La documentation est **globalement à jour sur l'intention** (architecture, philosophie gabarit,
algorithme de sync, panneaux F/S) mais comporte **plusieurs désynchronisations factuelles** avec
le code réel et, surtout, un **écart majeur entre le DDL documenté et le schéma réel de `elarc.db`**.

Légende : ✅ à jour · ⚠️ partiellement faux/obsolète · ❌ faux / manquant

---

## 1. Écarts CRITIQUES (à corriger en priorité)

### ❌ 1.1 Le `_DDL` de `sqlite_init.py` ne correspond pas au schéma réel
- **Doc concernée :** `docs/06`(implicite), `historique_construction.md` Itération 6 (l.266-282),
  `CONTEXT.md` §"Base de données unique elarc.db".
- **Réalité :** `elarc.db` contient ~50 tables issues de l'export complet PostgreSQL
  (`export_to_sqlite.py`), toutes en `colonne TEXT`. La vraie table `larcauth_evaluation`
  a les colonnes `id, label, nature, baremeNoteDP, type_evaluation, index_eval, crit_a..crit_f,
  aspect_a1..f7, created, updated, fk_classroom_termsubject_id, baremeNoteCritere, sync_version, ...`.
- **Le `_DDL`** crée au contraire un `larcauth_evaluation(evaluation_type, score, comment, fk_student_id, ...)`
  — colonnes **inexistantes/inutilisées** par l'IHM.
- **Conséquence :** le `_DDL` est trompeur. Le code IHM (`evaluation_panel.py`, `eval_manager.py`)
  lit/écrit `label, nature, source, crit_a..d, index_eval, type_evaluation` — qui ne sont PAS dans
  le `_DDL`. Ça ne fonctionne que parce que `elarc.db` est en réalité l'export complet.
  ⚠️ **`source` n'existe pas non plus dans le schéma réel** (à vérifier/ajouter).
- **À faire :** réaligner le `_DDL` (ou le supprimer au profit du seed par export) ET la doc.

### ❌ 1.2 `larcauth_criteria_of_levelsubject` interrogée mais absente du `_DDL`
- Utilisée par `evaluation_panel.py` et `eval_manager.py` (légende + labels critères).
- Présente dans `elarc.db` réel, mais **absente du `_DDL`** de `sqlite_init.py` et de `verify_tables()`.
- **À faire :** documenter et inclure dans le DDL/seed.

### ❌ 1.3 Colonne `source` de `larcauth_evaluation`
- Lue/écrite partout dans l'IHM (`source`), documentée dans `19_evaluation_panel.md`,
  mais **absente du schéma réel exporté** (la table a `label, nature, ...` mais pas `source`).
- **À vérifier :** soit la colonne existe côté serveur et n'a pas été listée, soit l'IHM écrit
  dans une colonne inexistante (UPDATE silencieusement sans effet).

---

## 2. Écarts dans `docs/` (fichiers individuels)

### ⚠️ 2.1 `docs/README.md` — index incomplet
- Ne liste **pas** `18_tableau_de_bord_prof.md` ni `20_eval_manager.md` (qui existent).
- Mentionne l'ordre numérique mais saute `18`.
- **À faire :** ajouter les entrées 18 et 20.

### ⚠️ 2.2 `docs/16_main_window.md` — partiellement obsolète
- Décrit le dialogue détail avec **Label = `QLineEdit` (modifiable)** et **Source = `QPlainTextEdit`**.
- Réalité (`evaluation_panel.py`) : **Label = `QLabel` lecture seule**, **Source = `QTextEdit` Markdown**.
- Ne mentionne pas le bouton "Gérer" ni `EvalManagerWindow`.

### ⚠️ 2.3 `docs/19_evaluation_panel.md` — partiellement obsolète
- `get_form_data()` documenté renvoie encore `label` et `toPlainText()` ; le code renvoie
  `toMarkdown()` et **pas** `label`.
- Le tableau des champs indique `Source = QPlainTextEdit` (réalité : `QTextEdit` + Markdown).
- Décrit `EvaluationDetailDialog` avec aspects affichés ; les aspects ne sont pas rendus en v1.
- La grille critères documentée est "verticale" alors que le code utilise une grille 4×2.

### ⚠️ 2.4 `docs/18_tableau_de_bord_prof.md` — décrit une cible non implémentée
- Décrit `pei_workspace.py` / `dp_workspace.py` + `QStackedWidget` + grille élèves×notes.
- Réalité : `main_window.py` n'a **pas** de QStackedWidget, **pas** de workspaces PEI/DP séparés,
  la grille élèves est un **placeholder**. C'est un document de **conception**, pas de l'existant.
- **À faire :** marquer clairement comme "cible / non implémenté".

### ⚠️ 2.5 `docs/17_pei_dp_separation.md`
- Statut "À FAIRE" correct, mais le reste de la doc (16/18) présente parfois cette séparation
  comme actée dans l'implémentation. Incohérence interne.

### ⚠️ 2.6 `docs/11_export_sqlite.md`
- Décrit `export_to_sqlite.py` correctement mais ne dit pas que **c'est ce script qui produit
  réellement `elarc.db`** (et non le `_DDL`). Lien manquant avec 1.1.

---

## 3. Écarts dans `CONTEXT.md`

### ⚠️ 3.1 Architecture fichiers incomplète
- Le bloc "Architecture fichiers" ne mentionne **pas** `common/sync.py` (qui existe, squelette).
- Ne mentionne pas `views/eval_manager.py` dans l'arbre principal (cité plus bas seulement).
- Fichiers utilitaires non documentés : `check_db.py`, `check_criteria2.py`, `check_labels.py`,
  `reset_pwd.py`, `DbInit/`.

### ⚠️ 3.2 Tables sync device
- CONTEXT mentionne `sync_state` ✅ (présente). Mais `sync_cursor` (présente dans le DDL et la base)
  n'est pas décrite dans la section sync ; rôle ambigu vs `sync_state`.

### ✅ 3.3 Philosophie gabarit / matrice de sync / déclencheurs
- Cohérents avec `common/sync.py` (squelette) et `docs/18` §6. À jour.

---

## 4. Écarts dans `historique_construction.md`

### ⚠️ 4.1 Numérotation des itérations en doublon
- Il y a **deux "Itération 12"** (l.539 "Synchronisation" ET l.636 "Panneaux F/S")
  et **deux "Itération 14"** (l.607 "venv" ET l.752 "EvalManagerWindow").
- Numérotation à reprendre proprement.

### ⚠️ 4.2 Annexe B (organisation fichiers)
- Ne mentionne pas `common/sync.py`. `eval_manager.py` listé ✅.

### ⚠️ 4.3 Itération 6 (DDL)
- Reflète le `_DDL` théorique, pas le schéma réel exporté (cf. 1.1).

---

## 5. Incohérences code ↔ historique (auth)

### ⚠️ 5.1 `larcib_term` vs `larcauth_term`
- `auth.py::_load_active_term` interroge `larcib_term` (avec `is_active`).
- La base réelle a `larcauth_term`. `check_teacher_exists` utilise `larcauth_academicyear` +
  `larcauth_term`. Le `larcib_term` semble obsolète/mort. À clarifier.

### ⚠️ 5.2 Colonne `enabled` dans `larcauth_teachadm`
- L'historique (Itération 3) dit explicitement "Pas de colonne `enabled`".
- Mais `OAuth2Manager.authenticate` (auth.py l.362) fait
  `WHERE aecuser_ptr_id = %s AND enabled = TRUE` → contradiction, risque d'erreur SQL en mode Cloud.

---

## 6. Documentation manquante (aucun fichier)

- ❌ Pas de doc dédiée à `common/sync.py` (le module existe en squelette). Référencé "étape 7"
  mais sans fichier `docs/21_sync_manager.md`.
- ❌ Pas de doc sur les scripts utilitaires racine (`check_*.py`, `reset_pwd.py`, `DbInit/`).
- ❌ Pas de doc sur `requirements.txt` exact ni la procédure d'install/venv (hors historique it.14).
