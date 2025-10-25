import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)  # 隨機生成安全密鑰

# 資料庫配置
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///orders.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_size': 5,
    'max_overflow': 10,
    'pool_timeout': 30
}

# 初始化 SocketIO 使用 gevent
socketio = SocketIO(app, async_mode='gevent')

# 初始化資料庫
db = SQLAlchemy(app)

# 導入模型（在 db 初始化後）
from database import MenuItem, Order

# 路由定義
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/waiter")
def waiter():
    return render_template("waiter.html")

@app.route("/kitchen")
def kitchen():
    return render_template("kitchen.html")

@app.route("/admin", methods=["GET", "POST"])
def admin_menu():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add_or_update":
            name = request.form.get("name")
            price = float(request.form.get("price"))
            description = request.form.get("description")
            category = request.form.get("category")
            new_item = MenuItem(name=name, price=price, description=description, category=category)
            db.session.add(new_item)
            db.session.commit()
            return redirect(url_for("admin_menu"))
        elif action == "delete":
            item_id = request.form.get("item_id")
            item = MenuItem.query.get(item_id)
            if item:
                db.session.delete(item)
                db.session.commit()
            return redirect(url_for("admin_menu"))
    
    items = MenuItem.query.order_by(MenuItem.category, MenuItem.id).all()
    menu_items = [item.to_dict() for item in items]
    return render_template("admin.html", menu_items=menu_items)

@app.route("/api/menu", methods=["GET"])
def get_menu():
    try:
        items = MenuItem.query.filter_by(available=1).order_by(MenuItem.category, MenuItem.name).all()
        menu = [item.to_dict() for item in items]
        return jsonify(menu)
    except Exception as e:
        print(f"Menu query error: {e}")
        return jsonify([]), 500

@app.route("/api/orders", methods=["GET", "POST"])
def manage_orders():
    if request.method == "POST":
        try:
            data = request.get_json()
            if not data or "items" not in data or not data["items"]:
                return jsonify({"error": "訂單內容為空"}), 400

            order_number = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            items_json = json.dumps(data["items"])
            total_amount = sum(item["price"] * item["quantity"] for item in data["items"])

            new_order = Order(
                order_number=order_number,
                items=items_json,
                total_amount=total_amount,
                status="pending",
                notes=data.get("notes", "")
            )
            db.session.add(new_order)
            db.session.commit()

            socketio.emit("new_order", new_order.to_dict(), broadcast=True)
            return jsonify({"message": "訂單已送出", "order": new_order.to_dict()}), 201
        except Exception as e:
            db.session.rollback()
            print(f"Order creation error: {e}")
            return jsonify({"error": "送出訂單失敗，請稍後重試"}), 500
    elif request.method == "GET":
        try:
            filter_status = request.args.get("filter", "all")
            if filter_status == "all":
                orders = Order.query.all()
            else:
                orders = Order.query.filter_by(status=filter_status).all()
            return jsonify([order.to_dict() for order in orders])
        except Exception as e:
            print(f"Order query error: {e}")
            return jsonify([]), 500

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=10000)
