from flask import Flask, request, redirect, session, render_template_string, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import os
app = Flask(__name__)
app.secret_key = "gota-v10-mxli"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gota.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Usuario(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    username=db.Column(db.String(80), unique=True)
    password=db.Column(db.String(200))
    rol=db.Column(db.String(20))
    nombre=db.Column(db.String(100))
    precio_agua=db.Column(db.Float, default=22)
class Pedido(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    cliente=db.Column(db.String(100)); direccion=db.Column(db.String(200))
    cantidad=db.Column(db.Integer); precio=db.Column(db.Float, default=22)
    estado=db.Column(db.String(20), default="Pendiente")
    chofer_id=db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    fecha=db.Column(db.DateTime, default=datetime.now)
class Ubicacion(db.Model):
    id=db.Column(db.Integer, primary_key=True); chofer_id=db.Column(db.Integer, db.ForeignKey('usuario.id'))
    lat=db.Column(db.Float); lng=db.Column(db.Float); fecha=db.Column(db.DateTime, default=datetime.now)
class Corte(db.Model):
    id=db.Column(db.Integer, primary_key=True); chofer_id=db.Column(db.Integer, db.ForeignKey('usuario.id'))
    fecha=db.Column(db.Date, default=date.today); salio=db.Column(db.Integer, default=0); regreso=db.Column(db.Integer, default=0)
class Descuento(db.Model):
    id=db.Column(db.Integer, primary_key=True); chofer_id=db.Column(db.Integer, db.ForeignKey('usuario.id'))
    fecha=db.Column(db.Date, default=date.today); tipo=db.Column(db.String(20)); cantidad=db.Column(db.Integer, default=1); tamano=db.Column(db.String(200)); total=db.Column(db.Float, default=0)
class Solicitud(db.Model):
    id=db.Column(db.Integer, primary_key=True); chofer_id=db.Column(db.Integer, db.ForeignKey('usuario.id'))
    fecha=db.Column(db.DateTime, default=datetime.now); tamano=db.Column(db.String(50)); cantidad=db.Column(db.Integer, default=1)
    precio_estaba=db.Column(db.Float); precio_quedo=db.Column(db.Float); diferencia=db.Column(db.Float)
    direccion=db.Column(db.String(200)); motivo=db.Column(db.String(200)); estado=db.Column(db.String(20), default="Pendiente")

@app.route("/logo.png")
def logo_file():
    return send_from_directory(".", "logo.png") if os.path.exists("logo.png") else ("",404)

@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        u=Usuario.query.filter_by(username=request.form['username']).first()
        if u and check_password_hash(u.password, request.form['password']):
            session['user_id']=u.id; session['rol']=u.rol; session['nombre']=u.nombre; return redirect("/panel")
        return render_template_string(LOGIN_HTML, error="Usuario o contrasena mal")
    return render_template_string(LOGIN_HTML, error=None)

@app.route("/panel")
def panel():
    if 'user_id' not in session: return redirect("/")
    pedidos=Pedido.query.order_by(Pedido.fecha.desc()).all()
    choferes=Usuario.query.filter_by(rol='chofer').all()
    dict_choferes={c.id:c.nombre for c in Usuario.query.all()}
    if session['rol']=='chofer':
        mis=[p for p in pedidos if p.chofer_id==session['user_id']]
        hoy=date.today()
        corte=Corte.query.filter_by(chofer_id=session['user_id'], fecha=hoy).first()
        if not corte: corte=Corte(chofer_id=session['user_id'], fecha=hoy); db.session.add(corte); db.session.commit()
        descuentos=Descuento.query.filter_by(chofer_id=session['user_id'], fecha=hoy).all()
        total_desc=sum(d.total for d in descuentos); vendidos=corte.salio-corte.regreso
        yo=Usuario.query.get(session['user_id']); precio_usar=yo.precio_agua if yo and yo.precio_agua else 22
        total_venta=vendidos*precio_usar - total_desc
        return render_template_string(CHOFER_HTML, pedidos=mis, nombre=session['nombre'], corte=corte, descuentos=descuentos, total_desc=total_desc, total_venta=total_venta, vendidos=vendidos, precio_usar=precio_usar)
    usuarios=Usuario.query.filter(Usuario.username!='sistemas').all() if session['rol']!='sistemas' else Usuario.query.all()
    solicitudes_pend=Solicitud.query.filter_by(estado="Pendiente").order_by(Solicitud.fecha.desc()).all()
    return render_template_string(ADMIN_HTML, pedidos=pedidos, choferes=choferes, dict=dict_choferes, usuarios=usuarios, rol=session['rol'], nombre=session['nombre'], solicitudes=solicitudes_pend)

@app.route("/pedido/nuevo", methods=["POST"])
def nuevo_pedido():
    cid=request.form.get('chofer_id'); 
    if cid=="auto" or not cid: cid=None
    else:
        try: cid=int(cid)
        except: cid=None
        if cid==0: cid=None
    p=Pedido(cliente=request.form['cliente'], direccion=request.form['direccion'], cantidad=int(request.form['cantidad']), precio=float(request.form.get('precio',22)), chofer_id=cid)
    db.session.add(p); db.session.commit(); return redirect("/panel")
@app.route("/pedido/mover/<int:id>")
def mover(id):
    p=Pedido.query.get(id); nc=request.args.get('chofer_id')
    if p and nc is not None:
        try:
            nc=int(nc)
            if nc==0: p.chofer_id=None
            else: p.chofer_id=nc
            db.session.commit()
        except: pass
    return redirect("/panel")
@app.route("/pedido/entregar/<int:id>")
def entregar(id):
    p=Pedido.query.get(id)
    if p: p.estado="Entregado"; db.session.commit()
    return redirect("/panel")
@app.route("/corte/update", methods=["POST"])
def corte_up():
    hoy=date.today(); c=Corte.query.filter_by(chofer_id=session['user_id'], fecha=hoy).first()
    if not c: c=Corte(chofer_id=session['user_id'], fecha=hoy); db.session.add(c)
    c.salio=int(request.form.get('salio',0)); c.regreso=int(request.form.get('regreso',0)); db.session.commit(); return redirect("/panel")
@app.route("/descuento/add", methods=["POST"])
def desc_add():
    d=Descuento(chofer_id=session['user_id'], fecha=date.today(), tipo=request.form['tipo'], cantidad=int(request.form.get('cantidad',1)), tamano=request.form.get('tamano',''), total=float(request.form.get('total',0)))
    db.session.add(d); db.session.commit(); return redirect("/panel")
@app.route("/descuento/borrar/<int:id>")
def desc_del(id):
    d=Descuento.query.get(id)
    if d: db.session.delete(d); db.session.commit()
    return redirect("/panel")
@app.route("/solicitar_precio", methods=["POST"])
def solicitar_precio():
    estaba=float(request.form.get('estaba',0) or 0); quedo=float(request.form.get('quedo',0) or 0); cant=int(request.form.get('cantidad',1) or 1)
    dif=(estaba-quedo)*cant
    s=Solicitud(chofer_id=session['user_id'], tamano=request.form.get('tamano'), cantidad=cant, precio_estaba=estaba, precio_quedo=quedo, diferencia=dif, direccion=request.form.get('direccion'), motivo=request.form.get('motivo'))
    db.session.add(s); db.session.commit(); return redirect("/panel")
@app.route("/autorizar/<int:id>")
def autorizar(id):
    s=Solicitud.query.get(id)
    if s and s.estado=="Pendiente":
        s.estado="Autorizado"; d=Descuento(chofer_id=s.chofer_id, fecha=date.today(), tipo="descuento_precio", cantidad=s.cantidad, tamano=f"{s.tamano} ${s.precio_estaba}->{s.precio_quedo} {s.direccion}", total=s.diferencia)
        db.session.add(d); db.session.commit()
    return redirect("/panel")
@app.route("/rechazar/<int:id>")
def rechazar(id):
    s=Solicitud.query.get(id)
    if s: s.estado="Rechazado"; db.session.commit()
    return redirect("/panel")
@app.route("/usuario/nuevo", methods=["POST"])
def nuevo_usuario():
    u=Usuario(username=request.form['username'], password=generate_password_hash(request.form['password']), rol=request.form['rol'], nombre=request.form['nombre'], precio_agua=float(request.form.get('precio_agua',22)))
    db.session.add(u); db.session.commit(); return redirect("/panel")
@app.route("/usuario/borrar/<int:id>")
def borrar(id):
    u=Usuario.query.get(id)
    if u and u.username!='sistemas': db.session.delete(u); db.session.commit()
    return redirect("/panel")
@app.route("/usuario/reset/<int:id>")
def reset(id):
    u=Usuario.query.get(id); u.password=generate_password_hash('123456'); db.session.commit(); return redirect("/panel")
@app.route("/usuario/precio/<int:id>", methods=["POST"])
def cambiar_precio(id):
    u=Usuario.query.get(id)
    if u: u.precio_agua=float(request.form.get('precio_agua',22)); db.session.commit()
    return redirect("/panel")
@app.route("/chofer/update_location", methods=["POST"])
def up_loc():
    d=request.json or {}; db.session.add(Ubicacion(chofer_id=session['user_id'], lat=d.get('lat'), lng=d.get('lng'))); db.session.commit(); return jsonify(ok=True)
@app.route("/api/ubicaciones")
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
<div style="background:white;border-radius:12px;padding:12px"><h3>Empleados</h3><form action="/usuario/nuevo" method="post" style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:8px"><input name="nombre" placeholder="Nombre" required><input name="username" placeholder="Usuario" required><input name="password" placeholder="Pass" required style="width:60px"><select name="rol"><option value="chofer">Chofer</option><option value="admin">Admin</option></select><input name="precio_agua" type="number" value="22" style="width:45px"><button>Crear</button></form>{% for u in usuarios %}<div style="border-bottom:1px solid #eee;padding:5px;font-size:12px"><b>{{u.nombre}} ({{u.rol}})</b> {% if u.rol=='chofer' %} ${{u.precio_agua}} <form action="/usuario/precio/{{u.id}}" method="post" style="display:inline"><input name="precio_agua" value="{{u.precio_agua}}" style="width:35px"><button>OK</button></form>{% endif %} <a href="/usuario/reset/{{u.id}}">Reset</a> <a href="/usuario/borrar/{{u.id}}" style="color:red">Baja</a></div>{% endfor %}</div>
</div>
</div>
<script>
function toggleMenu(id){
  document.querySelectorAll('.dropdown').forEach(d=>{if(d.id!=='menu-'+id) d.style.display='none'});
  var m=document.getElementById('menu-'+id); m.style.display = m.style.display==='block' ? 'none' : 'block';
}
document.addEventListener('click', function(e){ if(!e.target.classList.contains('menu-btn')){ if(!e.target.closest('.dropdown')) document.querySelectorAll('.dropdown').forEach(d=>d.style.display='none'); }});
var map=L.map('map').setView([32.6245, -115.452],12); L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
function cargar(){fetch('/api/ubicaciones').then(r=>r.json()).then(d=>{d.forEach(c=>{L.marker([c.lat,c.lng]).addTo(map).bindPopup(c.nombre)})})}
cargar(); setInterval(cargar,10000);
</script>
</body>"""

CHOFER_HTML = """
<body style="margin:0;font-family:system-ui;background:#f0fdf4">
<div style="background:white;padding:10px 14px;display:flex;justify-content:space-between"><div style="display:flex;align-items:center;gap:8px"><img src="/logo.png" style="height:35px" onerror="this.outerHTML='<b>💧 MXLI</b>'"><b>{{nombre}} - ${{precio_usar}} | Corte ${{total_venta}}</b></div><a href="/logout">Salir</a></div>
<div style="padding:12px;max-width:700px;margin:auto">
<div style="background:white;padding:12px;border-radius:12px;margin-bottom:12px"><h3>Mi Corte Hoy - Vendidos {{vendidos}}</h3><form action="/corte/update" method="post" style="display:flex;gap:6px">Salio <input name="salio" value="{{corte.salio}}" type="number" style="width:60px"> Regreso <input name="regreso" value="{{corte.regreso}}" type="number" style="width:60px"><button>Guardar</button></form><p>Vendidos {{vendidos}} x ${{precio_usar}} - Desc ${{total_desc}} = <b>${{total_venta}}</b></p><form action="/descuento/add" method="post" style="display:flex;gap:4px;flex-wrap:wrap;margin-top:8px"><select name="tipo"><option value="tambo">Tambo</option><option value="botella">Botella</option></select><input name="cantidad" type="number" value="1" style="width:40px"><input name="tamano" placeholder="Motivo" style="padding:4px"><input name="total" type="number" placeholder="$" style="width:50px"><button>Descuento</button></form>{% for d in descuentos %}<div style="font-size:12px;border-bottom:1px solid #eee">{{d.cantidad}}x {{d.tamano}} - ${{d.total}} <a href="/descuento/borrar/{{d.id}}" style="color:red">x</a></div>{% endfor %}</div>
<div style="background:white;padding:12px;border-radius:12px;margin-bottom:12px"><h3>Solicitar precio especial</h3><form action="/solicitar_precio" method="post" style="display:flex;gap:5px;flex-wrap:wrap"><input name="tamano" placeholder="20L" required style="width:60px"><input name="cantidad" type="number" value="1" style="width:40px"><input name="estaba" type="number" placeholder="Estaba" required style="width:60px"><input name="quedo" type="number" placeholder="Quedo" required style="width:60px"><input name="direccion" placeholder="Direccion" required><input name="motivo" placeholder="Motivo"><button style="background:#f59e0b;color:white;border:none;padding:6px 10px;border-radius:6px">Solicitar</button></form></div>
<div style="background:white;padding:12px;border-radius:12px"><h3>Mis pedidos</h3>{% for p in pedidos %}<div style="border-bottom:1px solid #eee;padding:8px;font-size:13px;display:flex;justify-content:space-between"><span>{{p.cliente}} - {{p.direccion}} - {{p.cantidad}}x ${{p.precio}} - {{p.estado}}</span><a href="/pedido/entregar/{{p.id}}" style="background:#16a34a;color:white;padding:4px 8px;border-radius:4px;text-decoration:none">Entregar</a></div>{% endfor %}</div>
</div>
<script>if(navigator.geolocation){setInterval(()=>{navigator.geolocation.getCurrentPosition(pos=>{fetch('/chofer/update_location',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lat:pos.coords.latitude,lng:pos.coords.longitude})})})},15000)}</script>
</body>"""

if __name__=="__main__":
    with app.app_context():
        db.create_all()
        if not Usuario.query.filter_by(username='sistemas').first():
            u=Usuario(username='sistemas', password=generate_password_hash('admin123'), rol='sistemas', nombre='Sistemas', precio_agua=22)
            db.session.add(u); db.session.commit()
    app.run(host='0.0.0.0', port=10000, debug=True)
