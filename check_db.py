import sqlite3

conn = sqlite3.connect('elarc.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
for t in tables:
    cur.execute(f'SELECT COUNT(*) FROM "{t}"')
    count = cur.fetchone()[0]
    # Show first row col names
    cur.execute(f'SELECT * FROM "{t}" LIMIT 1')
    if cur.description:
        cols = [d[0] for d in cur.description]
    else:
        cols = []
    print(f'{t}: {count} lignes, colonnes: {cols[:10]}...')
conn.close()
