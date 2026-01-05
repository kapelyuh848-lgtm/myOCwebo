from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# Секретный токен (ДОЛЖЕН СОВПАДАТЬ С ХОСТОМ)
SHARED_SECRET = "SUPER_SECRET_TOKEN_123"

# Временная база данных в оперативной памяти Сайта
users_db = {}
pending_registrations = []

@app.route('/')
def home():
    return f"MyOC Cloud Server. Users in memory: {len(users_db)}"

# МАРШРУТ: Регистрация нового юзера (например, через веб-форму)
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    if not data or 'username' not in data:
        return jsonify({"status": "error"}), 400
    
    # Добавляем в очередь, чтобы Хост мог забрать себе
    pending_registrations.append(data)
    # Сразу сохраняем в память сайта
    users_db[data['username']] = data
    return jsonify({"status": "success"}), 200

# МАРШРУТ: Хост забирает новых зарегистрированных
@app.route('/api/get_pending', methods=['GET'])
def get_pending():
    token = request.headers.get("X-Auth-Token")
    if token != SHARED_SECRET:
        return jsonify({"status": "forbidden"}), 403
    
    global pending_registrations
    data = pending_registrations[:]
    pending_registrations = [] # Очищаем очередь
    return jsonify(data), 200

# МАРШРУТ: Хост восстанавливает базу сайта (после рестарта Render)
@app.route('/api/sync/restore_users', methods=['POST'])
def restore_users():
    token = request.headers.get("X-Auth-Token")
    if token != SHARED_SECRET:
        return jsonify({"status": "forbidden"}), 403
    
    data = request.json
    if data:
        users_db.update(data)
        return jsonify({"status": "synced", "total": len(users_db)}), 200
    return jsonify({"status": "empty"}), 400

# МАРШРУТ: Логин из Rust-клиента (идет на сайт)
@app.route('/from_client/login', methods=['POST'])
def login():
    data = request.json
    u, p = data.get('username'), data.get('password')
    if u in users_db and users_db[u]['password'] == p:
        return jsonify({
            "status": "success", 
            "totp_secret": users_db[u].get('totp_secret', "")
        }), 200
    return jsonify({"status": "fail"}), 401

if __name__ == '__main__':
    # На Render порт задается через переменную окружения
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
