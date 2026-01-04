from flask import Flask, request, jsonify, render_template
import json
import pyotp
import os

app = Flask(__name__)

# Временная очередь для новых пользователей
pending_users = []
# Секретный ключ для связи с твоим ноутбуком
SHARED_SECRET = "SUPER_SECRET_TOKEN_123"

def load_users():
    if os.path.exists('users.json'):
        with open('users.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open('users.json', 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

@app.route('/')
def index():
    return "Сервер MyOC активен!"

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"status": "error", "message": "Заполните все поля"}), 400

    totp_secret = pyotp.random_base32()

    # Добавляем в очередь для ноутбука
    pending_users.append({
        "username": username,
        "password": password,
        "totp_secret": totp_secret
    })

    # Сохраняем на сайте только секрет для отображения кода 2FA
    users = load_users()
    users[username] = {"totp_secret": totp_secret}
    save_users(users)

    return jsonify({"status": "ok", "message": "Регистрация успешна! Ожидайте синхронизации с хостом."})

@app.route('/api/get_pending', methods=['GET'])
def get_pending():
    # Проверка безопасности: только твой ноут может забрать данные
    token = request.headers.get('X-Auth-Token')
    if token != SHARED_SECRET:
        return jsonify({"status": "error", "message": "Forbidden"}), 403
    
    global pending_users
    data = list(pending_users)
    pending_users.clear() # Очищаем очередь после выдачи
    return jsonify(data)

@app.route('/api/get_2fa/<username>')
def get_2fa(username):
    users = load_users()
    user = users.get(username)
    if user:
        totp = pyotp.TOTP(user['totp_secret'])
        return jsonify({"status": "ok", "code": totp.now()})
    return jsonify({"status": "error", "message": "User not found"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
