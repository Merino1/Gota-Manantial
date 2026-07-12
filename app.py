from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = 'gotademanantial_mexicali_2026'

# BASE DE DATOS FAKE PA EMPEZAR - YA DESPUÉS METEMOS SQL
usuarios = {
    'Karina': {
        'password': generate_password_hash('gota123'),
        'rol': 'admin', # Karina es admin, y admin puede hacer todo lo de secre
        'nombre': 'Patrona Karina'
    },
    'Alfonso': {
        'password': generate_password_hash('gota123'),
        'rol': 'chofer',
        'nombre': 'Alfonso Chofer'
    }
}

pedidos = [] # Aquí se guardan los pedidos

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def requiere_rol(roles_permitidos):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('rol') not in roles_permitidos:
                return "No tienes permiso wey 🔒", 403
            return f(*args, **kwargs)
        return decorated
    return decorator

@app.route('/')
@login_required
def home():
    if session['rol'] == 'admin':
        return redirect(url_for('panel_admin'))
    else:
        return redirect(url_for('panel_chofer'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = usuarios.get(username)

        if user and check_password_hash(user['password'], password):
            session['username'] = username
            session['rol'] = user['rol']
            session['nombre'] = user['nombre']
            return redirect(url_for('home'))
        else:
            return "Usuario o contraseña mal we 😞"

    return '''
    <h2>Gota de Manantial - Mexicali 💧</h2>
    <form method="post">
        Usuario: <input name="username"><br><br>
        Pass: <input name="password" type="password"><br><br>
        <input type="submit" value="Entrar">
    </form>
    '''

@app.route('/panel_admin')
@login_required
@requiere_rol(['admin'])
def panel_admin():
    pedidos_pendientes = [p for p in pedidos if p['estado'] == 'pendiente']
    return f'''
    <h2>Panel Patrona Karina 👑</h2>
    <p>Hola {session['nombre']} | <a href="/logout">Salir</a></p>

    <h3>Crear Pedido Nuevo</h3>
    <form action="/crear_pedido" method="post">
        Dirección: <input name="direccion" placeholder="Calle Juárez #123" required><br><br>
        Cantidad: <input name="cantidad" placeholder="5 garrafones o dejar vacío"><br><br>
        Asignar a: <select name="chofer">
            <option value="Alfonso">Alfonso</option>
        </select><br><br>
        <input type="submit" value="Crear Pedido">
    </form>

    <h3>Pedidos Pendientes: {len(pedidos_pendientes)}</h3>
    {''.join([f"<p><b>{p['direccion']}</b> - {p['cantidad']} - Asignado a: {p['chofer']} - {p['estado']}</p>" for p in pedidos_pendientes])}
    '''

@app.route('/crear_pedido', methods=['POST'])
@login_required
@requiere_rol(['admin'])
def crear_pedido():
    nuevo = {
        'id': len(pedidos) + 1,
        'direccion': request.form['direccion'],
        'cantidad': request.form['cantidad'] or 'Sin especificar',
        'chofer': request.form['chofer'],
        'estado': 'pendiente'
    }
    pedidos.append(nuevo)
    return redirect(url_for('panel_admin'))

@app.route('/panel_chofer')
@login_required
@requiere_rol(['chofer'])
def panel_chofer():
    mis_pedidos = [p for p in pedidos if p['chofer'] == session['username'] and p['estado'] == 'pendiente']
    return f'''
    <h2>Pedidos de {session['nombre']} 👷‍♂️</h2>
    <p><a href="/logout">Salir</a></p>

    <h3>Pendientes: {len(mis_pedidos)}</h3>
    {''.join([f"""
    <div style="border:1px solid #ccc; padding:10px; margin:10px;">
        <b>{p['direccion']}</b><br>
        Cantidad: {p['cantidad']}<br><br>
        <a href="https://waze.com/ul?q={p['direccion']}, Mexicali" target="_blank">
            <button>[Ir con Waze]</button>
        </a>
        <form action="/entregado/{p['id']}" method="post" style="display:inline;">
            <button type="submit">[Entregado]</button>
        </form>
    </div>
    """ for p in mis_pedidos]) if mis_pedidos else "<p>No tienes pedidos we, a descansar 🍺</p>"}
    '''

@app.route('/entregado/<int:pedido_id>', methods=['POST'])
@login_required
@requiere_rol(['chofer'])
def marcar_entregado(pedido_id):
    for p in pedidos:
        if p['id'] == pedido_id and p['chofer'] == session['username']:
            p['estado'] = 'entregado'
    return redirect(url_for('panel_chofer'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
