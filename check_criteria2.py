import sqlite3
conn = sqlite3.connect("elarc.anonyme.db")
cur = conn.cursor()

cur.execute("""
    SELECT name FROM sqlite_master
    WHERE type='table' AND name='larcauth_criteria_of_levelsubject'
""")
print("table exists:", cur.fetchone())

cur.execute("SELECT COUNT(*) FROM larcauth_criteria_of_levelsubject")
print("row count:", cur.fetchone()[0])

cur.execute("SELECT DISTINCT fk_levelsubject_id FROM larcauth_criteria_of_levelsubject LIMIT 5")
print("ls_ids:", [r[0] for r in cur.fetchall()])

cur.execute("SELECT DISTINCT fk_classroom_termsubject_id FROM larcauth_evaluation LIMIT 5")
for r in cur.fetchall():
    tid = r[0]
    cur.execute("SELECT fk_levelsubject_id FROM larcauth_classroom_termsubject WHERE id=?", (tid,))
    ls = cur.fetchone()
    if ls:
        cur.execute("""
            SELECT criteria_letter, criteria_label
            FROM larcauth_criteria_of_levelsubject WHERE fk_levelsubject_id=?
        """, (ls[0],))
        crits = cur.fetchall()
        print(f"  ts {tid}: ls {ls[0]}, crits {crits}")
    else:
        print(f"  ts {tid}: no classroom_termsubject row")

conn.close()
