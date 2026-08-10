from flask import Flask, request, redirect, session, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'gota-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gota.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16*1024*1024
db = SQLAlchemy(app)
os.makedirs('uploads', exist_ok=True)
os.makedirs('static', exist_ok=True)

# --- MODELOS ---
class Usuario(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    nombre=db.Column(db.String(80))
    username=db.Column(db.String(80),unique=True)
    password=db.Column(db.String(80))
    rol=db.Column(db.String(20))

class Chofer(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    usuario_id=db.Column(db.Integer,db.ForeignKey('usuario.id'))
    usuario=db.relationship('Usuario')

class Pedido(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    cliente=db.Column(db.String(120))
    telefono=db.Column(db.String(30))
    direccion=db.Column(db.String(200))
    precio_tambo=db.Column(db.Float,default=40)
    chofer_id=db.Column(db.Integer,db.ForeignKey('chofer.id'),nullable=True)
    estatus=db.Column(db.String(20),default='pendiente')
    foto_evidencia=db.Column(db.String(200),nullable=True)
    motivo_no_salio=db.Column(db.String(200),nullable=True)
    fecha_evento=db.Column(db.DateTime,default=datetime.now)

class ChoferUbicacion(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    chofer_id=db.Column(db.Integer,db.ForeignKey('chofer.id'))
    lat=db.Column(db.Float)
    lng=db.Column(db.Float)
    fecha=db.Column(db.DateTime,default=datetime.now)
    chofer=db.relationship('Chofer')

def get_logo():
    if os.path.exists("static/logo_login.png"): return "/static/logo_login.png"
    if os.path.exists("static/logo.png"): return "/static/logo.png"
    return ""

def page(cont, rol='admin'):
    logo=get_logo()
    menu=""
    if rol in ['admin','superadmin']:
        menu="<a href='/admin/choferes' class='btn btn-sm btn-outline-light me-1'>Choferes</a><a href='/admin/pedidos' class='btn btn-sm btn-outline-light me-1'>Pedidos</a><a href='/admin/corte' class='btn btn-sm btn-warning me-1'>Corte</a><a href='/admin/evidencias' class='btn btn-sm btn-danger me-1'>Plantados</a><a href='/mapa' class='btn btn-sm btn-info me-1'>Mapa</a>"
    secreto=""
    if rol=='superadmin':
        secreto='<div class="dropdown d-inline"><button class="btn btn-sm btn-light ms-2" type="button" data-bs-toggle="dropdown">⋮</button><ul class="dropdown-menu dropdown-menu-dark"><li><a class="dropdown-item" href="/admin/usuarios">Usuarios</a></li><li><a class="dropdown-item" href="/admin/db_backup">Respaldar DB</a></li></ul></div>'
    return "<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'><link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'><script src='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js'></script></head><body class='bg-light'><nav class='navbar navbar-dark bg-dark p-2'><div class='container-fluid'><span class='navbar-brand'>GOTA <small style='font-size:10px'>"+rol+"</small></span><div>"+menu+secreto+"<a href='/logout' class='btn btn-sm btn-danger ms-2'>Salir</a></div></div></nav><div class='container mt-3'>"+cont+"</div></body></html>"

def page_chofer(cont):
    return "<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'><link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'></head><body class='bg-light'><nav class='navbar navbar-dark bg-primary p-2 d-flex justify-content-between'><span class='navbar-brand'>Panel Chofer</span><div><a href='/chofer/corte' class='btn btn-sm btn-warning me-2'>Mi Corte</a><a href='/logout' class='btn btn-sm btn-light'>Salir</a></div></nav><div class='container mt-3'>"+cont+"</div></body></html>"

@app.route('/uploads/<f>')
def uploaded_file(f): return send_from_directory(app.config['UPLOAD_FOLDER'], f)

@app.route('/')
def index():
    return redirect('/login')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=Usuario.query.filter_by(username=request.form['username'], password=request.form['password']).first()
        if u:
            session['uid']=u.id; session['rol']=u.rol
            return redirect('/admin/pedidos' if u.rol in ['admin','superadmin'] else '/chofer/panel')
    logo=get_logo()
    cont=f"<div class='row justify-content-center'><div class='col-11 col-md-4 card p-4 shadow mt-5 text-center'><img src='{logo}' style='height:90px;object-fit:contain'><h5 style='color:#0a7a5c;font-weight:900'>GOTA DE MANANTIAL</h5><form method='post'><input name='username' class='form-control mb-2' placeholder='Usuario' required><input name='password' type='password' class='form-control mb-2' placeholder='Pass' required><button class='btn btn-primary w-100'>Entrar</button></form><div class='mt-2 text-start' style='font-size:11px'>sistemas / sistemas123<br>admin / admin123<br>chofer1 / 123</div></div></div>"
    return page(cont, rol='login')

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

# ... (todo lo demas igual) ...

@app.route('/admin/pedidos')
def admin_pedidos():
    if session.get('rol') not in ['admin','superadmin']: return redirect('/login')
    pedidos=Pedido.query.order_by(Pedido.id.desc()).all()
    opts="".join([f"<option value='{c.id}'>{c.usuario.nombre}</option>" for c in Chofer.query.all() if c.usuario]) or "<option>Sin choferes</option>"
    rows=""
    for p in pedidos:
        ch="Sin asignar"; col="secondary"
        if p.chofer_id:
            co=Chofer.query.get(p.chofer_id)
            if co and co.usuario:
                ch=co.usuario.nombre
                if p.estatus=='entregado': col='success'
                elif p.estatus=='no_salio': col='danger'
                elif p.estatus=='asignado': col='warning'
                ch+=f" <span class='badge bg-{col}'>{p.estatus}</span>"
        rows+=f"<tr><td>{p.id}</td><td>{p.cliente}</td><td>{p.direccion}</td><td>${p.precio_tambo}</td><td>{ch}</td><td><form method='post' action='/admin/pedidos/asignar/{p.id}' class='d-flex'><select name='chofer_id' class='form-select form-select-sm me-1'>{opts}</select><button class='btn btn-sm btn-success'>Ok</button></form></td></tr>"
    return page(f"<h3>Pedidos</h3><form action='/admin/pedidos/nuevo' method='post' class='row g-2 mb-3'><div class='col-3'><input name='cliente' class='form-control' placeholder='Cliente' required></div><div class='col-2'><input name='telefono' class='form-control' placeholder='Tel'></div><div class='col-4'><input name='direccion' class='form-control' placeholder='Direccion' required></div><div class='col-1'><input name='precio' type='number' class='form-control' value='40'></div><div class='col-2'><button class='btn btn-success w-100'>Crear</button></div></form><table class='table table-sm bg-white'><tr><th>ID</th><th>Cliente</th><th>Dir</th><th>$</th><th>Estado</th><th></th></tr>{rows}</table>", rol=session.get('rol'))

@app.route('/admin/pedidos/nuevo',methods=['POST'])
def nuevo_pedido():
    p=Pedido(cliente=request.form['cliente'], telefono=request.form.get('telefono'), direccion=request.form['direccion'], precio_tambo=float(request.form.get('precio',40))); db.session.add(p); db.session.commit(); return redirect('/admin/pedidos')

@app.route('/admin/pedidos/asignar/<int:id>',methods=['POST'])
def asignar(id):
    p=Pedido.query.get(id); p.chofer_id=int(request.form['chofer_id']); p.estatus='asignado'; db.session.commit(); return redirect('/admin/pedidos')

@app.route('/admin/choferes')
def admin_choferes():
    if session.get('rol') not in ['admin','superadmin']: return redirect('/login')
    rows="".join([f"<tr><td>{c.usuario.nombre}</td><td>{c.usuario.username}</td><td>{c.usuario.rol}</td></tr>" for c in Chofer.query.all() if c.usuario])
    return page(f"<h3>Choferes</h3><form action='/admin/choferes/nuevo' method='post' class='row g-2 mb-2'><div class='col-3'><input name='nombre' class='form-control' placeholder='Nombre' required></div><div class='col-2'><input name='username' class='form-control' placeholder='User' required></div><div class='col-2'><input name='password' class='form-control' placeholder='Pass' required></div><div class='col-2'><select name='rol' class='form-select'><option value='chofer'>Chofer</option><option value='admin'>Admin</option></select></div><div class='col-3'><button class='btn btn-success w-100'>Crear</button></div></form><table class='table bg-white'><tr><th>Nombre</th><th>User</th><th>Rol</th></tr>{rows}</table>", rol=session.get('rol'))

@app.route('/admin/choferes/nuevo',methods=['POST'])
def chofer_nuevo():
    u=Usuario(nombre=request.form['nombre'], username=request.form['username'], password=request.form['password'], rol=request.form.get('rol','chofer')); db.session.add(u); db.session.commit()
    if request.form.get('rol')=='chofer': db.session.add(Chofer(usuario_id=u.id)); db.session.commit()
    return redirect('/admin/choferes')

@app.route('/mapa')
def mapa():
    if session.get('rol') not in ['admin','superadmin']: return redirect('/login')
    return page("""
    <h3>Ubicacion Choferes en Tiempo Real</h3>
    <div id='map' style='height:400px' class='bg-white border'></div>
    <script>
    async function cargar(){
      let r=await fetch('/api/ubicaciones'); let d=await r.json();
      let h=''; for(let k in d){ h+=`<div>${d[k].nombre}: ${d[k].lat}, ${d[k].lng} - ${d[k].fecha}</div>`; }
      document.getElementById('map').innerHTML=h||'Sin ubicaciones aun';
    }
    setInterval(cargar,5000); cargar();
    </script>
    """, rol=session.get('rol'))

@app.route('/api/ubicacion_chofer', methods=['POST'])
def api_ubicacion_chofer():
    data=request.get_json()
    if data and data.get('chofer_id') and data.get('lat'):
        ub=ChoferUbicacion(chofer_id=data['chofer_id'], lat=data['lat'], lng=data['lng'])
        db.session.add(ub); db.session.commit()
        return jsonify({"ok":True})
    return jsonify({"ok":False}),400

@app.route('/api/ubicaciones')
def api_ubicaciones():
    ultimas={}
    for c in Chofer.query.all():
        u=ChoferUbicacion.query.filter_by(chofer_id=c.id).order_by(ChoferUbicacion.id.desc()).first()
        if u and c.usuario:
            ultimas[c.id]={"nombre":c.usuario.nombre,"lat":u.lat,"lng":u.lng,"fecha":u.fecha.strftime("%H:%M:%S")}
    return jsonify(ultimas)

with app.app_context():
    db.create_all()
    if not Usuario.query.filter_by(username='sistemas').first(): db.session.add(Usuario(nombre='Sistemas', username='sistemas', password='sistemas123', rol='superadmin')); db.session.commit()
    if not Usuario.query.filter_by(username='admin').first(): db.session.add(Usuario(nombre='Admin', username='admin', password='admin123', rol='admin')); db.session.commit()
    if not Usuario.query.filter_by(username='chofer1').first():
        u=Usuario(nombre='Chofer1', username='chofer1', password='123', rol='chofer'); db.session.add(u); db.session.commit(); db.session.add(Chofer(usuario_id=u.id)); db.session.commit()

if __name__=='__main__': app.run(host='0.0.0.0',port=5000)