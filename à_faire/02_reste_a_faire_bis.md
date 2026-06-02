# Reste à faire — eLarcProfPy (bis)

_Checklist validée le 31 mai 2026 (vérifiée dans le code, `elarc.db` et la documentation)._
_Dernière mise à jour : 31 mai 2026 (Tables termothersubject ajoutées)._
_Fichier compagnon : `01_fait_bis.md`._

Légende priorité : 🔴 critique · 🟠 important · 🟢 confort/finition

---

## 1. Corrections critiques (✅ TERMINÉES)

- [x] ✅ Ajouter `source` au DDL
- [x] ✅ Corriger `larcib_term` → `larcauth_term`
- [x] ✅ Retirer `enabled = TRUE` sur `larcauth_teachadm`
- [x] ✅ Ajouter `larcauth_criteria_of_levelsubject` au DDL + `verify_tables()`
- [x] ✅ Nettoyage des duplications DDL
- [ ] 🟠 Vérifier `source` côté serveur PostgreSQL (`LarcNewCloudSchéma.sql`)

## 2. Nettoyage schéma (🟠)

- [ ] 🟠 Clarifier `sync_cursor` vs `sync_state`

## 3. SyncManager (✅ IMPLÉMENTÉ)

- [x] ✅ Toutes les méthodes implémentées
- [x] ✅ Boutons **Synchroniser** et **Enregistrer et quitter** branchés
- [ ] 🟢 Tests unitaires matrice de décision

## 4. Bug IHM — "Enregistrer ce slot" (✅ CORRIGÉ)

- [x] ✅ Retiré `source` de l'UPDATE et du SELECT
- [x] ✅ Ajout de feedback status bar dans `EvalManagerWindow`

## 5. Renommage "Slot" → "Évaluation" (✅ FAIT)

- [x] ✅ Bouton, fenêtres, messages, titres de panneaux

## 6. Nouvelles tables métier (✅ AJOUTÉES)

- [x] ✅ `larcauth_classroom_termothersubject` — DDL + _ref + seed + verify_tables
- [x] ✅ `larcauth_learner_has_termothersubject` — DDL + _ref + seed + verify_tables
- [x] ✅ Clé étrangère professeur : `fk_supervisor_id`
- [x] ✅ `BUSINESS_TABLES` étendue aux 5 tables

## 7. IHM & Fonctionnalités (🟠)

### 7.1 Grille élèves × notes
- **État :** Placeholder.
- [ ] 🔴 Construire la grille (`QTableWidget` / `QTableView`).
- [ ] 🔴 Colonnes dynamiques selon critères actifs.
- [ ] 🔴 Lecture/écriture des notes (PEI/DP).
- [ ] 🟠 Validateurs (0–8 PEI, 0–20 DP).

### 7.2 IHM de résolution de conflits
- [ ] 🟠 Créer `views/conflict_dialog.py`.
- [ ] 🟠 Brancher sur `SyncReport.conflicts`.

### 7.3 Autres
- [ ] 🟢 Remplacer le placeholder "Filtres".
- [ ] 🟢 Séparation PEI/DP (décidée doc 17, non implémentée).
- [ ] 🟢 Intégration des "autres matières" (termothersubject) dans l'écran général.

## 8. Documentation (🟠)

- [ ] 🟠 `docs/README.md` : ajouter 18 et 20.
- [ ] 🟠 `docs/16_main_window.md` : corriger widgets et boutons.
- [ ] 🟠 `docs/19_evaluation_panel.md` : corriger `get_form_data()`, grille 4×2.
- [ ] 🟠 `docs/18_tableau_de_bord_prof.md` : marquer "cible / non implémenté".
- [ ] 🟠 `historique_construction.md` : corriger doublons.
- [ ] 🟠 `CONTEXT.md` : ajouter `sync.py` et `eval_manager.py`.
- [ ] 🟢 Créer `docs/21_sync_manager.md`.

## 9. Qualité / nettoyage (🟢)

- [ ] 🟢 Remplacer `print(...)` par `logger`.
- [ ] 🟢 Nettoyer fichiers racine.
- [ ] 🟢 Vérifier `.gitignore`.
- [ ] 🟢 Gérer `id TEXT` (CAST).

---

## Ordre de réalisation

1. ~~Corrections critiques~~ — **TERMINÉ**.
2. ~~SyncManager~~ — **TERMINÉ**.
3. ~~Bug "Enregistrer ce slot"~~ — **TERMINÉ**.
4. ~~Renommage~~ — **TERMINÉ**.
5. ~~Tables termothersubject~~ — **TERMINÉ**.
6. **7.1** (grille élèves) — fonctionnalité centrale.
7. **7.2** (conflits), **7.3** (filtres, PEI/DP, termothersubject IHM).
8. **8** (doc) et **9** (qualité).
