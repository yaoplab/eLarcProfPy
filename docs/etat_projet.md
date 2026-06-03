# État du Projet — eLarcProfPy

_Audit du 3 juin 2026 — Dernière mise à jour : 3 juin 2026_

## 1. Verdict Global

Phase 2 opérationnelle : top bar refactorée avec slots actifs uniquement, grille élèves × notes avec données réelles, édition par double-clic et sauvegarde en SQLite. SyncManager implémenté et branché. Daemon LarcCloudSync créé (Intranet ↔ Cloud).

## 2. Phase 1 — Connexion (✅ TERMINÉE)

- ✅ 4 onglets : Intranet (SHA-256), Cloud (OAuth2 PKCE), PIN (hors ligne), Nouvelle instance
- ✅ Changement mot de passe / PIN via `views/password.py`
- ✅ Indicateur d'état réseau unique en bas (4 états)
- ✅ Base unique `elarc.db` avec DDL complet + migration automatique

## 3. Phase 2 — Workspace (✅ FONCTIONNEL)

### Top bar (nouveau 2 juin)
- ✅ 4 sections fixes : Matière-Classe (210px), Formatives (stretch), Sommatives (stretch), Jugements (170px)
- ✅ Chaque section F/S : `QScrollArea` listant **uniquement les slots actifs**
- ✅ Slots inactifs invisibles (≠ grisés)
- ✅ Clic slot → bascule colonne dans la grille (bordure orange `#ff6b00`)
- ✅ Boutons **Toute** / **Aucune** / **Commentaire** par section
- ✅ Section Jugements : 3 toggles (Jgt/Note/Commentaire) + 4 critère A/B/C/D

### Grille élèves × notes
- ✅ Colonnes dynamiques : slots F/S visibles + critères sélectionnés + jugements
- ✅ Chargement depuis `larcauth_learnerpei_has_termsubjectpei` / DP
- ✅ Matching élèves → notes via `fk_student_id` (colonne ajoutée au seed)
- ✅ Fallback pour bases anciennes → message "relancez --mode4"
- ✅ Édition par double-clic → `_dirty_cells` trackées
- ✅ `_save_grid_edits()` : écrit en SQLite avant sync/fermeture

### EvalManagerWindow
- ✅ Fenêtre non-modale avec `_SlotBar`, tabs F01-F12, éditeur markdown
- ✅ Critères A/B/C/D + légende via `larcauth_criteria_of_levelsubject`
- ✅ Affichage progressif : actifs + suivant grisé
- ✅ Correcteur orthographique (`pyenchant` optionnel)

### SyncManager
- ✅ `common/sync.py` : diff cellule via shadow-tables `_ref`, pull/push/conflit
- ✅ `sync_state` : timestamp par table
- ✅ Bouton **Synchroniser** branché
- ✅ **Enregistrer et quitter** : sauvegarde grille → sync → fermeture

## 4. Problèmes Connus

### Données serveur T3
- Prof 1021 (Patrice LABONNE), trimestre 3 : 189 évaluations, **0 critères cochés**
- Tous les `crit_a..crit_d` = `'0'` → aucune évaluation active affichée
- Les évals actives sont sur T1-T2 uniquement
- → Problème de données, pas de code

### Bases anciennes
- Les PEI/DP tables créées avant le 2 juin 2026 n'ont pas `fk_student_id`
- Solution : message en barre d'état → relancer `--mode4`

## 5. Reste à Faire (Priorité)
1. Appliquer les scripts SQL `01_add_sync_columns.sql` + `02_create_triggers.sql` sur Intranet et Cloud
2. Aligner `common/sync.py` (device) sur le système `sync_listeMAJ` (actuellement en shadow-tables)
3. Validation des notes (0-8 PEI / 0-20 DP)
4. Jeu de test pour données T3
5. Dashboard par rôle (PROF, COORD, SECR, ADMIN)
6. Test sur données réelles T1/T2

## 6. Documentation
- `CONTEXT.md` — à jour (3 juin)
- `docs/etat_projet.md` — à jour
- `docs/16_main_window.md` — réécrit (layout top bar)
- `docs/historique_construction.md` — itérations 18-20 ajoutées
- `docs/README.md` — index à jour
- `docs/20_eval_manager.md` — documentation EvalManagerWindow

---

_Mémoire persistante eLarcProfPy — 3 juin 2026_
