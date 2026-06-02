import sqlite3
conn = sqlite3.connect(r'C:\Projets\eLarcProfPy\elarc.db')
for table in ['larcauth_learnerpei_has_termsubjectpei', 'larcauth_learnerdp_has_termsubjectdp', 'larcauth_evaluation']:
    try:
        cur = conn.execute(f'PRAGMA table_info("{table}")')
        cols = [row[1] for row in cur.fetchall()]
        print(f'\n=== {table} ({len(cols)} colonnes) ===')
        for c in cols:
            print(f'  {c}')
    except Exception as e:
        print(f'{table}: ERREUR {e}')
conn.close()
