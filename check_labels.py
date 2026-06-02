import sqlite3
conn = sqlite3.connect('elarc.anonyme.db')
cur = conn.cursor()

# Toutes les colonnes
cur.execute('PRAGMA table_info(larcauth_evaluation)')
print('=== larcauth_evaluation colonnes ===')
for c in cur.fetchall():
    print(f'  {c[1]}')

# Valeurs de label
print()
cur.execute("SELECT DISTINCT label FROM larcauth_evaluation WHERE type_evaluation IN ('F','S') ORDER BY label")
for r in cur.fetchall():
    print(f'  label = {repr(r[0])}')

# Voir des échantillons complets
print()
cur.execute("SELECT * FROM larcauth_evaluation WHERE type_evaluation='S' AND index_eval='1' LIMIT 2")
rows = cur.fetchall()
col_names = [d[0] for d in cur.description]
for r in rows:
    print('--- S01 sample ---')
    for i, v in enumerate(r):
        if v is not None:
            print(f'  {col_names[i]} = {repr(v)}')

# classroom_termsubject labels
print()
cur.execute("SELECT id, label, description FROM larcauth_classroom_termsubject LIMIT 5")
print('=== classroom_termsubject ===')
col_names = [d[0] for d in cur.description]
for r in cur.fetchall():
    for i, v in enumerate(r):
        if v is not None:
            print(f'  {col_names[i]} = {repr(v)}')
    print()

conn.close()
