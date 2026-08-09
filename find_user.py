import psycopg2

url = "postgresql://neondb_owner:npg_YaC69HIAGyZn@ep-muddy-darkness-ai9gl7w1-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require"
conn = psycopg2.connect(url)
cur = conn.cursor()
cur.execute("SELECT id, username, email, phone, country, date_creation FROM \"user\" WHERE username = %s", ('florant12',))
row = cur.fetchone()
if row:
    print(f"ID: {row[0]}")
    print(f"Username: {row[1]}")
    print(f"Email: {row[2]}")
    print(f"Phone: {row[3]}")
    print(f"Country: {row[4]}")
    print(f"Date: {row[5]}")
else:
    print("NOT FOUND")
conn.close(){% endraw %}