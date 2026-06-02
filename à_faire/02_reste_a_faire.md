# Reste à faire — eLarcProfPy

_Checklist détaillée établie le 31 mai 2026 d'après l'audit complet du code, des docs, du contexte et de l'historique._
_Fichier compagnon : `01_fait.md` (ce qui est déjà terminé)._

Légende priorité : 🔴 critique · 🟠 important · 🟢 confort/finition

---

## A. Corrections de cohérence schéma / DDL (🔴 bloquant pour la suite)

- [ ] 🔴 **Réaligner le `_DDL` de `common/sqlite_init.py` sur le schéma réel de `elarc.db`**
      (table `larcauth_evaluation` réelle = `label, nature, type_evaluation, index_eval, crit_a..crit_f, aspect_*, fk_classroom_termsubject_id, ...`, pas `evaluation_type/score/comment`).
- [ ] 🔴 **Décider de la source de vérité du schéma device** : soit `_DDL` complet et exact, soit seed
      par export (`export_to_sqlite.py`) — documenter le choix et supprimer la redondance trompeuse.
- [ ] 🔴 **Vérifier l'existence de la colonne `source`** dans `larcauth_evaluation` (serveur + device).
      Si absente, l'`UPDATE ... SET source=?` de l'IHM est silencieusement sans effet → ajouter la colonne ou retirer le champ.
- [ ] 🔴 **Ajouter `larcauth_criteria_of_levelsubject`** au `_DDL` et à `verify_tables()` (utilisée par l'IHM).
- [ ] 🟠 Compléter `verify_tables()` avec les tables réellement requises par l'IHM
      (`larcauth_criteria_of_levelsubject`, etc.).
- [ ] 🟠 Clarifier le rôle de `sync_cursor` vs `sync_state` (doublon apparent) et n'en garder qu'un.

## B. Corrections d'authentification (🟠)

- [ ] 🟠 **Trancher `larcib_term` vs `larcauth_term`** dans `auth.py::_load_active_term`
      (la base réelle a `larcauth_term`). Remplacer ou supprimer le code mort.
- [ ] 🟠 **Retirer `AND enabled = TRUE`** sur `larcauth_teachadm` dans `OAuth2Manager.authenticate`
      (auth.py l.362) — colonne inexistante d'après l'historique, risque d'erreur SQL côté Cloud.
- [ ] 🟢 Factoriser la logique commune `auth_intranet` / `OAuth2` (lookup user + teachadm + term).

## C. Module de synchronisation `common/sync.py` (🔴 — cœur Phase 2)

État : **squelette uniquement** (toutes les méthodes lèvent `NotImplementedError`).

- [ ] 🔴 Implémenter `_ensure_current_term()` (lecture `module_config.trimestre_courant`).
- [ ] 🔴 Implémenter `_ensure_server_connected()` (intranet ou cloud).
- [ ] 🔴 Implémenter `compute_cell_diff(table)` : jointure local + `_ref` + serveur sur `id`,
      filtre `term_id = trimestre_courant`, application de la matrice de décision cellule par cellule.
- [ ] 🔴 Implémenter `apply_pull(diff)` (local = serveur, ref = serveur).
- [ ] 🔴 Implémenter `apply_push(diff)` (serveur = local, ref = local) avec
      `SET LOCAL app.sync_source` + `SET LOCAL app.modified_by` avant chaque UPDATE serveur.
- [ ] 🔴 Implémenter `apply_resolution(diff, keep)` (conflit tranché par le prof).
- [ ] 🔴 Implémenter `touch_sync_state(table)` (mise à jour `sync_state.last_sync`/`last_source`).
- [ ] 🔴 Implémenter `pull_push()` (orchestration des 3 tables métiers, scope trimestre courant).
- [ ] 🟠 Garde-fou : **ne jamais INSERT/DELETE**, uniquement UPDATE (gabarit pré-alloué).
- [ ] 🟠 Garde-fou : **ignorer les trimestres passés** (read-only).
- [ ] 🟢 Tests unitaires de la matrice de décision (4 cas) sur une base SQLite jouet.

## D. IHM de résolution de conflits (🟠 — dépend de C)

- [ ] 🟠 Créer `views/conflict_dialog.py` (`ConflictResolutionDialog`) listant les cellules en conflit.
- [ ] 🟠 Choix par cellule : "Garder ma version" (push) / "Prendre le serveur" (pull).
- [ ] 🟠 Brancher sur `SyncReport.conflicts` retourné par `pull_push()`.

## E. Branchement des déclencheurs de synchro (🟠 — dépend de C)

- [ ] 🟠 Activer et brancher le bouton **Synchroniser** de `main_window.py` sur `sync.pull_push()`
      (actuellement `setEnabled(False)`).
- [ ] 🟠 Activer et brancher **Enregistrer et quitter** (synchro + fermeture) dans `main_window.py`.
- [ ] 🟠 Synchro sur **clic "Connecter"** (onglet Intranet / Cloud) si `local ≠ ref`.
- [ ] 🟢 Afficher la progression (spinner/barre) et le résultat (pull/push/conflits) dans la status bar.

## F. Grille élèves × notes — MainWindow (🔴 — fonctionnalité métier centrale manquante)

État : `_build_students_grid()` renvoie un **placeholder** "(à venir)".

- [ ] 🔴 Construire la grille (`QTableWidget` / `QTableView` + modèle) — colonne fixe "Élève".
- [ ] 🔴 Colonnes dynamiques selon critères actifs des F01..F12 / S01..S12 (`F{n}_note_{a..d}`, `S{n}_note_{a..d}`).
- [ ] 🔴 Lecture des notes depuis `larcauth_learnerpei_has_termsubjectpei` (PEI) / `..dp..` (DP).
- [ ] 🔴 Remplissage ligne par ligne pour `self._eleves_par_classe[class_id]`.
- [ ] 🔴 Colonne de synthèse (`note_on_7` PEI / `moy_on_20` DP).
- [ ] 🟠 Validateurs : PEI `QSpinBox` 0–8 (synthèse 0–7), DP `QDoubleSpinBox` 0–20 step 0.5.
- [ ] 🟠 Édition + écriture immédiate locale (UPDATE table de travail, jamais `_ref`),
      regroupement en transaction via `QTimer` (~2 s).
- [ ] 🟠 Trimestres passés en **lecture seule** (`NoEditTriggers`).
- [ ] 🟢 Masquage des colonnes dont le critère n'est coché pour aucun élève.

## G. Séparation PEI / DP (🟠 — décision actée non implémentée, cf. docs/17)

- [ ] 🟠 Décider : 2 fichiers (`pei_workspace.py` / `dp_workspace.py` + `QStackedWidget`) **ou**
      un widget unique paramétré. (La doc 17/18 prévoit 2 fichiers ; le code actuel n'en a aucun.)
- [ ] 🟠 Implémenter le basculement de cycle (`_determine_cycle` existe déjà et renvoie PEI/DP).
- [ ] 🟢 Spécificités DP : `cc_on_20`, `bacblanc`, `bacblanc2`, `ei_note`, `cpei`, etc.

## H. Panneau Filtres (🟢)

- [ ] 🟢 Remplacer le placeholder "Filtres" de `main_window.py` par un vrai panneau
      (tri, masquage colonnes, affichage par critère).

## I. Tableau de bord par rôle (🟢 — Phase post-2)

- [ ] 🟢 PROF : ses classes → saisie (en cours via MainWindow).
- [ ] 🟢 COORD : vue globale + validation.
- [ ] 🟢 SECR : gestion administrative.
- [ ] 🟢 ADMIN : configuration système.
- [ ] 🟢 Aiguillage selon `session.role` à l'ouverture de la fenêtre principale.

## J. Mise à jour documentaire (🟠 — voir 00_etat_documentation.md pour le détail)

- [ ] 🟠 `docs/README.md` : ajouter les entrées `18` et `20` (manquantes).
- [ ] 🟠 `docs/16_main_window.md` : Label en lecture seule, Source Markdown, bouton Gérer + EvalManager.
- [ ] 🟠 `docs/19_evaluation_panel.md` : `get_form_data()` (Markdown, sans `label`), grille critères 4×2.
- [ ] 🟠 `docs/18_tableau_de_bord_prof.md` : marquer explicitement "cible / non implémenté".
- [ ] 🟠 `historique_construction.md` : corriger les doublons d'itérations (deux 12, deux 14).
- [ ] 🟠 `CONTEXT.md` : ajouter `common/sync.py` et `views/eval_manager.py` à l'arbre fichiers.
- [ ] 🟢 Créer `docs/21_sync_manager.md` (documentation de `common/sync.py`).
- [ ] 🟢 Documenter les scripts utilitaires racine (`check_db.py`, `check_criteria2.py`,
      `check_labels.py`, `reset_pwd.py`, `DbInit/`) ou les ranger dans un dossier `tools/`.
- [ ] 🟢 Documenter le lien `export_to_sqlite.py` → `elarc.db` (source réelle du schéma).

## K. Qualité / nettoyage (🟢)

- [ ] 🟢 Remplacer les nombreux `print(...)` de debug par le `logger` (`common/logger.py`).
- [ ] 🟢 Nettoyer les fichiers de réflexion à la racine (`Reflexion_1.txt`,
      `Reflexion sur la suite du pgm1.html`, `historique_demandes.txt`, `tableConvert.md`).
- [ ] 🟢 Vérifier que `elarc.db` / `elarc.anonyme.db` sont bien dans `.gitignore` (données).
- [ ] 🟢 Ajouter des tests d'intégration (`--test-create-db` existe ; étendre au seed + sync).
- [ ] 🟢 Gérer proprement le cas `larcauth_evaluation` avec `id TEXT` (CAST systématiques actuels).

---

## Ordre de réalisation conseillé

1. **A** (schéma/DDL) — débloque tout le reste, évite des bugs silencieux.
2. **F** (grille élèves×notes) — la fonctionnalité métier centrale manquante.
3. **C** (SyncManager) puis **E** (déclencheurs) puis **D** (conflits).
4. **G** (PEI/DP) en parallèle de F.
5. **B**, **H**, **J**, **K** (finitions et doc) au fil de l'eau.
6. **I** (tableau de bord par rôle) en Phase 3.
