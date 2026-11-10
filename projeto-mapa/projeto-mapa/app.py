import os, json, sqlite3, secrets, time
from flask import Flask, request, jsonify, session, send_from_directory, redirect

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
STATIC = os.path.join(BASE, "static")
DB = os.path.join(DATA, "mapa.db")
os.makedirs(DATA, exist_ok=True)

keyfile = os.path.join(DATA, "secret.key")
if not os.path.exists(keyfile):
    with open(keyfile, "w") as f:
        f.write(secrets.token_hex(32))
    os.chmod(keyfile, 0o600)

app = Flask(__name__)
app.secret_key = open(keyfile).read().strip()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Strict",
    SESSION_COOKIE_SECURE=os.environ.get("MAPA_HTTPS") == "1",
    PERMANENT_SESSION_LIFETIME=60 * 60 * 12,
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,
)

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

with db() as c:
    c.execute("create table if not exists users(id integer primary key, username text unique not null, pw text not null)")
    c.execute("create table if not exists state(id integer primary key check(id=1), data text not null, updated text, usuario text)")
    c.execute("create table if not exists history(id integer primary key, ts text not null, usuario text, andar integer, sala text, dev_id text, dev_nome text, campo text, rotulo text, antes text, depois text, acao text)")
    c.execute("create index if not exists hist_dev on history(dev_id)")

LBL = {"worker": "Nome / trabalhador", "tag": "Código / IP", "type": "Tipo", "status": "Status", "host": "Nome do host",
       "ip": "Endereço IP", "anydesk": "ID Anydesk", "mac": "Endereço MAC", "modelo": "Modelo", "serie": "Nº de série",
       "so": "Sistema operacional", "fw": "Firmware", "vlan": "VLAN", "obs": "Observações", "users": "Usuários",
       "extra": "Configurações adicionais", "setor": "Setor/Sala", "notas": "Notas"}

def devmap(s):
    m, rooms = {}, {}
    for fi, rs in enumerate(s.get("floors") or []):
        for r in rs:
            rooms[r.get("id")] = (fi, r.get("name", ""))
            for p in r.get("pcs") or []:
                m[p.get("id")] = (fi, r.get("name", ""), p)
    return m, rooms

def fields(p):
    f = {"worker": p.get("worker") or "", "tag": p.get("tag") or "", "type": p.get("type") or "Computador",
         "status": p.get("status") or "Ativo", "setor": p.get("setor") or ""}
    for k, v in (p.get("cfg") or {}).items():
        f[k] = str(v or "")
    f["users"] = ", ".join(p.get("users") or [])
    f["extra"] = "; ".join("%s=%s" % (x.get("k", ""), x.get("v", "")) for x in (p.get("extra") or []) if x.get("k") or x.get("v"))
    for o in p.get("occ") or []:
        f["occ:" + str(o.get("id"))] = "%s | %s | %s" % (o.get("problema", ""), o.get("situacao", ""), o.get("solucao", ""))
    return f

def log(c, user, fi, sala, did, dnome, campo, rot, antes, depois, acao):
    if acao == "alterado":
        r = c.execute("select id, antes from history where usuario=? and dev_id=? and campo=? "
                      "and ts > datetime('now','-300 seconds') order by id desc limit 1", (user, did, campo)).fetchone()
        if r:
            if r["antes"] == depois:
                c.execute("delete from history where id=?", (r["id"],))
            else:
                c.execute("update history set depois=?, ts=datetime('now') where id=?", (depois, r["id"]))
            return
    c.execute("insert into history(ts,usuario,andar,sala,dev_id,dev_nome,campo,rotulo,antes,depois,acao) "
              "values(datetime('now'),?,?,?,?,?,?,?,?,?,?)", (user, fi, sala, did, dnome, campo, rot, antes, depois, acao))

def diff(c, old, new, user):
    ch = []
    om, orooms = devmap(old)
    nm, nrooms = devmap(new)
    nome = lambda p: p.get("worker") or p.get("tag") or p.get("type") or "Dispositivo"
    for rid, (fi, name) in nrooms.items():
        if rid not in orooms:
            ch.append((fi, name, "", "", "", "", "", name, "sala adicionada"))
        elif orooms[rid][1] != name:
            ch.append((fi, name, "", "", "sala", "Nome da sala", orooms[rid][1], name, "sala renomeada"))
    for rid, (fi, name) in orooms.items():
        if rid not in nrooms:
            ch.append((fi, name, "", "", "", "", name, "", "sala removida"))
    for did, (fi, sala, p) in nm.items():
        if did not in om:
            ch.append((fi, sala, did, nome(p), "", "", "", p.get("type") or "Computador", "dispositivo adicionado"))
        else:
            a, b = fields(om[did][2]), fields(p)
            for k in sorted(set(a) | set(b)):
                if a.get(k, "") != b.get(k, ""):
                    rot = "Ocorrência" if k.startswith("occ:") else LBL.get(k, k)
                    ch.append((fi, sala, did, nome(p), k, rot, a.get(k, ""), b.get(k, ""), "alterado"))
    for did, (fi, sala, p) in om.items():
        if did not in nm:
            ch.append((fi, sala, did, nome(p), "", "", "", "", "dispositivo removido"))
    if len(ch) > 300:
        ch = [(None, "", "", "", "", "", "", "%d mudanças" % len(ch), "alteração em massa")]
    for t in ch:
        log(c, user, *t)

fails = {}

def blocked(ip):
    n, t = fails.get(ip, (0, 0))
    return n >= 5 and time.time() - t < 300

@app.after_request
def headers(r):
    r.headers["Cache-Control"] = "no-store"
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["X-Frame-Options"] = "DENY"
    return r

@app.get("/")
def index():
    if "u" not in session:
        return redirect("/login.html")
    return send_from_directory(STATIC, "index.html")

@app.get("/login.html")
def login_page():
    return send_from_directory(STATIC, "login.html")

@app.post("/api/login")
def login():
    ip = request.remote_addr
    if blocked(ip):
        return jsonify(error="Muitas tentativas. Aguarde 5 minutos."), 429
    d = request.get_json(silent=True) or {}
    from werkzeug.security import check_password_hash
    with db() as c:
        u = c.execute("select * from users where username=?", (str(d.get("username", "")).strip().lower(),)).fetchone()
    if u and check_password_hash(u["pw"], str(d.get("password", ""))):
        fails.pop(ip, None)
        session.clear()
        session["u"] = u["username"]
        session.permanent = True
        return jsonify(ok=True)
    n, _ = fails.get(ip, (0, 0))
    fails[ip] = (n + 1, time.time())
    return jsonify(error="Usuário ou senha inválidos."), 401

@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(ok=True)

@app.get("/api/state")
def get_state():
    if "u" not in session:
        return jsonify(error="auth"), 401
    with db() as c:
        r = c.execute("select data from state where id=1").fetchone()
    return app.response_class(r["data"] if r else "null", mimetype="application/json")

@app.put("/api/state")
def put_state():
    if "u" not in session:
        return jsonify(error="auth"), 401
    d = request.get_json(silent=True)
    if not isinstance(d, dict) or not isinstance(d.get("floors"), list) or len(d["floors"]) != 8:
        return jsonify(error="dados inválidos"), 400
    with db() as c:
        r = c.execute("select data from state where id=1").fetchone()
        if r:
            try:
                diff(c, json.loads(r["data"]), d, session["u"])
            except Exception:
                app.logger.exception("historico")
        c.execute("insert into state(id,data,updated,usuario) values(1,?,datetime('now'),?) "
                  "on conflict(id) do update set data=excluded.data, updated=excluded.updated, usuario=excluded.usuario",
                  (json.dumps(d, ensure_ascii=False), session["u"]))
    return jsonify(ok=True)

@app.get("/api/me")
def me():
    if "u" not in session:
        return jsonify(error="auth"), 401
    return jsonify(user=session["u"])

@app.get("/api/history")
def history():
    if "u" not in session:
        return jsonify(error="auth"), 401
    dev = request.args.get("device", "")
    try:
        lim = max(1, min(int(request.args.get("limit", "200")), 500))
    except ValueError:
        lim = 200
    q = "select * from history" + (" where dev_id=?" if dev else "") + " order by id desc limit ?"
    with db() as c:
        rows = c.execute(q, ((dev, lim) if dev else (lim,))).fetchall()
    return jsonify([dict(r) for r in rows])
