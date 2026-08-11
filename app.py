from flask import Flask, render_template_string, request, redirect, session, send_file, url_for
import json, os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "gota-secreta-2026"

DATA_FILE = "data.json"
USERS_FILE = "users.json"

DEFAULT_USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "bodega": {"password": "bodega123", "role": "bodega"},
    "corte": {"password": "corte123", "role": "corte"}
}

def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

@app.route("/logo.png")
def logo():
    return send_file("logo.png", mimetype="image/png")

@app.route("/", methods=["GET", "POST"])
def login():
    users = load_json(USERS_FILE, DEFAULT_USERS)
    if request.method == "POST":
        u = request.form.get("username","").strip()
        p = request.form.get("password","").strip()
        if u in users and users[u]["password"] == p:
            session["user"] = u
            session["role"] = users[u]["role"]
            return redirect("/panel")
        return render_template_string(LOGIN_HTML, error="Usuario o contraseña incorrecta")
    return render_template_string(LOGIN_HTML, error=None)

@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")
    data = load_json(DATA_FILE, [])
    users = load_json(USERS_FILE, DEFAULT_USERS)
    return render_template_string(PANEL_HTML, data=data, users=users, user=session["user"], role=session["role"], logo_url=url_for('logo'))

@app.route("/add", methods=["POST"])
def add():
    if "user" not in session:
        return redirect("/")
    data = load_json(DATA_FILE, [])
    nuevo = {
        "id": len(data)+1,
        "codigo": request.form.get("codigo","").strip(),
        "rancho": request.form.get("rancho","").strip(),
        "variedad": request.form.get("variedad","").strip(),
        "estado": request.form.get("estado","Plantado"),
        "coordenadas": request.form.get("coordenadas","").strip(),
        "extraviado": False,
        "fecha": datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    data.append(nuevo)
    save_json(DATA_FILE, data)
    return redirect("/panel")

@app.route("/accion/<int:pid>/<string:accion>")
def accion(pid, accion):
    if "user" not in session:
        return redirect("/")
    data = load_json(DATA_FILE, [])
    for row in data:
        if row["id"] == pid:
            if accion == "extraviado":
                row["extraviado"] = not row.get("extraviado", False)
            else:
                row["estado"] = accion
            break
    save_json(DATA_FILE, data)
    return redirect("/panel")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

LOGIN_HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>GOTA DE MANANTIAL</title>
<style>
body{font-family:Arial;background:#f0fdf4;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}
.card{background:white;padding:30px;border-radius:15px;box-shadow:0 5px 15px rgba(0,0,0,0.1);width:90%;max-width:350px;text-align:center}
input{width:100%;padding:12px;margin:8px 0;border-radius:8px;border:1px solid #ccc;box-sizing:border-box}
button{width:100%;padding:12px;background:#16a34a;color:white;border:none;border-radius:8px;font-weight:bold}
</style></head><body>
<div class="card">
<img src="/logo.png" style="width:80px;margin-bottom:10px" onerror="this.style.display='none'">
<h2 style="color:#16a34a;margin:5px">GOTA DE MANANTIAL</h2>
{% if error %}<p style="color:red">{{error}}</p>{% endif %}
<form method="post"><input name="username" placeholder="Usuario"><input name="password" type="password" placeholder="Contraseña"><button>Entrar</button></form>
</div></body></html>
"""

PANEL_HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Panel - GOTA</title>
<style>
body{font-family:Arial;background:#f3f4f6;margin:0}
.header{background:white;padding:10px 15px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 5px rgba(0,0,0,0.1)}
table{width:100%;border-collapse:collapse;background:white;margin-top:10px}
th,td{padding:8px;border-bottom:1px solid #eee;font-size:14px;text-align:left}
.extraviado{background:#fee2e2!important;color:#991b1b;font-weight:bold}
.badge{padding:3px 7px;border-radius:10px;font-size:12px}
.b-Plantado{background:#dcfce7;color:#166534}
.b-Cosechado{background:#fef9c3;color:#854d0e}
.btn{padding:5px 8px;border-radius:6px;border:none;font-size:12px;text-decoration:none;color:white;display:inline-block;margin:1px}
.btn-green{background:#16a34a}.btn-yellow{background:#ca8a04}.btn-red{background:#dc2626}
</style></head><body>
<div class="header">
<div style="display:flex;align-items:center;gap:10px"><img src="{{logo_url}}" style="width:35px"><b>GOTA DE MANANTIAL</b></div>
<div>{{user}} ({{role}}) <a href="/logout" style="color:red;margin-left:10px">Salir</a></div>
</div>
<div style="padding:15px">
<h3>Registrar Rancho</h3>
<form action="/add" method="post" style="background:white;padding:15px;border-radius:10px;display:flex;flex-wrap:wrap;gap:8px">
<input name="codigo" placeholder="Código" required style="flex:1"><input name="rancho" placeholder="Rancho" required style="flex:1"><input name="variedad" placeholder="Variedad" style="flex:1">
<input name="coordenadas" placeholder="25.1234,-107.1234" style="flex:1">
<select name="estado" style="flex:1;padding:8px;border-radius:6px"><option>Plantado</option><option>Cosechado</option></select>
<button style="background:#16a34a;color:white;border:none;padding:10px 20px;border-radius:8px">Guardar</button>
</form>
<table><tr><th>ID</th><th>Código</th><th>Rancho</th><th>Estado</th><th>Acción</th></tr>
{% for r in data %}
<tr class="{% if r.extraviado %}extraviado{% endif %}">
<td>{{r.id}}</td><td>{{r.codigo}}</td><td>{{r.rancho}}</td>
<td><span class="badge b-{{r.estado}}">{{r.estado}}</span>{% if r.extraviado %} 🚨 EXTRAVIADO{% endif %}</td>
<td>
<a class="btn btn-green" href="/accion/{{r.id}}/Plantado">Plantado</a>
<a class="btn btn-yellow" href="/accion/{{r.id}}/Cosechado">Cosechado</a>
<a class="btn btn-red" href="/accion/{{r.id}}/extraviado">🚨 Extraviado</a>
</td></tr>
{% endfor %}
</table>
</div></body></html>
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
