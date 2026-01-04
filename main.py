from flask import Flask, request, jsonify, render_template, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash
import pyotp
import json
import os

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = "cloudoc-super-key-fixed"  # Ключ для входа

DB_FILE = 'users.json'


def load_users():
    if not os.path.exists(DB_FILE): return {}
    try:
        with open(DB_FILE, 'r') as f:
            return json.loads(f.read().strip() or "{}")
    except:
        return {}


def save_users(users):
    with open(DB_FILE, 'w') as f: json.dump(users, f, indent=4)


# --- ГЛАВНАЯ ---
@app.route('/')
def index():
    if 'user' in session:
        username = session['user']
        users = load_users()
        user_data = users.get(username)
        # Если вошли — показываем Аккаунт
        return render_template('index.html', logged_in=True, username=username, secret=user_data.get('secret'))
    # Если нет — показываем Войти и Регистрацию
    return render_template('index.html', logged_in=False)


# --- РЕГИСТРАЦИЯ (ВЕРНУЛ) ---
@app.route('/register')
def register_page():
    return render_template('register.html')


@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.form
    username = data.get('username')
    password = data.get('password')

    users = load_users()
    if username in users: return "Этот логин занят!", 400

    secret = pyotp.random_base32()
    users[username] = {
        "password": generate_password_hash(password),
        "secret": secret
    }
    save_users(users)
    return render_template('success.html', secret=secret)


# --- ВХОД ---
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True) or request.form
    username = data.get('username')
    password = data.get('password')
    code = data.get('code')

    users = load_users()
    user = users.get(username)

    if not user or not check_password_hash(user.get('password', ''), password):
        return jsonify({"status": "error", "message": "Неверный логин или пароль"}), 401

    if pyotp.TOTP(user['secret']).verify(code):
        session['user'] = username
        return jsonify({"status": "success"})

    return jsonify({"status": "error", "message": "Неверный код 2FA"}), 401


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)