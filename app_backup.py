from flask import Flask, request, redirect, session, render_template_string, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
from functools import wraps
import os

app = Flask(__name__)
app.jinja_env.globals.update(max=max)
app.secret_key = os.environ.get("SECRET_KEY", "gota-v11-segura-mxli-2026")
db_url = os.environ.get("DATABASE_URL", "sqlite:///gota.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
class Ubicacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chofer_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    velocidad = db.Column(db.Float, default=0) # <-- IMPORTANTE PARA LAS PARADAS
    fecha = db.Column(db.DateTime, default=datetime.now)

class Usuario(db.Model):
    __tablename__ = 'usuario'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    rol = db.Column(db.String(20), default='chofer') # 'admin', 'sistemas', 'chofer'
    tipo_chofer = db.Column(db.String(10), default='garrafon') # 'garrafon' o 'granel'
    
    # Campo necesario para la configuración del precio de agua por usuario
    precio_agua = db.Column(db.Float, default=22.0)
    
    # NUEVO CAMPO: Distingue el panel del chófer ('garrafon' o 'granel')
    tipo_chofer = db.Column(db.String(10), default='garrafon')


class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente = db.Column(db.String(100))
    direccion = db.Column(db.String(200))
    cantidad = db.Column(db.Integer)
    precio = db.Column(db.Float, default=22)
    estado = db.Column(db.String(20), default="Pendiente")
    chofer_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    fecha = db.Column(db.DateTime, default=datetime.now) # <-- AQUÍ CONTAMOS LOS GARRAFONES


class Corte(db.Model):
    __tablename__ = 'corte'
    
    id = db.Column(db.Integer, primary_key=True)
    chofer_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    
    # Discriminador del tipo de vendedor: 'garrafon' o 'granel'
    tipo_unidad = db.Column(db.String(10), default='garrafon')
    
    # Inventario inicial / final (Garrafones para ruta normal / Litros para granel)
    salio = db.Column(db.Float, default=0.0)
    regreso = db.Column(db.Float, default=0.0)
    
    # Campos específicos para venta a granel / nota
    folio_nota = db.Column(db.String(50), nullable=True)
    cliente_nombre = db.Column(db.String(100), nullable=True)
    cliente_direccion = db.Column(db.String(200), nullable=True)
    precio_por_litro = db.Column(db.Float, nullable=True)
    
    # Finanzas y detección de mermas/fugas
    total_dinero = db.Column(db.Float, default=0.0)
    fuga_alerta = db.Column(db.Boolean, default=False)
    diferencia_lts = db.Column(db.Float, default=0.0)
    
    # Registro de tiempo
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    # Relación con el modelo Usuario (para acceder a c.chofer.nombre)
    chofer = db.relationship('Usuario', backref=db.backref('cortes', lazy=True))

class Descuento(db.Model):
    id=db.Column(db.Integer, primary_key=True); chofer_id=db.Column(db.Integer, db.ForeignKey('usuario.id'))
    fecha=db.Column(db.Date, default=date.today); tipo=db.Column(db.String(20)); cantidad=db.Column(db.Integer, default=1); tamano=db.Column(db.String(200)); total=db.Column(db.Float, default=0)
class Solicitud(db.Model):
    id=db.Column(db.Integer, primary_key=True); chofer_id=db.Column(db.Integer, db.ForeignKey('usuario.id'))
    fecha=db.Column(db.DateTime, default=datetime.now); tamano=db.Column(db.String(50)); cantidad=db.Column(db.Integer, default=1)
    precio_estaba=db.Column(db.Float); precio_quedo=db.Column(db.Float); diferencia=db.Column(db.Float)
    direccion=db.Column(db.String(200)); motivo=db.Column(db.String(200)); estado=db.Column(db.String(20), default="Pendiente")

def login_required(f):
    @wraps(f)
    def w(*a, **kw):
        if 'user_id' not in session: return redirect("/")
        return f(*a, **kw)
    return w
def admin_required(f):
    @wraps(f)
    def w(*a, **kw):
        if session.get('rol') not in ('admin','sistemas'): return "No autorizado", 403
        return f(*a, **kw)
    return w

@app.route("/logo.png")
def logo_file():
    return send_from_directory(".", "logo.png") if os.path.exists("logo.png") else ("",404)

@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        u=Usuario.query.filter_by(username=request.form['username'].strip()).first()
        if u and check_password_hash(u.password, request.form['password']):
            session['user_id']=u.id; session['rol']=u.rol; session['nombre']=u.nombre; return redirect("/panel")
        return render_template_string(LOGIN_HTML, error="Usuario o contrasena mal")
    return render_template_string(LOGIN_HTML, error=None)

@app.route('/panel')
@login_required
def panel():
    if session.get('rol') not in ['admin', 'sistemas']:
        return redirect('/')

    try:
        cortes_hoy = Corte.query.all() if 'Corte' in globals() else []
        solicitudes = Solicitud.query.all() if 'Solicitud' in globals() else []
        usuarios_choferes = Usuario.query.filter_by(rol='chofer').all() if 'Usuario' in globals() else []

        return render_template_string(
            ADMIN_HTML,
            cortes=cortes_hoy,
            solicitudes=solicitudes,
            usuarios=usuarios_choferes,
            user={'username': session.get('username'), 'rol': session.get('rol')}
        )
    except Exception as e:
        db.session.rollback()
        import traceback
        return f"""
        <div style="padding:20px; background:#fff0f0; border:2px solid red; font-family:monospace;">
            <h3 style="color:red;">⚠️ Error al renderizar ADMIN_HTML:</h3>
            <p><b>{str(e)}</b></p>
            <pre style="background:#222; color:#0f0; padding:10px; border-radius:5px; overflow:auto;">{traceback.format_exc()}</pre>
        </div>
        """, 500
        
    except Exception as e:
        db.session.rollback()
        import traceback
        return f"""
        <div style="padding:20px; background:#fff0f0; border:2px solid red; font-family:monospace;">
            <h3 style="color:red;">⚠️ Error al renderizar ADMIN_HTML:</h3>
            <p><b>{str(e)}</b></p>
            <pre style="background:#222; color:#0f0; padding:10px; border-radius:5px; overflow:auto;">{traceback.format_exc()}</pre>
        </div>
        """, 500

    return render_template_string(ADMIN_HTML, pedidos=pedidos, choferes=choferes, dict=dict_choferes, usuarios=usuarios, rol=session['rol'], nombre=session['nombre'], solicitudes=solicitudes_pend)

@app.route("/pedido/nuevo", methods=["POST"])
@login_required
@admin_required
def nuevo_pedido():
    try:
        cid=request.form.get('chofer_id')
        if cid=="auto" or not cid: cid=None
        else:
            try: cid=int(cid)
            except: cid=None
            if cid==0: cid=None
        p=Pedido(cliente=request.form['cliente'][:100], direccion=request.form['direccion'][:200], cantidad=max(1,int(request.form['cantidad'])), precio=max(0,float(request.form.get('precio',22))), chofer_id=cid)
        db.session.add(p); db.session.commit()
    except: db.session.rollback()
    return redirect("/panel")

@app.route("/pedido/mover/<int:id>")
@login_required
@admin_required
def mover(id):
    p=db.session.get(Pedido,id); nc=request.args.get('chofer_id')
    if p and nc is not None:
        try:
            nc=int(nc); p.chofer_id=None if nc==0 else nc; db.session.commit()
        except: db.session.rollback()
    return redirect("/panel")

@app.route("/pedido/entregar/<int:id>")
@login_required
def entregar(id):
    p=db.session.get(Pedido,id)
    if p and (session['rol'] in ('admin','sistemas') or p.chofer_id==session['user_id']):
        p.estado="Entregado"; db.session.commit()
    return redirect("=/panel")

@app.route("/corte/update", methods=["POST"])
@login_required
def corte_up():
    hoy=date.today(); c=Corte.query.filter_by(chofer_id=session['user_id'], fecha=hoy).first()
    if not c: c=Corte(chofer_id=session['user_id'], fecha=hoy); db.session.add(c)
    try:
        c.salio=max(0,int(request.form.get('salio',0))); c.regreso=max(0,int(request.form.get('regreso',0)))
        if c.regreso > c.salio: c.regreso=c.salio
        db.session.commit()
    except: db.session.rollback()
    return redirect("/panel")

@app.route("/descuento/add", methods=["POST"])
@login_required
def desc_add():
    try:
        d=Descuento(chofer_id=session['user_id'], fecha=date.today(), tipo=request.form['tipo'][:20], cantidad=max(1,int(request.form.get('cantidad',1))), tamano=request.form.get('tamano','')[:200], total=max(0,float(request.form.get('total',0))))
        db.session.add(d); db.session.commit()
    except: db.session.rollback()
    return redirect("/panel")

@app.route("/descuento/borrar/<int:id>")
@login_required
def desc_del(id):
    d=db.session.get(Descuento,id)
    if d and (d.chofer_id==session['user_id'] or session['rol'] in ('admin','sistemas')):
        db.session.delete(d); db.session.commit()
    return redirect("/panel")

@app.route("/solicitar_precio", methods=["POST"])
@login_required
def solicitar_precio():
    try:
        estaba=float(request.form.get('estaba',0) or 0); quedo=float(request.form.get('quedo',0) or 0); cant=max(1,int(request.form.get('cantidad',1) or 1))
        if quedo<0 or quedo>=estaba: return redirect("/panel")
        dif=(estaba-quedo)*cant
        s=Solicitud(chofer_id=session['user_id'], tamano=request.form.get('tamano','')[:50], cantidad=cant, precio_estaba=estaba, precio_quedo=quedo, diferencia=dif, direccion=request.form.get('direccion','')[:200], motivo=request.form.get('motivo','')[:200])
        db.session.add(s); db.session.commit()
    except: db.session.rollback()
    return redirect("/panel")

@app.route("/autorizar/<int:id>")
@login_required
@admin_required
def autorizar(id):
    s=db.session.get(Solicitud,id)
    if s and s.estado=="Pendiente":
        s.estado="Autorizado"; d=Descuento(chofer_id=s.chofer_id, fecha=date.today(), tipo="descuento_precio", cantidad=s.cantidad, tamano=f"{s.tamano} ${s.precio_estaba}->{s.precio_quedo} {s.direccion}"[:200], total=max(0,s.diferencia))
        db.session.add(d); db.session.commit()
    return redirect("/panel")

@app.route("/rechazar/<int:id>")
@login_required
@admin_required
def rechazar(id):
    s=db.session.get(Solicitud,id)
    if s: s.estado="Rechazado"; db.session.commit()
    return redirect("/panel")

@app.route("/usuario/nuevo", methods=["POST"])
@login_required
@admin_required
def nuevo_usuario():
    try:
        u=Usuario(username=request.form['username'].strip()[:80], password=generate_password_hash(request.form['password']), rol=request.form['rol'], nombre=request.form['nombre'][:100], precio_agua=max(0,float(request.form.get('precio_agua',22))))
        db.session.add(u); db.session.commit()
    except Exception as e: db.session.rollback(); print(e)
    return redirect("/panel")

@app.route("/usuario/borrar/<int:id>")
@login_required
@admin_required
def borrar(id):
    u=db.session.get(Usuario,id)
    if u and u.username!='sistemas' and u.id!=session['user_id']: db.session.delete(u); db.session.commit()
    return redirect("/panel")

@app.route("/usuario/reset/<int:id>")
@login_required
@admin_required
def reset(id):
    u=db.session.get(Usuario,id)
    if u and u.username!='sistemas': u.password=generate_password_hash('123456'); db.session.commit()
    return redirect("/panel")

@app.route("/usuario/precio/<int:id>", methods=["POST"])
@login_required
@admin_required
def cambiar_precio(id):
    u=db.session.get(Usuario,id)
    if u: u.precio_agua=max(0,float(request.form.get('precio_agua',22))); db.session.commit()
    return redirect("/panel")

@app.route("/chofer/update_location", methods=["POST"])
@login_required
def up_loc():
    d=request.json or {}
    try:
        lat=float(d.get('lat')); lng=float(d.get('lng'))
        if -90<=lat<=90 and -180<=lng<=180:
            db.session.add(Ubicacion(chofer_id=session['user_id'], lat=lat, lng=lng)); db.session.commit()
    except: db.session.rollback()
    return jsonify(ok=True)

from datetime import timedelta

@app.route("/mapa/detallado/<int:chofer_id>")
@login_required
@admin_required
def mapa_detallado(chofer_id):
    ch = db.session.get(Usuario, chofer_id)
    hoy = date.today().strftime('%Y-%m-%d')
    
    # Traemos todos los puntos de la ruta de hoy
    puntos = Ubicacion.query.filter_by(chofer_id=chofer_id).filter(
    db.func.strftime('%Y-%m-%d', Ubicacion.fecha) == hoy
    ).order_by(Ubicacion.fecha.asc()).all()
    
    paradas = []
    recorrido_coords = []
    
    # Lógica simple para agrupar paradas cuando velocidad es 0
    for p in puntos:
        recorrido_coords.append({"lat": p.lat, "lng": p.lng, "hora": p.fecha.strftime("%H:%M"), "vel": p.velocidad})
        if p.velocidad == 0:
            # Si el chofer está detenido, lo registramos como posible parada
            paradas.append({"lat": p.lat, "lng": p.lng, "hora": p.fecha.strftime("%H:%M")})

    return render_template_string(MAPA_DETALLADO_HTML, ch=ch, puntos=recorrido_coords, paradas=paradas)

@app.route("/api/ubicaciones")
@login_required
def api_ubs():
    data=[]
    for c in Usuario.query.filter_by(rol='chofer').all():
        u=Ubicacion.query.filter_by(chofer_id=c.id).order_by(Ubicacion.fecha.desc()).first()
        if u: data.append({'id':c.id,'nombre':c.nombre,'lat':u.lat,'lng':u.lng})
    return jsonify(data)

@app.route("/logout")
def logout(): session.clear(); return redirect("/")

LOGIN_HTML = """
<body style="margin:0;font-family:system-ui;background:#e0f7fa;display:flex;justify-content:center;align-items:center;height:100vh">
<div style="background:white;padding:35px;border-radius:20px;width:360px;text-align:center;box-shadow:0 8px 24px rgba(0,0,0,.1)">
<img src="/logo.png" style="width:180px" onerror="this.outerHTML='<div style=\\'background:#0891b2;color:white;padding:12px;border-radius:12px;font-weight:bold\\'>💧 GOTA DE MANANTIAL<br><small style=\\'font-weight:normal\\'>Mexicali</small></div>'">
<h2 style="margin:16px 0">GOTA DE MANANTIAL</h2>
{% if error %}<div style="background:#fee2e2;color:#991b1b;padding:8px;border-radius:8px;margin-bottom:8px">{{error}}</div>{% endif %}
<form method="post"><input name="username" placeholder="Usuario" required style="width:100%;padding:12px;margin:6px 0;border-radius:8px;border:1px solid #ccc"><input name="password" type="password" placeholder="Contrasena" required style="width:100%;padding:12px;margin:6px 0;border-radius:8px;border:1px solid #ccc"><button style="width:100%;padding:12px;background:#0891b2;color:white;border:none;border-radius:8px;font-weight:bold">Entrar</button></form>
</div></body>"""

ADMIN_HTML = """
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
.pedido-row{border-bottom:1px solid #eee;padding:10px 8px;font-size:13px;display:flex;justify-content:space-between;align-items:center}
.menu-btn{cursor:pointer;padding:4px 8px;border-radius:6px;font-weight:bold;font-size:18px}
.menu-btn:hover{background:#f1f5f9}
.dropdown{position:absolute;right:0;top:28px;background:white;border:1px solid #ddd;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,.15);min-width:160px;display:none;z-index:99}
.dropdown a{display:block;padding:8px 12px;text-decoration:none;color:#333;font-size:13px}
.dropdown a:hover{background:#f1f5f9}
</style>
<body style="margin:0;font-family:system-ui;background:#f1f5f9">
<div style="background:white;padding:10px 14px;display:flex;justify-content:space-between;align-items:center"><div style="display:flex;align-items:center;gap:8px"><img src="/logo.png" style="height:38px" onerror="this.outerHTML='<b>💧 GOTA MXLI</b>'"><b>{{nombre}} ({{rol}})</b></div><a href="/logout">Salir</a></div>
<div style="padding:12px;max-width:1200px;margin:auto;display:grid;grid-template-columns:1fr 360px;gap:12px">
<div>
<div style="background:white;border-radius:12px;padding:12px;margin-bottom:12px"><h3>Nuevo Pedido - Mexicali</h3><form action="/pedido/nuevo" method="post" style="display:flex;gap:6px;flex-wrap:wrap"><input name="cliente" placeholder="Cliente" required><input name="direccion" placeholder="Direccion" required><input name="cantidad" type="number" value="1" style="width:60px"><input name="precio" type="number" value="22" style="width:60px"><select name="chofer_id"><option value="auto">Sin asignar</option>{% for ch in choferes %}<option value="{{ch.id}}">{{ch.nombre}}</option>{% endfor %}</select><button>Agregar</button></form></div>
<div style="background:#fffbeb;border:2px solid #f59e0b;border-radius:12px;padding:12px;margin-bottom:12px"><h3>Solicitudes de precio</h3>{% for s in solicitudes %}<div style="background:white;border:1px solid #fbbf24;padding:8px;border-radius:8px;margin-bottom:6px;font-size:13px"><b>{{s.cantidad}}x {{s.tamano}} ${{s.precio_estaba}}->${{s.precio_quedo}} = ${{s.diferencia}}</b><br>{{dict.get(s.chofer_id,'-')}} - {{s.direccion}} - {{s.motivo}}<br><a href="/autorizar/{{s.id}}" style="background:#16a34a;color:white;padding:5px 10px;border-radius:5px;text-decoration:none">Aceptar</a> <a href="/rechazar/{{s.id}}" style="background:#dc2626;color:white;padding:5px 10px;border-radius:5px;text-decoration:none">Rechazar</a></div>{% else %}<p style="font-size:13px;color:#666">Sin solicitudes</p>{% endfor %}</div>
<div style="background:white;border-radius:12px;padding:12px"><h3>Pedidos</h3>
{% for p in pedidos %}
<div class="pedido-row"><span><b>{{p.cliente}}</b> - {{p.direccion}} - {{p.cantidad}}x ${{p.precio}} - <b>{{p.estado}}</b> - <span style="color:#0891b2">{{dict.get(p.chofer_id,'Sin asignar')}}</span></span><div style="position:relative"><div class="menu-btn" onclick="toggleMenu({{p.id}})">⋮</div><div id="menu-{{p.id}}" class="dropdown"><a href="/pedido/entregar/{{p.id}}">✅ Entregado</a><div style="border-top:1px solid #eee;padding:6px 12px;font-size:11px;color:#888">Mandar a:</div>{% for ch in choferes %}<a href="/pedido/mover/{{p.id}}?chofer_id={{ch.id}}">👤 {{ch.nombre}}</a>{% endfor %}<a href="/pedido/mover/{{p.id}}?chofer_id=0" style="color:#888">📦 Sin asignar</a></div></div></div>
{% endfor %}</div>
</div>
<div>
<div style="background:white;border-radius:12px;padding:12px;margin-bottom:12px"><h3>Mapa Mexicali</h3><div id="map" style="height:320px;border-radius:8px"></div></div>
<div style="background:white;border-radius:12px;padding:12px"><h3>Empleados</h3><form action="/usuario/nuevo" method="post" style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:8px"><input name="nombre" placeholder="Nombre" required><input name="username" placeholder="Usuario" required><input name="password" placeholder="Pass" required style="width:60px"><select name="rol"><option value="chofer">Chofer</option><option value="admin">Admin</option></select><input name="precio_agua" type="number" placeholder="$" style="width:45px"><button>Crear</button></form>{% for u in usuarios %}<div style="border-bottom:1px solid #eee;padding:5px;font-size:12px"><b>{{u.nombre}} ({{u.rol}})</b> {% if u.rol=='chofer' %} ${{u.precio_agua}} <form action="/usuario/precio/{{u.id}}" method="post" style="display:inline"><input name="precio_agua" value="{{u.precio_agua}}" style="width:35px"><button>OK</button></form>{% endif %} <a href="/usuario/reset/{{u.id}}">Reset</a> <a href="/usuario/borrar/{{u.id}}" style="color:red">Baja</a></div>{% endfor %}</div>
</div>
</div>
<script>
function toggleMenu(id){
  document.querySelectorAll('.dropdown').forEach(d=>{if(d.id!=='menu-'+id) d.style.display='none'});
  var m=document.getElementById('menu-'+id); m.style.display = m.style.display==='block' ? 'none' : 'block';
}
document.addEventListener('click', function(e){ if(!e.target.classList.contains('menu-btn')){ if(!e.target.closest('.dropdown')) document.querySelectorAll('.dropdown').forEach(d=>d.style.display='none'); }});
var map=L.map('map').setView([32.6245, -115.452],12); L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
var markers={};
function cargar(){fetch('/api/ubicaciones').then(r=>r.json()).then(d=>{d.forEach(c=>{ if(markers[c.id]) map.removeLayer(markers[c.id]); markers[c.id]=L.marker([c.lat,c.lng]).addTo(map).bindPopup(c.nombre) })})}
cargar(); setInterval(cargar,10000);
</script>
</body>"""

CHOFER_HTML = """
<div style="background:#fef9c3; border:2px solid #ca8a04; padding:8px; border-radius:8px; margin:10px 0; text-align:center;"><b>META SEMANAL:</b> <span style="font-size:16px; font-weight:bold; color:#a16207;">{{ garrafones_semana }} / 700</span></div>
<body style="margin:0;font-family:system-ui;background:#f0fdf4">
<div style="background:white;padding:10px 14px;display:flex;justify-content:space-between"><div style="display:flex;align-items:center;gap:8px"><img src="/logo.png" style="height:35px" onerror="this.outerHTML='<b>💧 MXLI</b>'"><b>{{nombre}} - ${{precio_usar}} | Corte ${{total_venta}}</b></div><a href="/logout">Salir</a></div>
<div style="padding:12px;max-width:700px;margin:auto">
<!-- BLOQUE DE DESCUENTOS REGISTRADOS -->
<div class="card" style="background: white; padding: 14px; border-radius: 12px; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
    <h3 style="margin-top: 0; color: #dc2626;">Registrar Descuento / Gasto</h3>
    <form action="/descuento/nuevo" method="post">
        <div style="display: flex; gap: 6px; margin-bottom: 6px;">
            <input type="number" name="cantidad" placeholder="Cantidad" required style="width: 35%; padding: 10px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box;">
            <input type="number" step="0.01" name="total" placeholder="Total $" required style="width: 65%; padding: 10px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box;">
            <input type="number" name="tarjetas" placeholder="Tarjetas" required style="width: 35%; padding: 10px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box;">
            <input type="numbre" step="0.01" name="cantidad" placeholder="Total $" required style="width: 65%; padding : 10px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box;">     
        </div>
        <input type="text" name="descripcion" placeholder="Descripción (ej. Gasolina, Cliente especial)" required style="width: 100%; padding: 10px; margin-bottom: 8px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box;">
        <button style="width: 100%; padding: 12px; background: #dc2626; color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer;">Agregar Descuento</button>
    </form>
</div>
<!-- SOLICITUD DE PRECIO PARA TAMBOS -->
<div class="card" style="background: white; padding: 14px; border-radius: 12px; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
    <h3 style="margin-top: 0; color: #0891b2;">Solicitar Precio Especial (Tambos)</h3>
    <form action="/solicitar_precio" method="post">
        <input type="text" name="tambo" placeholder="Tipo de Tambo (ej. Tambo 11G, Tambo 9G)" required style="width: 100%; padding: 10px; margin-bottom: 6px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box;">
        <div style="display: flex; gap: 6px; margin-bottom: 6px;">
            <input type="number" name="cantidad" placeholder="Cantidad" value="1" required style="width: 35%; padding: 10px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box;">
            <input type="number" step="0.1" name="quedo" placeholder="Precio Solicitado" required style="width: 65%; padding: 10px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box;">
        </div>
        <input type="text" name="direccion" placeholder="Dirección / Cliente" required style="width: 100%; padding: 10px; margin-bottom: 8px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box;">
        <button style="width: 100%; padding: 12px; background: #0891b2; color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer;">Solicitar Precio</button>
    </form>
</div>
</div>
<script>
let watchId;
function iniciarGps() {
    if (!navigator.geolocation) return;
    // watchPosition gasta menos batería y se queda transmitiendo en vivo
    watchId = navigator.geolocation.watchPosition(pos => {
        fetch('/chofer/update_location', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lat: pos.coords.latitude, lng: pos.coords.longitude })
        }).catch(err => console.log("Error mandando GPS"));
    }, null, { enableHighAccuracy: true, maximumAge: 0, timeout: 8000 });

    // Truco maestro: Evita que Android suspenda el rastreo al apagar la pantalla
    if ('wakeLock' in navigator) {
        navigator.wakeLock.request('screen').catch(() => {});
    }
}
iniciarGps();
// Si el chofer minimiza la app y regresa, reengancha el GPS de inmediato
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') iniciarGps(); });
</script>

</body>"""

if __name__=="__main__":
    with app.app_context():
        db.create_all()
        # Si existe, lo borra y recrea con clave limpia
        u = Usuario.query.filter_by(username='sistemas').first()
        if not u:
            print(">>> Creando usuario sistemas / admin123")
            u = Usuario(username='sistemas', password=generate_password_hash("admin123"), rol='sistemas', nombre='Sistemas', precio_agua=22)
            db.session.add(u)
            db.session.commit()
        else:
            # Si no te deja entrar, forza reset al iniciar
            u.password = generate_password_hash("admin123")
            db.session.commit()
            print(">>> Password de sistemas reseteado a admin123")

    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)), debug=False)
