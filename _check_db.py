import sqlite3
conn = sqlite3.connect(r'cluster_a.db')
c = conn.cursor()

# Check profiles table structure
c.execute("PRAGMA table_info(profiles)")
cols = c.fetchall()
print("profiles columns:")
for col in cols:
    print(f"  {col[1]} ({col[2]})")

# Check aspirant user
c.execute("SELECT * FROM profiles WHERE email='ravi.kumar@milletfoods.in'")
r = c.fetchone()
if r:
    col_names = [col[1] for col in cols]
    print("\nAspirant profile found:")
    for name, val in zip(col_names, r):
        print(f"  {name}: {val}")
else:
    print("\nNo aspirant with email ravi.kumar@milletfoods.in found")
    c.execute("SELECT id, email, role FROM profiles")
    for row in c.fetchall():
        print(f"  {row}")

conn.close()
