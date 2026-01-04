from flask import Flask, request, jsonify, render_template
import json
import pyotp
import os

app = Flask(__name__)

# Временная очередь для новых пользователей (пока их не заберет ноутбук)
pending_users = []
# Секретный ключ для связи с твоим ноутбуком (должен совпадать на обоих концах)
SHARED_SECRET = "SUPER_SECRET_TOKEN_123"

def load_users():
    if os.path.exists('users.json'):
        with open('users.json', 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_users(users):
    with open('users.json', 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

# --- ГЛАВНАЯ СТРАНИЦА (ДИЗАЙН) ---
@app.route('/')
def index():
    return render_template('index.html')

# --- API ДЛЯ РЕГИСТРАЦИИ ---
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"status": "error", "message": "Заполните все поля"}), 400

    # Генерируем секретный ключ 2FA
    totp_secret = pyotp.random_base32()

    # Складываем в "очередь", чтобы ноутбук мог это скачать
    pending_users.append({
        "username": username,
        "password": password,
        "totp_secret": totp_secret
    })

    # Сохраняем на сайте ТОЛЬКО секрет (для генерации кодов в браузере)
    # Пароль на сайте НЕ храним!
    users = load_users()
    users[username] = {"totp_secret": totp_secret}
    save_users(users)

    return jsonify({"status": "ok", "message": "Регистрация успешна! Данные передаются на хост."})

# --- РУЧКА ДЛЯ НОУТБУКА (ЗАБРАТЬ НОВЫХ ЮЗЕРОВ) ---
@app.route('/api/get_pending', methods=['GET'])
def get_pending():
    # Проверка: только твой ноут с правильным токеном может забрать данные
    token = request.headers.get('X-Auth-Token')
    if token != SHARED_SECRET:
        return jsonify({"status": "error", "message": "Forbidden"}), 403
    
    global pending_users
    # Копируем список, очищаем оригинал и отдаем данные ноутбуку
    data = list(pending_users)
    pending_users.clear()
    return jsonify(data)

# --- API ДЛЯ ПОЛУЧЕНИЯ ТЕКУЩЕГО КОДА 2FA ---
@app.route('/api/get_2fa/<username>')
def get_2fa(username):
    users = load_users()
    user = users.get(username)
    if user:
        totp = pyotp.TOTP(user['totp_secret'])
        return jsonify({"status": "ok", "code": totp.now()})
    return jsonify({"status": "error", "message": "Пользователь не найден"}), 404

if __name__ == '__main__':
    # На Render порт задается автоматически, 10000 - стандарт
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
