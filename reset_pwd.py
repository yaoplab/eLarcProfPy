import hashlib
import psycopg2

new_pass = "Aec-2026"
h = hashlib.sha256(new_pass.encode('utf-8')).hexdigest()
print(f'Hash SHA-256: {h}')

conn = psycopg2.connect(host='127.0.0.1', port=5432, dbname='NewLarcDB',
                        user='postgres', password='postgres')
cur = conn.cursor()
email = 'patrlabo@arc-en-ciel.org'
cur.execute("SELECT id, email FROM larcauth_aecuser WHERE LOWER(email) = %s", (email.lower(),))
row = cur.fetchone()
if row:
    print(f'Utilisateur trouvé: id={row[0]}, email={row[1]}')
    cur.execute("UPDATE larcauth_aecuser SET password = %s WHERE id = %s", (h, row[0]))
    conn.commit()
    print(f'Mot de passe réinitialisé à "{new_pass}"')
else:
    print(f'Utilisateur {email} NON trouvé')
conn.close()
