import sqlite3
conn = sqlite3.connect(r'C:\Projets\eLarcProfPy\elarc.db')

# Y a-t-il des evaluations avec au moins 1 critère coché?
cur = conn.execute('''
    SELECT id, index_eval, type_evaluation, fk_classroom_termsubject_id,
           crit_a, crit_b, crit_c, crit_d
    FROM larcauth_evaluation
    WHERE (crit_a != '0' OR crit_b != '0' OR crit_c != '0' OR crit_d != '0')
    LIMIT 10
''')
rows = cur.fetchall()
print(f'Evaluations avec critères cochés: {len(rows)}')
for r in rows:
    print(f'  id={r[0]} idx={r[1]} type={r[2]} fk={r[3]} crits={r[4:8]}')

# Combien de fk_classroom_termsubject_id uniques?
cur = conn.execute('SELECT DISTINCT fk_classroom_termsubject_id FROM larcauth_evaluation')
fks = [r[0] for r in cur.fetchall()]
print(f'\nfk_classroom_termsubject_id uniques: {fks}')

# Quel type sont les fk?
print(f'\nType de fk: {type(fks[0]) if fks else "N/A"}')

# Vérifier si le filtre fonctionne avec type text
cur = conn.execute('''
    SELECT COUNT(*) FROM larcauth_evaluation
    WHERE fk_classroom_termsubject_id = '1258113'
      AND CAST(index_eval AS INTEGER) BETWEEN 1 AND 12
''')
print(f"SELECT avec string '1258113': {cur.fetchone()[0]} lignes")

cur = conn.execute('''
    SELECT COUNT(*) FROM larcauth_evaluation
    WHERE fk_classroom_termsubject_id = 1258113
      AND CAST(index_eval AS INTEGER) BETWEEN 1 AND 12
''')
print(f"SELECT avec int 1258113: {cur.fetchone()[0]} lignes")

# Données PEI
print('\n--- PEI: 5 premières lignes (toutes colonnes note) ---')
cur = conn.execute('SELECT * FROM larcauth_learnerpei_has_termsubjectpei LIMIT 2')
cols = [d[0] for d in cur.description]
for r in cur.fetchall():
    non_null = [(cols[i], r[i]) for i in range(len(r)) if r[i] is not None and r[i] != '']
    print(f'  Non-nuls: {non_null[:10]}')

conn.close()
