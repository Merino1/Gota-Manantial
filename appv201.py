from flask import Flask, request, redirect, session, render_template_string, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import sqlite3, os

app = Flask(__name__)
app.secret_key = 'gota-manantial-2026'

# ============ USUARIOS CON HASH BUENO DE 1234 ============
def h(p): return generate_password_hash(p)
usuarios = {
    'karina': {'pass': h('1234'), 'rol': 'admin', 'nombre': 'Karina'},
    'lupita': {'pass': h('1234'), 'rol': 'secre', 'nombre': 'Lupita'},
    'alfonso': {'pass': h('1234'), 'rol': 'chofer', 'nombre': 'Alfonso'},
    'armando': {'pass': h('1234'), 'rol': 'chofer', 'nombre': 'Armando'},
    'juan': {'pass': h('1234'), 'rol': 'chofer', 'nombre': 'Juan'},
    'juan_mecanico': {'pass': h('1234'), 'rol': 'mecanico', 'nombre': 'Juan Mecanico'},
    'victor': {'pass': h('1234'), 'rol': 'sistemas', 'nombre': 'Victor'},
    'chucho': {'pass': h('1234'), 'rol': 'chofer', 'nombre': 'Chucho el Roto'},
}

DB='gota.db'
def db():
    con=sqlite3.connect(DB)
    con.row_factory=sqlite3.Row
    return con

def init():
    con=db()
    con.execute('''CREATE TABLE IF NOT EXISTS pedidos (id INTEGER PRIMARY KEY, cliente TEXT, direccion TEXT, cantidad INTEGER, fecha TEXT, chofer TEXT, estado TEXT, precio REAL)''')
    con.execute('''CREATE TABLE IF NOT EXISTS ubicaciones (id INTEGER PRIMARY KEY, chofer TEXT, lat REAL, lon REAL, fecha TEXT)''')
    con.execute('''CREATE TABLE IF NOT EXISTS taller (id INTEGER PRIMARY KEY, chofer TEXT, falla TEXT, fecha TEXT, estado TEXT)''')
    con.commit(); con.close()
init()

LOGIN = """
<meta name="viewport" content="width=device-width,initial-scale=1">
<body style="font-family:system-ui;background:#e0f7fa;display:flex;justify-content:center;align-items:center;height:100vh;margin:0">
<div style="background:white;padding:30px;border-radius:20px;width:350px;text-align:center">
<h2>💧 GOTA DE MANANTIAL</h2>
{% if e %}<div style="background:#fecaca;padding:8px;border-radius:8px;margin:8px 0">{{e}}</div>{% endif %}
<form method="post">
<input name="u" placeholder="Usuario" required style="width:100%;padding:12px;margin:6px 0;border-radius:8px;border:1px solid #ccc">
<input name="p" type="password" placeholder="Contraseña" required style="width:100%;padding:12px;margin:6px 0;border-radius:8px;border:1px solid #ccc">
<button style="width:100%;padding:12px;background:#0891b2;color:white;border:none;border-radius:8px;font-weight:bold">ENTRAR</button>
</form>
<small>karina/alfonso/lupita/juan_mecanico/victor/chucho -> 1234</small>
</div></body>
"""

@app.route('/', methods=['GET','POST'])
@app.route('/login', methods=['GET','POST'])
def login():
    e=None
    if request.method=='POST':
        u=request.form.get('u','').strip().lower()
        p=request.form.get('p','').strip()
        if u in usuarios and check_password_hash(usuarios[u]['pass'], p):
            session['u']=u; session['nombre']=usuarios[u]['nombre']; session['rol']=usuarios[u]['rol']
            r=usuarios[u]['rol']
            if r=='admin': return redirect('/admin')
            if r=='secre': return redirect('/secre')
            if r=='chofer': return redirect('/chofer')
            if r=='mecanico': return redirect('/mecanico')
            if r=='sistemas': return redirect('/sistemas')
        else:
            e="Usuario o contraseña incorrectos"
    return render_template_string(LOGIN, e=e)

@app.route('/logout')
def logout():
    session.clear(); return redirect('/login')

# ============ ADMIN ============
@app.route('/admin')
def admin():
    if session.get('rol')!='admin': return redirect('/login')
    con=db(); peds=con.execute("SELECT * FROM pedidos ORDER BY id DESC LIMIT 50").fetchall()
    ubis=con.execute("SELECT * FROM ubicaciones ORDER BY id DESC LIMIT 50").fetchall()
    con.close()
    return render_template_string("""
    <h2>Admin - {{n}}</h2>
    <a href='/secre'>Panel Secre</a> | <a href='/historial'>Historial REAL</a> | <a href='/logout'>Salir</a>
    <hr><h3>Crear Pedido</h3>
    <form action='/crear_pedido' method='post'>
    Cliente: <input name='cliente' required> Direccion: <input name='direccion' required>
    Cant: <input name='cantidad' type='number' value='1'> Chofer: <select name='chofer'>
    <option>alfonso</option><option>armando</option><option>juan</option><option>chucho</option></select>
    <button>Crear</button></form>
    <hr><h3>Pedidos ({{peds|length}})</h3>
    {% for pe in peds %}<div>#{{pe['id']}} {{pe['cliente']}} - {{pe['chofer']}} - {{pe['estado']}} - ${{pe['precio']}}</div>{% endfor %}
    <hr><h3>Mapa (ultimas {{ubis|length}} ubicaciones)</h3>
    {% for u in ubis %}<div>{{u['chofer']}} {{u['lat']}},{{u['lon']}} {{u['fecha']}}</div>{% endfor %}
    """, n=session['nombre'], peds=peds, ubis=ubis)

# ============ SECRE ============
@app.route('/secre')
def secre():
    if session.get('rol') not in ('admin','secre'): return redirect('/login')
    con=db(); peds=con.execute("SELECT * FROM pedidos WHERE estado='pendiente' ORDER BY id DESC").fetchall(); con.close()
    return render_template_string("""
    <h2>Secre - {{n}}</h2><a href='/historial'>Historial</a> | <a href='/logout'>Salir</a>
    <form action='/crear_pedido' method='post'>
    Cliente: <input name='cliente' required> Dir: <input name='direccion' required> Cant: <input name='cantidad' type='number' value='1'>
    Chofer: <select name='chofer'><option>alfonso</option><option>armando</option><option>juan</option><option>chucho</option></select><button>Crear</button></form>
    <hr>{% for pe in peds %}<div>{{pe['cliente']}} -> {{pe['chofer']}} <a href='/entregar/{{pe['id']}}'>Entregar</a></div>{% endfor %}
    <script>setInterval(()=>{navigator.geolocation.getCurrentPosition(p=>fetch('/ubicacion?lat='+p.coords.latitude+'&lon='+p.coords.longitude))},10000)</script>
    """, n=session['nombre'], peds=peds)

# ============ CHOFER ============
@app.route('/chofer')
def chofer():
    if session.get('rol') not in ('chofer','admin','secre'): return redirect('/login')
    cho=session['u'] if session['rol']=='chofer' else request.args.get('ver','alfonso')
    con=db(); peds=con.execute("SELECT * FROM pedidos WHERE chofer=? AND estado='pendiente'", (cho,)).fetchall()
    hoy=con.execute("SELECT COUNT(*) as c, SUM(cantidad) as s FROM pedidos WHERE chofer=? AND date(fecha)=date('now')", (cho,)).fetchone()
    con.close()
    return render_template_string("""
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <h2>🚚 {{n}} - Chofer</h2>
    <div>Viajes hoy: {{hoy['c'] or 0}} | Garrafones: {{hoy['s'] or 0}}</div>
    <hr>{% for pe in peds %}<div style="border:1px solid #ccc;padding:10px;border-radius:10px;margin:6px 0">
    <b>{{pe['cliente']}}</b><br>{{pe['direccion']}}<br>{{pe['cantidad']}} garrafones<br>
    <a href='/entregar/{{pe['id']}}' style="background:#0891b2;color:white;padding:8px 12px;border-radius:8px;text-decoration:none">ENTREGADO</a>
    </div>{% else %}<p>Sin pedidos we</p>{% endfor %}
    <a href='/historial?chofer={{cho}}'>Mi historial</a> | <a href='/logout'>Salir</a>
    <script>
    function manda(){navigator.geolocation.getCurrentPosition(p=>{fetch('/ubicacion?lat='+p.coords.latitude+'&lon='+p.coords.longitude);},null,{enableHighAccuracy:true})}
    manda(); setInterval(manda,15000);
    </script>
    """, n=session['nombre'], peds=peds, hoy=hoy, cho=cho)

# ============ MECANICO ============
@app.route('/mecanico')
def mecanico():
    if session.get('rol') not in ('mecanico','admin','sistemas'): return redirect('/login')
    con=db(); fallas=con.execute("SELECT * FROM taller ORDER BY id DESC").fetchall(); con.close()
    return render_template_string("""
    <h2>🔧 Taller - {{n}}</h2>
    <form action='/reporte_falla' method='post'><input name='falla' placeholder='Falla del camion' required><button>Reportar</button></form>
    <hr>{% for f in fallas %}<div>{{f['chofer']}}: {{f['falla']}} - {{f['estado']}}</div>{% endfor %}
    <a href='/logout'>Salir</a>
    """, n=session['nombre'], fallas=fallas)

# ============ SISTEMAS / META ============
@app.route('/sistemas')
def sistemas():
    if session.get('rol') not in ('sistemas','admin'): return redirect('/login')
    con=db()
    total=con.execute("SELECT COUNT(*) as t FROM pedidos").fetchone()['t']
    pend=con.execute("SELECT COUNT(*) as t FROM pedidos WHERE estado='pendiente'").fetchone()['t']
    con.close()
    return f"<h2>💻 Sistemas - {session['nombre']}</h2><p>Total pedidos: {total}</p><p>Pendientes: {pend}</p><a href='/admin'>Admin</a> | <a href='/historial'>Historial completo</a> | <a href='/logout'>Salir</a>"

@app.route('/crear_pedido', methods=['POST'])
def crear_pedido():
    if session.get('rol') not in ('admin','secre'): return redirect('/login')
    c=request.form
    con=db(); con.execute("INSERT INTO pedidos (cliente,direccion,cantidad,chofer,fecha,estado,precio) VALUES (?,?,?,?,?,?,?)",
    (c['cliente'], c['direccion'], int(c['cantidad']), c['chofer'], datetime.now().isoformat(), 'pendiente', int(c['cantidad'])*40))
    con.commit(); con.close()
    return redirect(request.referrer or '/admin')

@app.route('/entregar/<int:id>')
def entregar(id):
    con=db(); con.execute("UPDATE pedidos SET estado='entregado' WHERE id=?", (id,)); con.commit(); con.close()
    return redirect(request.referrer or '/chofer')

@app.route('/ubicacion')
def ubicacion():
    if 'u' not in session: return "no login"
    lat=request.args.get('lat'); lon=request.args.get('lon')
    if lat and lon:
        con=db(); con.execute("INSERT INTO ubicaciones (chofer,lat,lon,fecha) VALUES (?,?,?,?)",(session['u'], float(lat), float(lon), datetime.now().isoformat()))
        con.commit(); con.close(); return "ok"
    return "fail"

@app.route('/historial')
def historial():
    if 'u' not in session: return redirect('/login')
    chofer=request.args.get('chofer')
    con=db()
    if chofer:
        rows=con.execute("SELECT * FROM pedidos WHERE chofer=? ORDER BY id DESC LIMIT 200", (chofer,)).fetchall()
    else:
        rows=con.execute("SELECT * FROM pedidos ORDER BY id DESC LIMIT 200").fetchall()
    con.close()
    html=f"<h2>Historial ({len(rows)})</h2><a href='/admin'>Admin</a> | <a href='/chofer'>Chofer</a> | <a href='/logout'>Salir</a><hr>"
    for r in rows:
        html+=f"<div>#{r['id']} {r['fecha'][:16]} | {r['cliente']} | {r['direccion']} | {r['chofer']} | {r['estado']} | ${r['precio']}</div><hr>"
    return html

@app.route('/reporte_falla', methods=['POST'])
def reporte_falla():
    con=db(); con.execute("INSERT INTO taller (chofer,falla,fecha,estado) VALUES (?,?,?,?)",(session['u'], request.form['falla'], datetime.now().isoformat(), 'pendiente'))
    con.commit(); con.close(); return redirect('/mecanico')

if __name__=='__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
