import sys, getpass
from werkzeug.security import generate_password_hash
from app import db

name = input("Usuário: ").strip().lower()
pw = getpass.getpass("Senha (mínimo 10 caracteres): ")
if not name or len(pw) < 10:
    sys.exit("Usuário vazio ou senha curta demais.")
with db() as c:
    c.execute("insert into users(username,pw) values(?,?) on conflict(username) do update set pw=excluded.pw",
              (name, generate_password_hash(pw)))
print("Usuário salvo:", name)
