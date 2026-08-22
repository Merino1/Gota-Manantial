from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.secret_key = 'cambia_esto_por_algo_secreto'

# Base de datos
DB = 'gota.db'

# Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, nombre, rol):
        self.id = id
        self.username = username
        self.nombre = nombre
        self.rol = rol

@login_manager.user_loader
def load_user(user_id):
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("SELECT id, username, nombre, rol FROM usuarios WHERE id =?", (user_id,))
    user = cur.fetchone()
    con.close()
    if user:
        return User(user[0], user[1], user[2], user[3])
    return None

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        contra = request.form['contra']
        con = sqlite3.connect(DB)
        cur = con.cursor()
        cur.execute("SELECT id, username, password, nombre, rol FROM usuarios WHERE username =?", (usuario,))
        user = cur.fetchone()
        con.close()
        if user and check_password_hash(user[2], contra):
            user_obj = User(user[0], user[1], user[3], user[4])
            login_user(user_obj)
            return redirect(url_for('panel'))
        return "Usuario o contra mal"
    return '''
    <h1>Login Gota Manantial</h1>
    <form method="post">
      Usuario: <input name="usuario"><br><br>
      Contra: <input name="contra" type="password"><br><br>
      <button type="submit">Entrar</button>
    </form>
    '''

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/panel')
@login_required
def panel():
    return f'''
    <h1>Panel - Bienvenido {current_user.nombre}</h1>
    <p>Tu rol: {current_user.rol}</p>
    <a href="/agregar_personal">Agregar Personal</a><br><br>
    <a href="/logout">Cerrar Sesión</a>
    '''

@app.route('/agregar_personal', methods=['GET', 'POST'])
@login_required
def agregar_personal():
    if current_user.rol not in ['admin', 'dueño', 'sistemas']:
        return "No tienes permisos we"

    if request.method == 'POST':
        usuario = request.form['usuario']
        contra = generate_password_hash(request.form['contra'])
        nombre = request.form['nombre']
        rol = request.form['rol']
        email = request.form['correo']

        con = sqlite3.connect(DB)
        cur = con.cursor()
        cur.execute("INSERT INTO usuarios (username, password, nombre, rol, email) VALUES (?,?,?,?,?)",
                    (usuario, contra, nombre, rol, email))
        con.commit()
        con.close()
        return redirect(url_for('panel'))

    return '''
    <h1>Agregar Personal</h1>
    <form method="post">
      Nombre: <input name="nombre" required><br><br>
      Usuario: <input name="usuario" required><br><br>
      Contra: <input name="contra" type="password" required><br><br>
      Rol: <select name="rol" required>
        <option value="chofer">Chofer</option>
        <option value="admin">Admin</option>
        <option value="dueño">Dueño</option>
        <option value="sistemas">Sistemas</option>
      </select><br><br>
      Correo: <input name="correo" type="email" required><br><br>
      <button type="submit">Guardar</button>
    </form>
    <br><a href="/panel">Regresar al Panel</a>
    '''

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
