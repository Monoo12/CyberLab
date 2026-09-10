"""Crea la base sqlite con el usuario admin y una clave del diccionario.

La clave es debil a proposito (metodo 3, fuerza bruta) y ademas coincide con la
credencial filtrada en el HTML (metodo 1). El login concatena strings, asi que
tambien es vulnerable a SQL injection (metodo 2).
"""
import os
import sqlite3

DB_PATH = os.environ.get("LAB_DB", "/tmp/lab.db")
LAB_USER = os.environ.get("LAB_USER", "admin")
LAB_PASS = os.environ.get("LAB_PASS", "S3cr3t-2024!")


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password TEXT)")
    con.executemany(
        "INSERT INTO users (username, password) VALUES (?, ?)",
        [(LAB_USER, LAB_PASS), ("guest", "guest")],
    )
    con.commit()
    con.close()
    print("seed_db: base creada en", DB_PATH, "usuario", LAB_USER)


if __name__ == "__main__":
    main()
