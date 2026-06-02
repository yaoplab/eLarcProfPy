# État de la documentation, du contexte et de l'historique (bis)

_Audit vérifié le 31 mai 2026 — comparaison code réel ↔ `elarc.db` ↔ docs/ ↔ CONTEXT.md ↔ historique_
_Dernière mise à jour : 31 mai 2026 (Tables termothersubject ajoutées + duplications nettoyées)_

## Verdict global

Les bugs DB sont corrigés. Le SyncManager est implémenté. Le bouton "Enregistrer ce slot" fonctionne. Les tables `termothersubject` sont intégrées au seed.

Légende : ✅ Vérifié et conforme · ⚠️ Vérifié et partiellement faux/obsolète · ❌ Vérifié et faux

---

## 1. Écarts SCHÉMA / DDL (Corrigés)

### ✅ 1.1 `_DDL` de `sqlite_init.py` — CORREGÉ
### ✅ 1.2 Colonne `source` — AJOUTÉE au DDL, retirée des requêtes IHM
### ✅ 1.3 `larcauth_criteria_of_levelsubject` — AJOUTÉE
### ✅ 1.4 Duplications DDL — NETTOYÉES

---

## 2. Bugs Auth (Corrigés)

### ✅ 2.1 `larcib_term` → `larcauth_term` — CORREGÉ
### ✅ 2.2 `enabled = TRUE` supprimé — CORREGÉ

---

## 3. SyncManager (IMPLÉMENTÉ)

### ✅ 3.1 `common/sync.py` — COMPLÈTEMENT IMPLÉMENTÉ
### ✅ 3.2 Boutons branchés dans `main_window.py`

---

## 4. Bug IHM — "Enregistrer ce slot" (CORRIGÉ)

### ✅ 4.1 `views/eval_manager.py` — `_on_save_slot()` corrigé
### ✅ 4.2 `views/evaluation_panel.py` — `_save_criteria()` et `load_evaluations()` corrigés
### ✅ 4.3 `EvalManagerWindow` — statusBar ajoutée

---

## 5. Nouvelles tables métier (AJOUTÉES)

### ✅ 5.1 `larcauth_classroom_termothersubject` — DDL + _ref + seed + verify_tables
- Clé étrangère professeur : `fk_supervisor_id`
### ✅ 5.2 `larcauth_learner_has_termothersubject` — DDL + _ref + seed + verify_tables
### ✅ 5.3 `BUSINESS_TABLES` étendue aux 5 tables

---

## 6. Écarts Documentation `docs/` (À corriger)

### ⚠️ 6.1 `docs/README.md` — Index incomplet
### ⚠️ 6.2 `docs/16_main_window.md` — Obsolète
### ⚠️ 6.3 `docs/19_evaluation_panel.md` — Obsolète
### ⚠️ 6.4 `docs/18_tableau_de_bord_prof.md` — Cible non implémentée

---

## 7. Écarts `CONTEXT.md`

### ⚠️ 7.1 Arbre des fichiers incomplet
### ✅ 7.2 Philosophie & Sync — Conform

---

## 8. Écarts `historique_construction.md`

### ⚠️ 8.1 Numérotation erronée

---

## 9. Documentation manquante

- ❌ `docs/21_sync_manager.md` à créer
- ❌ Scripts utilitaires racine non documentés
