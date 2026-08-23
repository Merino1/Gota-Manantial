import os
import math
from functools import wraps
from datetime import date, datetime, timedelta
from flask import Flask, render_template_string, request, redirect, jsonify, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'gota_manantial_secret_key_mexicali_2026'

db_url = os.environ.get('DATABASE_URL')
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url or 'sqlite:///manantial.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==================== MODELOS DE BASE DE DATOS ====================

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    rol = db.Column(db.String(20), nullable=False) # 'admin', 'secretaria', 'chofer', 'sistemas'
    nombre = db.Column(db.String(100), nullable=False)
    tipo_pago = db.Column(db.String(20), default="Comisionista")
    precio_agua = db.Column(db.Float, default=16.0)
    valor_tarjeta = db.Column(db.Float, default=22.0)

class ViajeChofer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chofer_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    fecha = db.Column(db.String(20))
    salida = db.Column(db.Float, default=40.0)
    regreso = db.Column(db.Float, default=0.0)

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente = db.Column(db.String(100), nullable=False)
    direccion = db.Column(db.String(200), nullable=False)
    cantidad = db.Column(db.Integer, default=1)
    precio = db.Column(db.Float, default=22.0)
    estado = db.Column(db.String(30), default="Pendiente")
    chofer_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    fecha = db.Column(db.DateTime, default=datetime.now)

class Ubicacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chofer_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    velocidad = db.Column(db.Float, default=0.0)
    fecha = db.Column(db.DateTime, default=datetime.now)

class Descuento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chofer_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    fecha = db.Column(db.Date, default=date.today)
    tipo = db.Column(db.String(20))
    cantidad = db.Column(db.Integer, default=1)
    tamano = db.Column(db.String(200))
    total = db.Column(db.Float, default=0)

class Tarjeta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chofer_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    fecha = db.Column(db.Date, default=date.today)
    cantidad = db.Column(db.Integer, default=1)
    monto_descuento = db.Column(db.Float, default=22.0)

class Solicitud(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chofer_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    fecha = db.Column(db.DateTime, default=datetime.now)
    tamano = db.Column(db.String(50))
    cantidad = db.Column(db.Integer, default=1)
    precio_estaba = db.Column(db.Float)
    precio_quedo = db.Column(db.Float)
    diferencia = db.Column(db.Float)
    direccion = db.Column(db.String(200))
    motivo = db.Column(db.String(200))
    estado = db.Column(db.String(20), default="Pendiente")

with app.app_context():
    db.create_all()

# ==================== FUNCIONES AUXILIARES ====================

def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def obtener_chofer_mas_cercano():
    choferes = Usuario.query.filter_by(rol='chofer').all()
    if not choferes: return None
    mas_cercano = None
    min_dist = float('inf')
    ref_lat, ref_lng = 32.6245, -115.452

    for ch in choferes:
        last_loc = Ubicacion.query.filter_by(chofer_id=ch.id).order_by(Ubicacion.fecha.desc()).first()
        if last_loc:
            dist = calcular_distancia(ref_lat, ref_lng, last_loc.lat, last_loc.lng)
            if dist < min_dist:
                min_dist = dist
                mas_cercano = ch.id

    return mas_cercano or (choferes[0].id if choferes else None)

# ==================== PLANTILLAS HTML ====================

LOGIN_HTML = """
<head><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;font-family:system-ui;background:#e0f7fa;display:flex;justify-content:center;align-items:center;height:100vh">
<div style="background:white;padding:35px;border-radius:20px;width:360px;text-align:center;box-shadow:0 8px 24px rgba(0,0,0,.1)">
<img src="/logo.png" style="width:180px" onerror="this.outerHTML='<div style=\\'background:#0891b2;color:white;padding:12px;border-radius:12px;font-weight:bold\\'>💧 GOTA DE MANANTIAL<br><small style=\\'font-weight:normal\\'>Mexicali</small></div>'">
<h2 style="margin:16px 0">GOTA DE MANANTIAL</h2>
{% if error %}<div style="background:#fee2e2;color:#991b1b;padding:8px;border-radius:8px;margin-bottom:8px">{{error}}</div>{% endif %}
<form method="post"><input name="username" placeholder="Usuario" required style="width:100%;padding:12px;margin:6px 0;border-radius:8px;border:1px solid #ccc;box-sizing:border-box"><input name="password" type="password" placeholder="Contraseña" required style="width:100%;padding:12px;margin:6px 0;border-radius:8px;border:1px solid #ccc;box-sizing:border-box"><button style="width:100%;padding:12px;background:#0891b2;color:white;border:none;border-radius:8px;font-weight:bold;cursor:pointer">Entrar</button></form>
</div></body>"""

ADMIN_HTML = """
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
.pedido-row{border-bottom:1px solid #eee;padding:10px 8px;font-size:13px;display:flex;justify-content:space-between;align-items:center}
.menu-btn{cursor:pointer;padding:4px 8px;border-radius:6px;font-weight:bold;font-size:18px}
.menu-btn:hover{background:#f1f5f9}
.dropdown{position:absolute;right:0;top:28px;background:white;border:1px solid #ddd;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,.15);min-width:160px;display:none;z-index:99}
.dropdown a{display:block;padding:8px 12px;text-decoration:none;color:#333;font-size:13px}
.dropdown a:hover{background:#f1f5f9}
.admin-grid { display: grid; grid-template-columns: 1fr 380px; gap: 12px; }
@media (max-width: 768px) { .admin-grid { grid-template-columns: 1fr; } }
th, td { text-align: left; padding: 6px; border-bottom: 1px solid #ddd; font-size: 13px; }
</style>
</head>
<body style="margin:0;font-family:system-ui;background:#f1f5f9">
<div style="background:white;padding:10px 14px;display:flex;justify-content:space-between;align-items:center"><div style="display:flex;align-items:center;gap:8px"><img src="/logo.png" style="height:38px" onerror="this.outerHTML='<b>💧 GOTA MXLI</b>'"><b>{{nombre}} ({{rol|upper}})</b></div><a href="/logout" style="color:red;font-weight:bold;text-decoration:none">Salir</a></div>
<div class="admin-grid" style="padding:12px;max-width:1200px;margin:auto">
<div>

<!-- CONTROL DE CARGAS Y REGRESOS -->
<div style="background:white;border-radius:12px;padding:12px;margin-bottom:12px;box-shadow:0 2px 4px rgba(0,0,0,0.05);border-left:5px solid #0891b2">
    <h3 style="margin-top:0;color:#0891b2">🚚 Control de Cargas y Inventario (Salida / Regreso)</h3>
    <form action="/viaje/add_admin" method="post" style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-bottom:12px">
        <select name="chofer_id" required style="padding:8px;border-radius:6px;border:1px solid #ccc">
            <option value="">-- Seleccionar Chofer --</option>
            {% for ch in choferes %}
            <option value="{{ch.id}}">{{ch.nombre}}</option>
            {% endfor %}
        </select>
        <input type="number" step="any" name="salida" placeholder="Cargó (Salida)" required style="width:100px;padding:8px;border-radius:6px;border:1px solid #ccc">
        <input type="number" step="any" name="regreso" placeholder="Regresó" value="0" required style="width:90px;padding:8px;border-radius:6px;border:1px solid #ccc">
        <button style="background:#0891b2;color:white;border:none;padding:8px 14px;border-radius:6px;font-weight:bold;cursor:pointer">Registrar Vuelta</button>
    </form>

    <!-- HISTORIAL DE CARGAS DEL DÍA -->
    <h4 style="margin:10px 0 6px 0;color:#334155;font-size:13px">📋 Historial de Cargas Registradas Hoy:</h4>
    <div style="max-height:150px;overflow-y:auto;background:#f8fafc;padding:8px;border-radius:8px;border:1px solid #e2e8f0">
        {% for v in viajes_hoy_todos %}
        <div style="display:flex;justify-content:space-between;align-items:center;font-size:12px;padding:4px 0;border-bottom:1px solid #eee">
            <span>👤 <b>{{dict.get(v.chofer_id, 'Chofer')}}</b> | Cargó: <b>{{v.salida}}</b> - Regresó: <b>{{v.regreso}}</b> (Vendió: <b style="color:#16a34a">{{v.salida - v.regreso}}</b>)</span>
            <a href="/viaje/borrar/{{v.id}}" onclick="return confirm('¿Borrar esta vuelta por equivocación?')" style="color:red;text-decoration:none;font-weight:bold;padding:2px 6px">❌ Borrar</a>
        </div>
        {% else %}
        <p style="font-size:12px;color:#888;margin:0;text-align:center">No se han registrado cargas hoy.</p>
        {% endfor %}
    </div>
</div>

<!-- RESUMEN / CORTE DIARIO -->
<div style="background:white;border-radius:12px;padding:12px;margin-bottom:12px;box-shadow:0 2px 4px rgba(0,0,0,0.05)">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
        <h3 style="margin:0;color:#0891b2">📊 Cortes Diarios de Choferes</h3>
        <form method="get" action="/panel" style="display:flex;gap:6px;align-items:center;margin:0">
            <input type="date" name="fecha_filtro" value="{{ fecha_filtro }}" style="padding:4px 8px;border:1px solid #ccc;border-radius:6px;font-size:12px">
            <button style="background:#0891b2;color:white;border:none;padding:5px 10px;border-radius:6px;font-weight:bold;cursor:pointer;font-size:12px">Filtrar</button>
        </form>
    </div>
    
    <div style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse">
            <thead>
                <tr style="background:#f8fafc;color:#475569">
                    <th>Chofer</th>
                    <th>Garrafones</th>
                    <th>Ventas Total</th>
                    <th>Gastos/Desc.</th>
                    <th>Tarjetas</th>
                    <th>A Entregar Caja</th>
                </tr>
            </thead>
            <tbody>
                {% for c in cortes %}
                <tr>
                    <td><b>{{ c.nombre }}</b></td>
                    <td><b style="color:#0891b2">{{ c.garrafones }} pcs</b></td>
                    <td>${{ c.ventas }}</td>
                    <td><span style="color:red">-${{ c.gastos }}</span></td>
                    <td><span style="color:#d97706">-${{ c.tarjetas_monto }}</span> <small>({{c.tarjetas_count}} pcs)</small></td>
                    <td><b style="color:#16a34a;font-size:15px">${{ c.caja }}</b></td>
                </tr>
                {% else %}
                <tr><td colspan="6" style="text-align:center;color:#666">No hay registros de cortes para esta fecha ({{ fecha_filtro }}).</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>

<div style="background:white;border-radius:12px;padding:12px;margin-bottom:12px"><h3>Nuevo Pedido - Mexicali</h3><form action="/pedido/nuevo" method="post" style="display:flex;gap:6px;flex-wrap:wrap"><input name="cliente" placeholder="Cliente" required style="padding:8px;border:1px solid #ccc;border-radius:6px"><input name="direccion" placeholder="Dirección" required style="padding:8px;border:1px solid #ccc;border-radius:6px"><input name="cantidad" type="number" value="1" style="width:60px;padding:8px;border:1px solid #ccc;border-radius:6px"><input name="precio" type="number" value="22" style="width:60px;padding:8px;border:1px solid #ccc;border-radius:6px"><select name="chofer_id" style="padding:8px;border:1px solid #ccc;border-radius:6px"><option value="auto">🤖 Asignar Chofer Más Cercano</option>{% for ch in choferes %}<option value="{{ch.id}}">👤 {{ch.nombre}}</option>{% endfor %}</select><button style="background:#16a34a;color:white;border:none;padding:8px 14px;border-radius:6px;font-weight:bold;cursor:pointer">Agregar Pedido</button></form></div>

<div style="background:#fffbeb;border:2px solid #f59e0b;border-radius:12px;padding:12px;margin-bottom:12px"><h3>Solicitudes de precio (Tambos)</h3>{% for s in solicitudes %}<div style="background:white;border:1px solid #fbbf24;padding:8px;border-radius:8px;margin-bottom:6px;font-size:13px"><b>{{s.cantidad}}x {{s.tamano}} ${{s.precio_estaba}}->${{s.precio_quedo}} = ${{s.diferencia}}</b><br>{{dict.get(s.chofer_id,'-')}} - {{s.direccion}} - {{s.motivo}}<br><a href="/autorizar/{{s.id}}" style="background:#16a34a;color:white;padding:5px 10px;border-radius:5px;text-decoration:none;display:inline-block;margin-top:4px">Aceptar</a> <a href="/rechazar/{{s.id}}" style="background:#dc2626;color:white;padding:5px 10px;border-radius:5px;text-decoration:none;display:inline-block;margin-top:4px">Rechazar</a></div>{% else %}<p style="font-size:13px;color:#666">Sin solicitudes pendientes</p>{% endfor %}</div>

<div style="background:white;border-radius:12px;padding:12px"><h3>Pedidos Registrados</h3>
{% for p in pedidos %}
<div class="pedido-row"><span><b>{{p.cliente}}</b> - {{p.direccion}} - {{p.cantidad}}x ${{p.precio}} - 
<b style="color:{% if p.estado=='Entregado' %}green{% elif p.estado=='No salio nadie' %}red{% else %}orange{% endif %}">{{p.estado}}</b> - 
<span style="color:#0891b2">{{dict.get(p.chofer_id,'Sin asignar')}}</span></span>
<div style="position:relative"><div class="menu-btn" onclick="toggleMenu({{p.id}})">⋮</div><div id="menu-{{p.id}}" class="dropdown"><a href="/pedido/entregar/{{p.id}}">✅ Entregado</a><a href="/pedido/no_salio/{{p.id}}">❌ No Salió Nadie</a><div style="border-top:1px solid #eee;padding:6px 12px;font-size:11px;color:#888">Reasignar a:</div>{% for ch in choferes %}<a href="/pedido/mover/{{p.id}}?chofer_id={{ch.id}}">👤 {{ch.nombre}}</a>{% endfor %}</div></div></div>
{% endfor %}</div>
</div>

<div>
<div style="background:white;border-radius:12px;padding:12px;margin-bottom:12px"><h3>Mapa Choferes Mexicali</h3><div id="map" style="height:320px;border-radius:8px"></div></div>

<div style="background:white;border-radius:12px;padding:12px"><h3>Configurar Empleados</h3>
{% if rol in ['admin', 'sistemas'] %}
<form action="/usuario/nuevo" method="post" style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:12px">
<input name="nombre" placeholder="Nombre" required style="width:45%;padding:6px;border:1px solid #ccc;border-radius:6px">
<input name="username" placeholder="Usuario" required style="width:45%;padding:6px;border:1px solid #ccc;border-radius:6px">
<input name="password" placeholder="Pass" required style="width:45%;padding:6px;border:1px solid #ccc;border-radius:6px">
<select name="rol" style="width:45%;padding:6px;border:1px solid #ccc;border-radius:6px">
    <option value="chofer">Chofer</option>
    <option value="secretaria">Secretaria</option>
    <option value="admin">Admin</option>
</select>
<select name="tipo_pago" style="width:45%;padding:6px;border:1px solid #ccc;border-radius:6px"><option value="Comisionista">Comisionista</option><option value="Sueldo">Sueldo Fijo</option></select>
<input name="precio_agua" type="number" step="0.1" placeholder="$ Agua" style="width:45%;padding:6px;border:1px solid #ccc;border-radius:6px">
<input name="valor_tarjeta" type="number" step="0.1" placeholder="$ Tarjeta" style="width:45%;padding:6px;border:1px solid #ccc;border-radius:6px">
<button style="width:100%;margin-top:4px;background:#0891b2;color:white;border:none;padding:8px;border-radius:6px;font-weight:bold;cursor:pointer">Crear Empleado</button>
</form>
{% endif %}

{% for u in usuarios %}
<div style="border-bottom:1px solid #eee;padding:8px 0;font-size:12px">
<b>{{u.nombre}} ({{u.rol|upper}})</b> - <i>{{u.tipo_pago}}</i><br>
{% if u.rol=='chofer' %}
    {% if rol in ['admin', 'sistemas'] %}
    <form action="/usuario/actualizar_config/{{u.id}}" method="post" style="display:inline-flex;gap:4px;margin-top:4px">
    Agua: $<input name="precio_agua" value="{{u.precio_agua}}" style="width:35px">
    Tarjeta: $<input name="valor_tarjeta" value="{{u.valor_tarjeta}}" style="width:35px">
    <button style="font-size:10px">Guardar</button>
    </form><br>
    {% endif %}
    <a href="/mapa/detallado/{{u.id}}" style="color:#0891b2">📍 Ver Ruta GPS</a>
{% endif %}
{% if rol in ['admin', 'sistemas'] and u.username != 'sistemas' %}
 | <a href="/usuario/reset/{{u.id}}">Reset Pass</a> | <a href="/usuario/borrar/{{u.id}}" style="color:red">Baja</a>
{% endif %}
</div>
{% endfor %}
</div>
</div>
</div>
<script>
function toggleMenu(id){
  document.querySelectorAll('.dropdown').forEach(d=>{if(d.id!=='menu-'+id) d.style.display='none'});
  var m=document.getElementById('menu-'+id); m.style.display = m.style.display==='block' ? 'none' : 'block';
}
document.addEventListener('click', function(e){ if(!e.target.classList.contains('menu-btn')){ if(!e.target.closest('.dropdown')) document.querySelectorAll('.dropdown').forEach(d=>d.style.display='none'); }});
var map=L.map('map').setView([32.6245, -115.452],12);
L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', { maxZoom: 19 }).addTo(map);
var markers={};
function cargar(){fetch('/api/ubicaciones').then(r=>r.json()).then(d=>{d.forEach(c=>{ if(markers[c.id]) map.removeLayer(markers[c.id]); markers[c.id]=L.marker([c.lat,c.lng]).addTo(map).bindPopup(c.nombre) })})}
cargar(); setInterval(cargar,10000);
// Audio generado por código (no necesitas subir ningún archivo mp3)
function sonarAlertaAdmin() {
    let ctx = new (window.AudioContext || window.webkitAudioContext)();
    let osc = ctx.createOscillator();
    let gain = ctx.createGain();
    osc.connect(gain); gain.connect(ctx.destination);
    osc.type = "triangle"; osc.frequency.value = 880; // Tono agudo
    gain.gain.setValueAtTime(0.1, ctx.currentTime);
    osc.start(); osc.stop(ctx.currentTime + 0.3);
}

// Revisar si hay solicitudes pendientes cada 5 segundos
setInterval(() => {
    fetch('/api/solicitudes_pendientes')
    .then(r => r.json())
    .then(data => {
        if (data.total > 0) {
            sonarAlertaAdmin();
            // Opcional: mostrar notificación nativa del navegador si da permiso
            if (Notification.permission === "granted") {
                new Notification("⚠️ Solicitud de Precio", { body: `Tienes ${data.total} solicitud(es) pendiente(s)` });
            }
        }
    });
}, 5000);

// Solicitar permiso de notificaciones al tocar la pantalla
document.addEventListener('click', () => {
    if (Notification.permission === "default") Notification.requestPermission();
}, { once: true });

</script>
</body>"""

CHOFER_HTML = """
<head><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;font-family:system-ui;background:#f0fdf4">
<audio id="alerta-sound" src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" preload="auto"></audio>

<div style="background:#fef9c3; border:2px solid #ca8a04; padding:8px; border-radius:8px; margin:10px; text-align:center;">
    <b>META SEMANAL:</b> <span style="font-size:16px; font-weight:bold; color:#a16207;">{{ garrafones_semana }} / 700</span>
</div>

<div style="background:white;padding:10px 14px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #ddd">
    <div>
        <b>{{nombre}}</b> (<i>{{tipo_pago}}</i>)<br>
        <small style="color:#666">Agua: ${{precio_agua}} | Tarjeta: ${{valor_tarjeta}}</small><br>
        <small style="color:#666">Corte Líquido Caja: <b style="color:#16a34a;font-size:16px">${{total_entrega_caja}}</b></small>
    </div>
    <a href="/logout" style="color:red;text-decoration:none;font-weight:bold">Salir</a>
</div>

<div style="padding:12px;max-width:700px;margin:auto">

<!-- VUELTAS REGISTRADAS POR OFICINA (INFORMATIVO) -->
<div style="background: white; padding: 14px; border-radius: 12px; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left:6px solid #16a34a">
    <h3 style="margin-top:0; color:#16a34a">🚚 Cargas Asignadas Hoy (Oficina)</h3>
    <div style="font-size:13px; color:#444;">
        {% for v in viajes_hoy %}
        <div style="display:flex; justify-content:space-between; border-bottom:1px dashed #eee; padding:6px 0;">
            <span>Vuelta #{{ loop.index }}: Llevó <b>{{ v.salida }}</b>, Regresó <b>{{ v.regreso }}</b></span>
            <span>Vendidos: <b style="color:#16a34a">{{ v.salida - v.regreso }}</b></span>
        </div>
        {% else %}
        <p style="color:#666; text-align:center; margin:4px 0;">Sin cargas autorizadas aún por oficina.</p>
        {% endfor %}
    </div>
</div>

<!-- MIS PEDIDOS ASIGNADOS -->
<div style="background: white; padding: 14px; border-radius: 12px; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left:6px solid #0891b2">
    <h3 style="margin-top:0;color:#0891b2">🚚 Mis Pedidos Asignados (<span id="cant-pedidos">{{ pedidos|length }}</span>)</h3>
    <div id="contenedor-pedidos">
        {% for p in pedidos %}
        <div style="background:#f8fafc; border:1px solid #e2e8f0; padding:10px; border-radius:8px; margin-bottom:8px;">
            <div style="margin-bottom:6px">
                <b>{{p.cliente}}</b> ({{p.cantidad}} Garrafones - ${{p.precio}} ea)<br>
                <small style="color:#475569">📍 {{p.direccion}}</small>
            </div>
            <div style="display:flex; gap:6px;">
                <a href="/pedido/entregar/{{p.id}}" style="background:#16a34a; color:white; padding:8px 12px; border-radius:6px; text-decoration:none; font-weight:bold; font-size:12px; flex:1; text-align:center;">✅ Entregado</a>
                <a href="/pedido/no_salio/{{p.id}}" style="background:#dc2626; color:white; padding:8px 12px; border-radius:6px; text-decoration:none; font-weight:bold; font-size:12px; flex:1; text-align:center;">❌ No Salió Nadie</a>
            </div>
            <a href="https://www.google.com/maps/search/?api=1&query={{ p.direccion | urlencode }}" target="_blank" style="background:#0284c7; color:white; padding:8px 12px; border-radius:6px; text-decoration:none; font-weight:bold; font-size:12px; text-align:center; display:block; margin-top:6px;">
                🗺️ Abrir Navegación GPS
            </a>
        </div>
        {% else %}
        <p style="color:#64748b; font-size:14px; text-align:center;">No tienes pedidos pendientes en este momento.</p>
        {% endfor %}
    </div>
</div>

<!-- RESUMEN CORTE DIARIO -->
<div style="background: white; padding: 14px; border-radius: 12px; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
    <h3 style="margin-top:0;">📊 Resumen de Corte Hoy</h3>
    <div style="font-size:13px; line-height:1.8">
        (+) Ventas Totales: <b>${{ventas_hoy}}</b><br>
        (-) Descuentos / Gastos: <b style="color:red">-${{total_descuentos}}</b><br>
        (-) Tarjetas ({{tarjetas_count}} pcs x ${{valor_tarjeta}}): <b style="color:red">-${{total_tarjetas}}</b><br>
        <hr style="border:0; border-top:1px dashed #ccc">
        <b>(=) Total a Entregar en Caja: <span style="color:#16a34a; font-size:16px">${{total_entrega_caja}}</span></b>
    </div>
</div>

<!-- REGISTRO DE TARJETAS PROMOCIONALES -->
<div style="background: white; padding: 14px; border-radius: 12px; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left:6px solid #eab308">
    <h3 style="margin-top:0; color:#ca8a04">💳 Tarjetas Promocionales Recogidas</h3>
    <p style="font-size:12px; color:#666; margin-top:-8px">Cada tarjeta aplica ${{valor_tarjeta}} de descuento al corte.</p>
    <form action="/tarjeta/add" method="post" style="display:flex; gap:6px;">
        <input type="number" name="cantidad" placeholder="Cantidad Tarjetas" value="1" min="1" required style="width:70%; padding:10px; border:1px solid #ccc; border-radius:6px;">
        <button style="width:30%; background:#eab308; color:white; border:none; border-radius:6px; font-weight:bold; cursor:pointer;">Reportar</button>
    </form>
</div>

<!-- REGISTRO DE GASTOS Y DESCUENTOS -->
<div style="background: white; padding: 14px; border-radius: 12px; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
    <h3 style="margin-top: 0; color: #dc2626;">⛽ Registrar Descuento / Gasto</h3>
    <form action="/descuento/add" method="post">
        <div style="display: flex; gap: 6px; margin-bottom: 6px;">
            <input type="text" name="tipo" placeholder="Tipo (ej. Gasolina)" required style="width: 50%; padding: 10px; border: 1px solid #ccc; border-radius: 6px;">
            <input type="number" name="cantidad" placeholder="Cant." value="1" required style="width: 25%; padding: 10px; border: 1px solid #ccc; border-radius: 6px;">
            <input type="number" step="0.01" name="total" placeholder="Total $" required style="width: 25%; padding: 10px; border: 1px solid #ccc; border-radius: 6px;">
        </div>
        <input type="text" name="tamano" placeholder="Descripción / Detalles" style="width: 100%; padding: 10px; margin-bottom: 8px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box;">
        <button style="width: 100%; padding: 12px; background: #dc2626; color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer;">Agregar Descuento</button>
    </form>
</div>

<!-- SOLICITUD DE PRECIO PARA TAMBOS -->
<div style="background: white; padding: 14px; border-radius: 12px; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
    <h3 style="margin-top: 0; color: #0891b2;">🛢️ Solicitar Precio Especial (Tambos)</h3>
    <form action="/solicitar_precio" method="post">
        <input type="text" name="tamano" placeholder="Tipo de Tambo (ej. Tambo 11G)" required style="width: 100%; padding: 10px; margin-bottom: 6px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box;">
        <div style="display: flex; gap: 6px; margin-bottom: 6px;">
            <input type="number" name="cantidad" placeholder="Cant." value="1" required style="width: 30%; padding: 10px; border: 1px solid #ccc; border-radius: 6px;">
            <input type="number" step="0.1" name="estaba" placeholder="Precio Orig." required style="width: 35%; padding: 10px; border: 1px solid #ccc; border-radius: 6px;">
            <input type="number" step="0.1" name="quedo" placeholder="Precio Nuev." required style="width: 35%; padding: 10px; border: 1px solid #ccc; border-radius: 6px;">
        </div>
        <input type="text" name="direccion" placeholder="Dirección / Cliente" required style="width: 100%; padding: 10px; margin-bottom: 6px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box;">
        <input type="text" name="motivo" placeholder="Motivo del descuento" required style="width: 100%; padding: 10px; margin-bottom: 8px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box;">
        <button style="width: 100%; padding: 12px; background: #0891b2; color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer;">Solicitar Autorización</button>
    </form>
</div>

</div>

<script>
let ultimosPedidos = {{ pedidos|length }};
setInterval(() => {
    fetch('/api/mis_pedidos').then(r => r.json()).then(data => {
        if (data.length > ultimosPedidos) {
            document.getElementById('alerta-sound').play().catch(()=>{});
            alert("⚠️ ¡Tienes un NUEVO PEDIDO asignado!");
            location.reload();
        }
        ultimosPedidos = data.length;
    });
}, 7000);

function iniciarGps() {
    if (!navigator.geolocation) return;
    navigator.geolocation.watchPosition(pos => {
        fetch('/chofer/update_location', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lat: pos.coords.latitude, lng: pos.coords.longitude })
        });
    }, null, { enableHighAccuracy: true, maximumAge: 0, timeout: 8000 });
}
iniciarGps();
</script>
</body>"""

MAPA_DETALLADO_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Mapa Detallado - {{ ch.nombre }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>#map { height: 90vh; width: 100%; }</style>
</head>
<body style="margin:0; font-family:system-ui;">
    <div style="padding: 10px; background: #333; color: white;">
        <h2>Recorrido de {{ ch.nombre }}</h2>
        <a href="/panel" style="color: #38bdf8;">← Volver al panel</a>
    </div>
    <div id="map"></div>
    <script>
        var map = L.map('map').setView([32.6245, -115.452], 13);
        L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', { maxZoom: 19 }).addTo(map);

        var puntos = {{ puntos|tojson }};
        var latlngs = puntos.map(p => [p.lat, p.lng]);
        if(latlngs.length > 0) {
            var polyline = L.polyline(latlngs, {color: 'blue'}).addTo(map);
            map.fitBounds(polyline.getBounds());
        }
// SONIDO Y ALERTA PARA EL ADMIN CUANDO HAY SOLICITUDES DE PRECIO
function sonarAlertaAdmin() {
    let ctx = new (window.AudioContext || window.webkitAudioContext)();
    let osc = ctx.createOscillator();
    let gain = ctx.createGain();
    osc.connect(gain); gain.connect(ctx.destination);
    osc.type = "triangle"; osc.frequency.value = 880;
    gain.gain.setValueAtTime(0.1, ctx.currentTime);
    osc.start(); osc.stop(ctx.currentTime + 0.3);
}

setInterval(() => {
    fetch('/api/solicitudes_pendientes')
    .then(r => r.json())
    .then(data => {
        if (data.total > 0) {
            sonarAlertaAdmin();
        }
    });
}, 5000);

    </script>
</body>
</html>"""

# ==================== MIDDLEWARES / DECORADORES ====================

def login_required(f):
    @wraps(f)
    def w(*a, **kw):
        if 'user_id' not in session: return redirect("/")
        return f(*a, **kw)
    return w

def staff_required(f):
    @wraps(f)
    def w(*a, **kw):
        if session.get('rol') not in ('admin', 'secretaria', 'sistemas'): 
            return "No autorizado", 403
        return f(*a, **kw)
    return w

def admin_required(f):
    @wraps(f)
    def w(*a, **kw):
        if session.get('rol') not in ('admin', 'sistemas'): 
            return "No autorizado", 403
        return f(*a, **kw)
    return w

# ==================== RUTAS DE LA APLICACIÓN ====================

@app.route("/logo.png")
def logo_file():
    return send_from_directory(".", "logo.png") if os.path.exists("logo.png") else ("", 404)

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username_input = request.form.get('username', '').strip()
        password_input = request.form.get('password', '').strip()

        u = Usuario.query.filter_by(username=username_input).first()
        if u and check_password_hash(u.password, password_input):
            session['user_id'] = u.id
            session['rol'] = u.rol
            session['nombre'] = u.nombre
            session['username'] = u.username
            return redirect("/panel")
        return render_template_string(LOGIN_HTML, error="Usuario o contraseña incorrectos")
    return render_template_string(LOGIN_HTML, error=None)

@app.route('/panel')
@login_required
def panel():
    rol = session.get('rol')
    user_id = session.get('user_id')

    if rol in ['admin', 'secretaria', 'sistemas']:
        pedidos = Pedido.query.order_by(Pedido.id.desc()).all()
        choferes = Usuario.query.filter_by(rol='chofer').all()
        dict_choferes = {c.id: c.nombre for c in choferes}
        
        if session.get('username') == 'sistemas':
            usuarios = Usuario.query.all()
        else:
            usuarios = Usuario.query.filter(Usuario.username != 'sistemas').all()

        solicitudes_pend = Solicitud.query.filter_by(estado='Pendiente').all()

        # 1. Primero se define la fecha del filtro
        fecha_filtro_str = request.args.get('fecha_filtro')
        if fecha_filtro_str:
            try:
                fecha_dt = datetime.strptime(fecha_filtro_str, '%Y-%m-%d').date()
            except:
                fecha_dt = date.today()
                fecha_filtro_str = fecha_dt.strftime('%Y-%m-%d')
        else:
            fecha_dt = date.today()
            fecha_filtro_str = fecha_dt.strftime('%Y-%m-%d')

        # 2. AHORA SÍ consultamos los viajes de la fecha seleccionada
        viajes_hoy_todos = ViajeChofer.query.filter_by(fecha=fecha_filtro_str).all()

        cortes_choferes = []
        for ch in choferes:
            precio_agua = ch.precio_agua or 16.0
            val_tarjeta = ch.valor_tarjeta or 22.0

            vueltas = ViajeChofer.query.filter_by(chofer_id=ch.id, fecha=fecha_filtro_str).all()
            garrafones_vueltas = sum(max(0, v.salida - v.regreso) for v in vueltas)
            ventas_vueltas = garrafones_vueltas * precio_agua

            ventas_pedidos = db.session.query(db.func.sum(Pedido.cantidad * Pedido.precio)).filter(
                Pedido.chofer_id == ch.id,
                Pedido.estado == 'Entregado',
                db.func.date(Pedido.fecha) == fecha_dt
            ).scalar() or 0.0

            ventas_totales = ventas_vueltas + ventas_pedidos

            gastos = db.session.query(db.func.sum(Descuento.total)).filter(
                Descuento.chofer_id == ch.id,
                Descuento.fecha == fecha_dt
            ).scalar() or 0.0

            tarjetas_cnt = db.session.query(db.func.sum(Tarjeta.cantidad)).filter(
                Tarjeta.chofer_id == ch.id,
                Tarjeta.fecha == fecha_dt
            ).scalar() or 0

            tarjetas_monto = tarjetas_cnt * val_tarjeta
            caja = max(0.0, ventas_totales - gastos - tarjetas_monto)

            cortes_choferes.append({
                'nombre': ch.nombre,
                'garrafones': garrafones_vueltas,
                'ventas': ventas_totales,
                'gastos': gastos,
                'tarjetas_count': tarjetas_cnt,
                'tarjetas_monto': tarjetas_monto,
                'caja': caja
            })

        return render_template_string(
            ADMIN_HTML,
            pedidos=pedidos,
            choferes=choferes,
            dict=dict_choferes,
            usuarios=usuarios,
            rol=rol,
            nombre=session.get('nombre'),
            solicitudes=solicitudes_pend,
            cortes=cortes_choferes,
            fecha_filtro=fecha_filtro_str,
            viajes_hoy_todos=viajes_hoy_todos
        )
    else:
        usuario = db.session.get(Usuario, user_id)
        hoy = date.today()
        hoy_str = hoy.strftime('%Y-%m-%d')
        precio_agua = usuario.precio_agua or 16.0
        valor_tarjeta_chofer = usuario.valor_tarjeta or 22.0

        mis_pedidos = Pedido.query.filter_by(chofer_id=user_id, estado='Pendiente').all()
        viajes_hoy = ViajeChofer.query.filter_by(chofer_id=user_id, fecha=hoy_str).all()

        garrafones_vueltas_hoy = sum(max(0, v.salida - v.regreso) for v in viajes_hoy)
        ventas_vueltas_hoy = garrafones_vueltas_hoy * precio_agua

        hace_7_dias_str = (hoy - timedelta(days=7)).strftime('%Y-%m-%d')
        viajes_semana = ViajeChofer.query.filter(
            ViajeChofer.chofer_id == user_id,
            ViajeChofer.fecha >= hace_7_dias_str
        ).all()
        garrafones_semana = sum(max(0, v.salida - v.regreso) for v in viajes_semana)

        ventas_pedidos_hoy = db.session.query(db.func.sum(Pedido.cantidad * Pedido.precio)).filter(
            Pedido.chofer_id == user_id,
            Pedido.estado == 'Entregado',
            db.func.date(Pedido.fecha) == hoy
        ).scalar() or 0.0

        ventas_totales_hoy = ventas_vueltas_hoy + ventas_pedidos_hoy

        total_descuentos = db.session.query(db.func.sum(Descuento.total)).filter(
            Descuento.chofer_id == user_id,
            Descuento.fecha == hoy
        ).scalar() or 0.0

        tarjetas_count = db.session.query(db.func.sum(Tarjeta.cantidad)).filter(
            Tarjeta.chofer_id == user_id,
            Tarjeta.fecha == hoy
        ).scalar() or 0

        total_tarjetas = tarjetas_count * valor_tarjeta_chofer
        total_entrega_caja = max(0.0, ventas_totales_hoy - total_descuentos - total_tarjetas)

        return render_template_string(
            CHOFER_HTML,
            nombre=session.get('nombre'),
            tipo_pago=usuario.tipo_pago,
            pedidos=mis_pedidos,
            precio_agua=precio_agua,
            valor_tarjeta=valor_tarjeta_chofer,
            ventas_hoy=ventas_totales_hoy,
            total_descuentos=total_descuentos,
            tarjetas_count=tarjetas_count,
            total_tarjetas=total_tarjetas,
            total_entrega_caja=total_entrega_caja,
            garrafones_semana=garrafones_semana,
            viajes_hoy=viajes_hoy
        )

@app.route("/viaje/add_admin", methods=["POST"])
@login_required
@staff_required
def viaje_add_admin():
    try:
        chofer_id = int(request.form.get('chofer_id'))
        salida = float(request.form.get('salida', 40))
        regreso = float(request.form.get('regreso', 0))
        hoy_str = date.today().strftime('%Y-%m-%d')

        v = ViajeChofer(chofer_id=chofer_id, fecha=hoy_str, salida=salida, regreso=regreso)
        db.session.add(v)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
    return redirect("/panel")

@app.route("/pedido/nuevo", methods=["POST"])
@login_required
@staff_required
def nuevo_pedido():
    try:
        cid = request.form.get('chofer_id')
        if cid == "auto" or not cid:
            cid = obtener_chofer_mas_cercano()
        else:
            try: cid = int(cid)
            except: cid = None

        p = Pedido(
            cliente=request.form['cliente'][:100],
            direccion=request.form['direccion'][:200],
            cantidad=max(1, int(request.form['cantidad'])),
            precio=max(0, float(request.form.get('precio', 22))),
            chofer_id=cid
        )
        db.session.add(p)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
    return redirect("/panel")

@app.route("/pedido/mover/<int:id>")
@login_required
@staff_required
def mover(id):
    p = db.session.get(Pedido, id)
    nc = request.args.get('chofer_id')
    if p and nc is not None:
        try:
            nc = int(nc)
            p.chofer_id = None if nc == 0 else nc
            db.session.commit()
        except:
            db.session.rollback()
    return redirect("/panel")

@app.route("/viaje/borrar/<int:id>")
@login_required
@staff_required
def borrar_viaje(id):
    v = db.session.get(ViajeChofer, id)
    if v:
        db.session.delete(v)
        db.session.commit()
    return redirect("/panel")

@app.route("/pedido/entregar/<int:id>")
@login_required
def entregar(id):
    p = db.session.get(Pedido, id)
    if p and (session['rol'] in ('admin', 'secretaria', 'sistemas') or p.chofer_id == session['user_id']):
        p.estado = "Entregado"
        db.session.commit()
    return redirect("/panel")

@app.route("/pedido/no_salio/<int:id>")
@login_required
def no_salio(id):
    p = db.session.get(Pedido, id)
    if p and (session['rol'] in ('admin', 'secretaria', 'sistemas') or p.chofer_id == session['user_id']):
        p.estado = "No salio nadie"
        db.session.commit()
    return redirect("/panel")

@app.route("/tarjeta/add", methods=["POST"])
@login_required
def tarjeta_add():
    try:
        usuario = db.session.get(Usuario, session['user_id'])
        v_tarjeta = usuario.valor_tarjeta if usuario else 22.0
        cant = max(1, int(request.form.get('cantidad', 1)))
        t = Tarjeta(chofer_id=session['user_id'], fecha=date.today(), cantidad=cant, monto_descuento=v_tarjeta)
        db.session.add(t)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
    return redirect("/panel")

@app.route("/descuento/add", methods=["POST"])
@login_required
def desc_add():
    try:
        d = Descuento(
            chofer_id=session['user_id'],
            fecha=date.today(),
            tipo=request.form['tipo'][:20],
            cantidad=max(1, int(request.form.get('cantidad', 1))),
            tamano=request.form.get('tamano', '')[:200],
            total=max(0, float(request.form.get('total', 0)))
        )
        db.session.add(d)
        db.session.commit()
    except:
        db.session.rollback()
    return redirect("/panel")

@app.route("/solicitar_precio", methods=["POST"])
@login_required
def solicitar_precio():
    try:
        estaba = float(request.form.get('estaba', 0) or 0)
        quedo = float(request.form.get('quedo', 0) or 0)
        cant = max(1, int(request.form.get('cantidad', 1) or 1))
        if quedo < 0 or quedo >= estaba:
            return redirect("/panel")
        dif = (estaba - quedo) * cant
        s = Solicitud(
            chofer_id=session['user_id'],
            tamano=request.form.get('tamano', '')[:50],
            cantidad=cant,
            precio_estaba=estaba,
            precio_quedo=quedo,
            diferencia=dif,
            direccion=request.form.get('direccion', '')[:200],
            motivo=request.form.get('motivo', '')[:200]
        )
        db.session.add(s)
        db.session.commit()
    except:
        db.session.rollback()
    return redirect("/panel")

@app.route('/api/solicitudes_pendientes')
@login_required
def api_solicitudes_pendientes():
    cant = Solicitud.query.filter_by(estado='Pendiente').count()
    return jsonify({'total': cant})

@app.route('/api/mis_pedidos_count')
@login_required
def api_mis_pedidos_count():
    user_id = session.get('user_id')
    cant = Pedido.query.filter_by(chofer_id=user_id, estado='Pendiente').count()
    return jsonify({'count': cant})

@app.route("/autorizar/<int:id>")
@login_required
@staff_required
def autorizar(id):
    s = db.session.get(Solicitud, id)
    if s and s.estado == "Pendiente":
        s.estado = "Autorizado"
        d = Descuento(
            chofer_id=s.chofer_id,
            fecha=date.today(),
            tipo="Descuento Tambo",
            cantidad=s.cantidad,
            tamano=f"{s.tamano} ${s.precio_estaba}->${s.precio_quedo} | {s.direccion}"[:200],
            total=max(0, s.diferencia)
        )
        db.session.add(d)
        db.session.commit()
    return redirect("/panel")

@app.route("/rechazar/<int:id>")
@login_required
@staff_required
def rechazar(id):
    s = db.session.get(Solicitud, id)
    if s:
        s.estado = "Rechazado"
        db.session.commit()
    return redirect("/panel")

@app.route("/usuario/nuevo", methods=["POST"])
@login_required
@admin_required
def nuevo_usuario():
    try:
        u = Usuario(
            username=request.form['username'].strip()[:80],
            password=generate_password_hash(request.form['password']),
            rol=request.form['rol'],
            nombre=request.form['nombre'][:100],
            tipo_pago=request.form.get('tipo_pago', 'Comisionista'),
            precio_agua=max(0, float(request.form.get('precio_agua', 16) or 16)),
            valor_tarjeta=max(0, float(request.form.get('valor_tarjeta', 22) or 22))
        )
        db.session.add(u)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
    return redirect("/panel")

@app.route("/usuario/actualizar_config/<int:id>", methods=["POST"])
@login_required
@admin_required
def actualizar_config(id):
    u = db.session.get(Usuario, id)
    if u:
        u.precio_agua = max(0, float(request.form.get('precio_agua', 16) or 16))
        u.valor_tarjeta = max(0, float(request.form.get('valor_tarjeta', 22) or 22))
        db.session.commit()
    return redirect("/panel")

@app.route("/usuario/borrar/<int:id>")
@login_required
@admin_required
def borrar(id):
    u = db.session.get(Usuario, id)
    if u and u.username != 'sistemas' and u.id != session['user_id']:
        db.session.delete(u)
        db.session.commit()
    return redirect("/panel")

@app.route("/usuario/reset/<int:id>")
@login_required
@admin_required
def reset(id):
    u = db.session.get(Usuario, id)
    if u and u.username != 'sistemas':
        u.password = generate_password_hash('123456')
        db.session.commit()
    return redirect("/panel")

@app.route("/chofer/update_location", methods=["POST"])
@login_required
def up_loc():
    d = request.json or {}
    try:
        lat = float(d.get('lat'))
        lng = float(d.get('lng'))
        if -90 <= lat <= 90 and -180 <= lng <= 180:
            db.session.add(Ubicacion(chofer_id=session['user_id'], lat=lat, lng=lng))
            db.session.commit()
    except:
        db.session.rollback()
    return jsonify(ok=True)

@app.route("/api/mis_pedidos")
@login_required
def mis_pedidos_api():
    pedidos = Pedido.query.filter_by(chofer_id=session['user_id'], estado='Pendiente').all()
    return jsonify([{'id': p.id, 'cliente': p.cliente} for p in pedidos])

@app.route("/mapa/detallado/<int:chofer_id>")
@login_required
@staff_required
def mapa_detallado(chofer_id):
    ch = db.session.get(Usuario, chofer_id)
    hoy = date.today().strftime('%Y-%m-%d')

    puntos = Ubicacion.query.filter_by(chofer_id=chofer_id).filter(
        db.func.strftime('%Y-%m-%d', Ubicacion.fecha) == hoy
    ).order_by(Ubicacion.fecha.asc()).all()

    recorrido_coords = [{"lat": p.lat, "lng": p.lng, "hora": p.fecha.strftime("%H:%M")} for p in puntos]
    return render_template_string(MAPA_DETALLADO_HTML, ch=ch, puntos=recorrido_coords)

@app.route("/api/ubicaciones")
@login_required
def api_ubs():
    data = []
    for c in Usuario.query.filter_by(rol='chofer').all():
        u = Ubicacion.query.filter_by(chofer_id=c.id).order_by(Ubicacion.fecha.desc()).first()
        if u:
            data.append({'id': c.id, 'nombre': c.nombre, 'lat': u.lat, 'lng': u.lng})
    return jsonify(data)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ==================== INICIALIZACIÓN Y EJECUCIÓN ====================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        u = Usuario.query.filter_by(username='sistemas').first()
        if not u:
            u = Usuario(
                username='sistemas',
                password=generate_password_hash("admin123"),
                rol='sistemas',
                nombre='Sistemas',
                tipo_pago='Sueldo',
                precio_agua=16,
                valor_tarjeta=22
            )
            db.session.add(u)
            db.session.commit()
        else:
            u.password = generate_password_hash("admin123")
            db.session.commit()

    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)), debug=True)
