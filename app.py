import os, json
from flask import Flask, render_template_string, request, redirect, url_for, session, send_file
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "gota-manantial-2026")
DATA_FILE = "data.json"
USERS_FILE = "users.json"

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

def get_logo_url():
    if os.path.exists("static/logo.png"):
        return "/static/logo.png"
    if os.path.exists("logo.png"):
        return "/logo.png"
    return "https://via.placeholder.com/150?text=GOTA"

DEFAULT_USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "bodega": {"password": "bodega123", "role": "bodega"},
    "corte": {"password": "corte123", "role": "corte"}
}

def get_users():
    u = load_json(USERS_FILE, None)
    if u is None:
        save_json(USERS_FILE, DEFAULT_USERS)
        return DEFAULT_USERS
    return u

def get_data():
    return load_json(DATA_FILE, [])

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role")!= "admin":
            return "No tienes permisos", 403
        return f(*args, **kwargs)
    return decorated

HTML = """
<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gota Manantial</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>body{background:#f4fbf6}.navbar{background:#0d6efd}.logo{height:40px;border-radius:8px;background:white;padding:2px}.card-stat{border-left:5px solid #0d6efd}.badge-extraviado{background:#dc3545}.badge-plantado{background:#198754}.badge-cosechado{background:#6f42c1}</style>
</head><body>
<nav class="navbar navbar-dark px-3 d-flex justify-content-between">
<a class="navbar-brand d-flex align-items-center gap-2" href="/"><img src="{{ logo_url }}" class="logo"> <b>Gota Manantial</b></a>
<div><span class="text-white me-2">👤 {{ session.user }} ({{ session.role }})</span><a href="/logout" class="btn btn-light btn-sm">Salir</a></div>
</nav>
<div class="container mt-4">
{% if session.role == 'admin' %}
<div class="row mb-3">
<div class="col-6 col-md-3"><div class="card p-3">Total: <b>{{ stats.total }}</b></div></div>
<div class="col-6 col-md-3"><div class="card p-3 border-danger">Extraviados: <b>{{ stats.extraviado }}</b></div></div>
<div class="col-6 col-md-3"><div class="card p-3" style="border-color:#198754">Plantados: <b>{{ stats.plantado }}</b></div></div>
<div class="col-6 col-md-3"><div class="card p-3" style="border-color:#6f42c1">Cosechados: <b>{{ stats.cosechado }}</b></div></div>
</div>{% endif %}
<ul class="nav nav-tabs mb-3">
<li class="nav-item"><a class="nav-link active" data-bs-toggle="tab" href="#lista">📋 Lista</a></li>
<li class="nav-item"><a class="nav-link" data-bs-toggle="tab" href="#mapa">🗺️ Mapa</a></li>
{% if session.role == 'admin' %}
<li class="nav-item"><a class="nav-link" data-bs-toggle="tab" href="#usuarios">👥 Usuarios</a></li>
<li class="nav-item"><a class="nav-link" data-bs-toggle="tab" href="#respaldo">💾 Respaldo</a></li>
{% endif %}</ul>
<div class="tab-content">
<div class="tab-pane fade show active" id="lista">
<div class="card p-3 mb-3"><h5>Nuevo Registro</h5>
<form method="POST" action="/add" class="row g-2">
<div class="col-md-2"><input name="lote" class="form-control" placeholder="Lote / Caja" required></div>
<div class="col-md-2"><select name="estatus" class="form-select"><option>En Bodega</option><option>En Corte</option><option value="Extraviado en Corte">🚨 Extraviado en Corte</option><option>Plantado</option><option>Cosechado</option></select></div>
<div class="col-md-2"><input name="cantidad" type="number" class="form-control" placeholder="Cantidad" required></div>
<div class="col-md-2"><input name="ubicacion" class="form-control" placeholder="Ubicación"></div>
<div class="col-md-2"><input name="coords" class="form-control" placeholder="Lat,Lon"></div>
<div class="col-md-2"><button class="btn btn-primary w-100">Guardar</button></div>
</form></div>
<div class="table-responsive"><table class="table table-striped table-sm"><thead><tr><th>Fecha</th><th>Lote</th><th>Estatus</th><th>Cant</th><th>Ubicación</th><th>Acción</th></tr></thead><tbody>
{% for r in data|reverse %}
<tr class="{{ 'table-danger' if r.estatus=='Extraviado en Corte' else '' }}"><td>{{ r.fecha }}</td><td><b>{{ r.lote }}</b></td><td>
{% if r.estatus=='Extraviado en Corte' %}<span class="badge bg-danger">{{ r.estatus }}</span>
{% elif r.estatus=='Plantado' %}<span class="badge bg-success">{{ r.estatus }}</span>
{% elif r.estatus=='Cosechado' %}<span class="badge" style="background:#6f42c1">{{ r.estatus }}</span>
{% else %}<span class="badge bg-secondary">{{ r.estatus }}</span>{% endif %}</td><td>{{ r.cantidad }}</td><td>{{ r.ubicacion }}</td>
<td><a href="/cambiar/{{ r.id }}/Plantado" class="btn btn-sm btn-success">Plantado</a><a href="/cambiar/{{ r.id }}/Cosechado" class="btn btn-sm btn-primary ms-1">Cosechado</a><a href="/cambiar/{{ r.id }}/Extraviado en Corte" class="btn btn-sm btn-danger ms-1">Extraviado</a>
{% if session.role=='admin' %}<a href="/del/{{ r.id }}" class="btn btn-sm btn-outline-danger ms-1">X</a>{% endif %}</td></tr>
{% endfor %}</tbody></table></div></div>
<div class="tab-pane fade" id="mapa"><div id="map" style="height:500px;border-radius:15px;"></div></div>
{% if session.role == 'admin' %}
<div class="tab-pane fade" id="usuarios"><div class="card p-3"><h5>Usuarios</h5>
<form method="POST" action="/add_user" class="row g-2 mb-3">
<div class="col-md-3"><input name="new_user" class="form-control" placeholder="Usuario" required></div>
<div class="col-md-3"><input name="new_pass" class="form-control" placeholder="Contraseña" required></div>
<div class="col-md-3"><select name="new_role" class="form-select"><option value="bodega">Bodega</option><option value="corte">Corte</option><option value="admin">Admin</option></select></div>
<div class="col-md-3"><button class="btn btn-dark w-100">Crear</button></div></form>
<table class="table table-sm"><tr><th>Usuario</th><th>Rol</th><th></th></tr>
{% for k,v in users.items() %}<tr><td>{{ k }}</td><td>{{ v.role }}</td><td>{% if k!='admin' %}<a href="/del_user/{{ k }}" class="btn btn-sm btn-danger">Borrar</a>{% endif %}</td></tr>{% endfor %}</table></div></div>
<div class="tab-pane fade" id="respaldo"><div class="card p-4 text-center"><h5>💾 Respaldo</h5><a href="/backup" class="btn btn-success btn-lg">Descargar Respaldo</a><hr>
<form method="POST" action="/restore" enctype="multipart/form-data"><input type="file" name="file" class="form-control mb-2" required><button class="btn btn-warning">Restaurar</button></form></div></div>
{% endif %}</div></div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
var map = L.map('map').setView([32.5149, -117.0382], 11);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
var data = {{ data|tojson }};
data.forEach(r=>{
  if(r.coords && r.coords.includes(',')){
    let p = r.coords.split(','); let lat=parseFloat(p[0]); let lon=parseFloat(p[1]);
    if(!isNaN(lat)) L.marker([lat,lon]).addTo(map).bindPopup(`<b>${r.lote}</b><br>${r.estatus}`);
  }
});
</script></body></html>
"""

LOGIN_HTML = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{background:#e8f5e9;display:flex;align-items:center;justify-content:center;height:100vh}</style>
</head><body><div class="card p-4 shadow" style="width:100%;max-width:350px">
<div class="text-center mb-3"><img src="{{ logo_url }}" style="height:80px;border-radius:15px"><h4 class="mt-2">Gota Manantial</h4></div>
<form method="POST"><input name="user" class="form-control mb-2" placeholder="Usuario" required><input name="password" type="password" class="form-control mb-3" placeholder="Contraseña" required><button class="btn btn-success w-100">Entrar</button></form>
{% if error %}<div class="alert alert-danger mt-3">{{ error }}</div>{% endif %}</div></body></html>"""

@app.route("/logo.png")
def logo_root():
    if os.path.exists("logo.png"):
        return send_file("logo.png", mimetype="image/png")
    if os.path.exists("static/logo.png"):
        return send_file("static/logo.png", mimetype="image/png")
    return "", 404

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        users=get_users(); u=request.form.get("user"); p=request.form.get("password")
        if u in users and users[u]["password"]==p:
            session["user"]=u; session["role"]=users[u]["role"]; return redirect("/")
        return render_template_string(LOGIN_HTML, logo_url=get_logo_url(), error="Usuario o contraseña mal")
    return render_template_string(LOGIN_HTML, logo_url=get_logo_url(), error=None)

@app.route("/logout")
def logout():
    session.clear(); return redirect("/login")

@app.route("/")
def index():
    if "user" not in session:
        return redirect("/login")
    data=get_data()
    stats={"total": len(data),"extraviado": len([d for d in data if d["estatus"]=="Extraviado en Corte"]),"plantado": len([d for d in data if d["estatus"]=="Plantado"]),"cosechado": len([d for d in data if d["estatus"]=="Cosechado"])}
    return render_template_string(HTML, data=data, users=get_users(), stats=stats, logo_url=get_logo_url(), session=session)

@app.route("/add", methods=["POST"])
def add():
    if "user" not in session: return redirect("/login")
    data=get_data(); new_id = max([d["id"] for d in data], default=0)+1
    data.append({"id": new_id,"fecha": datetime.now().strftime("%d/%m %H:%M"),"lote": request.form.get("lote"),"estatus": request.form.get("estatus"),"cantidad": request.form.get("cantidad"),"ubicacion": request.form.get("ubicacion"),"coords": request.form.get("coords","").strip(),"usuario": session.get("user")})
    save_json(DATA_FILE, data); return redirect("/")

@app.route("/cambiar/<int:rid>/<estatus>")
def cambiar(rid, estatus):
    if "user" not in session: return redirect("/login")
    data=get_data()
    for d in data:
        if d["id"]==rid: d["estatus"]=estatus
    save_json(DATA_FILE, data); return redirect("/")

@app.route("/del/<int:rid>")
def delete(rid):
    if session.get("role")!="admin": return "No permisos", 403
    data=get_data(); data=[d for d in data if d["id"]!=rid]; save_json(DATA_FILE, data); return redirect("/")

@app.route("/add_user", methods=["POST"])
def add_user():
    if session.get("role")!="admin": return "No permisos", 403
    users=get_users(); users[request.form.get("new_user")]={"password": request.form.get("new_pass"), "role": request.form.get("new_role")}; save_json(USERS_FILE, users); return redirect("/")

@app.route("/del_user/<user>")
def del_user(user):
    if session.get("role")!="admin": return "No permisos", 403
    users=get_users()
    if user in users and user!="admin": del users[user]; save_json(USERS_FILE, users)
    return redirect("/")

@app.route("/backup")
def backup():
    if session.get("role")