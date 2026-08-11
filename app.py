from flask import Flask, request, redirect, session, render_template_string, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "gota-manantial-final"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gota.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(200))
    rol = db.Column(db.String(20)) # sistemas, admin, secre, chofer
    nombre = db.Column(db.String(100))

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente = db.Column(db.String(100))
    direccion = db.Column(db.String(200))
    cantidad = db.Column(db.Integer)
    precio = db.Column(db.Float, default=22)
    estado = db.Column(db.String(20), default="Pendiente")
    chofer_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    fecha = db.Column(db.DateTime, default=datetime.now)

class Ubicacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chofer_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    fecha = db.Column(db.DateTime, default=datetime.now)

@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = Usuario.query.filter_by(username=request.form['username']).first()
        if u and check_password_hash(u.password, request.form['password']):
            session['user_id'] = u.id; session['rol'] = u.rol; session['nombre'] = u.nombre
            return redirect("/panel")
        return render_template_string(LOGIN, error="Mal")
    return render_template_string(LOGIN, error=None)

@app.route("/panel")
def panel():
    if 'user_id' not in session: return redirect("/")
    pedidos = Pedido.query.order_by(Pedido.fecha.desc()).all()
    choferes = Usuario.query.filter_by(rol='chofer').all()
    
    # Diccionario para mostrar nombre en vez de ID
    choferes_dict = {c.id: c.nombre for c in Usuario.query.all()}

    if session['rol'] == 'chofer':
        mis_pedidos = [p for p in pedidos if p.chofer_id == session['user_id']]
        return render_template_string(CHOFER_HTML, pedidos=mis_pedidos, nombre=session['nombre'], dict=choferes_dict)
    
    hoy = datetime.now().date()
    entregados_hoy = [p for p in pedidos if p.fecha.date() == hoy and p.estado == 'Entregado']
    total_hoy = sum(p.cantidad * p.precio for p in entregados_hoy)
    usuarios = Usuario.query.all() if session['rol'] == 'sistemas' else []
    return render_template_string(ADMIN_HTML, pedidos=pedidos, choferes=choferes, usuarios=usuarios, total_hoy=total_hoy, entregados_hoy=len(entregados_hoy), rol=session['rol'], nombre=session['nombre'], dict=choferes_dict)

@app.route("/pedido/nuevo", methods=["POST"])
def nuevo_pedido():
    if 'user_id' not in session: return redirect("/")
    p = Pedido(cliente=request.form['cliente'], direccion=request.form['direccion'], cantidad=int(request.form['cantidad']), precio=float(request.form.get('precio',22)), chofer_id=int(request.form['chofer_id']) if request.form['chofer_id'] else None)
    db.session.add(p); db.session.commit()
    return redirect("/panel")

@app.route("/pedido/entregar/<int:id>")
def entregar(id):
    p = Pedido.query.get(id); 
    if p: p.estado = "Entregado"; db.session.commit()
    return redirect("/panel")

@app.route("/usuario/nuevo", methods=["POST"])
def nuevo_usuario():
    if session.get('rol') != 'sistemas': return redirect("/panel")
    u = Usuario(username=request.form['username'], password=generate_password_hash(request.form['password']), rol=request.form['rol'], nombre=request.form['nombre'])
    db.session.add(u); db.session.commit()
    return redirect("/panel")

@app.route("/chofer/update_location", methods=["POST"])
def update_location():
    d = request.json or {}; db.session.add(Ubicacion(chofer_id=session['user_id'], lat=d.get('lat'), lng=d.get('lng'))); db.session.commit()
    return jsonify(ok=True)

@app.route("/logout")
def logout(): session.clear(); return redirect("/")

LOGIN = """<body style="font-family:Arial;background:#ecfeff;display:flex;justify-content:center;align-items:center;height:100vh"><div style="background:white;padding:30px;border-radius:15px;text-align:center;width:320px"><h2>💧 GOTA MANANTIAL</h2>{% if error %}<p style="color:red">{{error}}</p>{% endif %}<form method="post"><input name="username" placeholder="Usuario" required style="width:100%;padding:12px;margin:6px 0"><input name="password" type="password" placeholder="Contraseña" required style="width:100%;padding:12px;margin:6px 0"><button style="width:100%;padding:12px;background:#0891b2;color:white;border:none;border-radius:8px">Entrar</button></form><p style="font-size:11px;color:#666">sistemas/sistemas123 | admin/admin123 | secre/secre123 | chofer1/chofer123</p></div></body>"""

ADMIN_HTML = """
<body style="font-family:Arial;background:#f3f4f6;margin:0"><div style="background:white;padding:12px;display:flex;justify-content:space-between"><b>💧 {{nombre}} ({{rol}})</b><a href="/logout" style="color:red">Salir</a></div><div style="padding:15px">
<div style="display:flex;gap:10px;flex-wrap:wrap"><div style="background:white;padding:15px;border-radius:10px;flex:1"><h3>Corte Hoy</h3><h2>${{total_hoy}}</h2><p>{{entregados_hoy}} entregados</p></div>
<div style="background:white;padding:15px;border-radius:10px;flex:2"><h3>Nuevo Pedido (sin teléfono)</h3>
<form action="/pedido/nuevo" method="post" style="display:flex;gap:6px;flex-wrap:wrap"><input name="cliente" placeholder="Cliente" required style="flex:1;padding:8px"><input name="direccion" placeholder="Dirección" required style="flex:2;padding:8px"><input name="cantidad" type="number" value="1" style="width:60px"><input name="precio" type="number" value="22" style="width:60px"><select name="chofer_id" style="flex:1"><option value="">Sin chofer</option>{% for c in choferes %}<option value="{{c.id}}">{{c.nombre}}</option>{% endfor %}</select><button style="background:#0891b2;color:white;border:none;padding:8px 15px;border-radius:6px">Crear</button></form></div></div>
{% if rol == 'sistemas' %}<div style="background:white;padding:15px;border-radius:10px;margin-top:15px"><h3>👨‍💻 Panel Sistemas - Crear Usuarios</h3><form action="/usuario/nuevo" method="post" style="display:flex;gap:6px;flex-wrap:wrap"><input name="nombre" placeholder="Nombre completo" required style="padding:8px"><input name="username" placeholder="Usuario" required style="padding:8px"><input name="password" placeholder="Contraseña" required style="padding:8px"><select name="rol" style="padding:8px"><option value="chofer">Chofer</option><option value="secre">Secretaria</option><option value="admin">Admin</option><option value="sistemas">Sistemas</option></select><button style="background:black;color:white;padding:8px 15px">Crear Usuario</button></form><p style="font-size:12px">Usuarios actuales: {% for u in usuarios %}{{u.nombre}} ({{u.username}}/{{u.rol}}) | {% endfor %}</p></div>{% endif %}
<h3>Pedidos - Ruta</h3><table style="width:100%;background:white;border-radius:10px;border-collapse:collapse"><tr style="background:#ecfeff"><th style="padding:8px">ID</th><th>Cliente</th><th>Dirección</th><th>Chofer Ruta</th><th>Estado</th><th>Acción</th></tr>{% for p in pedidos %}<tr style="border-bottom:1px solid #eee"><td style="padding:8px">{{p.id}}</td><td>{{p.cliente}}</td><td>{{p.direccion}} ({{p.cantidad}} garrafones)</td><td><b>{{ dict.get(p.chofer_id, 'Sin asignar') }}</b></td><td>{{p.estado}}</td><td><a href="https://waze.com/ul?q={{p.direccion}}" target="_blank">Waze</a> | <a href="/pedido/entregar/{{p.id}}">Entregado</a></td></tr>{% endfor %}</table></div></body>
"""

CHOFER_HTML = """<body style="font-family:Arial;background:#f0fdf4;margin:0"><div style="background:white;padding:12px;display:flex;justify-content:space-between"><b>🚚 {{nombre}} - Mis Pedidos</b><a href="/logout">Salir</a></div><div style="padding:15px"><div style="background:#dcfce7;padding:10px;border-radius:8px;margin-bottom:10px">📍 GPS: <span id="gps">Buscando...</span></div>{% for p in pedidos %}<div style="background:white;padding:15px;border-radius:10px;margin-bottom:10px"><h3>{{p.cliente}} - {{p.cantidad}} garrafones</h3><p>{{p.direccion}}</p><a href="https://waze.com/ul?q={{p.direccion}}" target="_blank" style="background:#3b82f6;color:white;padding:10px 15px;border-radius:8px;text-decoration:none">Waze</a> {% if p.estado != 'Entregado' %}<a href="/pedido/entregar/{{p.id}}" style="background:#f59e0b;color:white;padding:10px 15px;border-radius:8px;text-decoration:none">Entregado</a>{% endif %}</div>{% endfor %}</div><script>function s(p){document.getElementById('gps').innerText=p.coords.latitude.toFixed(5)+','+p.coords.longitude.toFixed(5);fetch('/chofer/update_location',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lat:p.coords.latitude,lng:p.coords.longitude})});}setInterval(()=>navigator.geolocation.getCurrentPosition(s),15000);navigator.geolocation.getCurrentPosition(s);</script></body>"""

with app.app_context():
    db.create_all()
    if not Usuario.query.filter_by(username='sistemas').first():
        db.session.add(Usuario(username='sistemas', password=generate_password_hash('sistemas123'), rol='sistemas', nombre='Sistemas'))
        db.session.add(Usuario(username='admin', password=generate_password_hash('admin123'), rol='admin', nombre='Admin'))
        db.session.add(Usuario(username='secre', password=generate_password_hash('secre123'), rol='secre', nombre='Karina'))
        db.session.add(Usuario(username='chofer1', password=generate_password_hash('chofer123'), rol='chofer', nombre='Alfonso'))
        db.session.add(Usuario(username='chofer2', password=generate_password_hash('chofer123'), rol='chofer', nombre='Juan'))
        db.session.commit()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
