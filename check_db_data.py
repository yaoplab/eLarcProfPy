import sqlite3
conn = sqlite3.connect(r'C:\Projets\eLarcProfPy\elarc.db')

# Combien de lignes dans chaque table?
for t in ['larcauth_learnerpei_has_termsubjectpei', 'larcauth_learnerdp_has_termsubjectdp', 'larcauth_evaluation']:
    cur = conn.execute(f'SELECT COUNT(*) FROM "{t}"')
    print(f'{t}: {cur.fetchone()[0]} lignes')

# Avoir des notes non-nulles?
print('\n--- Notes PEI non-nulles ---')
cur = conn.execute('''
    SELECT f01_note_a, f01_note_b, f01_note_c, f01_note_d, note_on_7
    FROM larcauth_learnerpei_has_termsubjectpei
    LIMIT 5
''')
for r in cur.fetchall():
    print(f'  {r}')

# Evaluations
print('\n--- Evaluations (type_evaluation + critères) ---')
cur = conn.execute('''
    SELECT id, index_eval, type_evaluation, crit_a, crit_b, crit_c, crit_d
    FROM larcauth_evaluation
    ORDER BY type_evaluation, CAST(index_eval AS INTEGER)
    LIMIT 20
''')
for r in cur.fetchall():
    print(f'  id={r[0]} idx={r[1]} type={r[2]} crits={r[3:7]}')

# fk_classroom_termsubject_id types
print('\n--- eval fk types ---')
cur = conn.execute('SELECT typeof(fk_classroom_termsubject_id), fk_classroom_termsubject_id FROM larcauth_evaluation LIMIT 3')
for r in cur.fetchall():
    print(f'  type={r[0]} val={r[1]}')

conn.close()
