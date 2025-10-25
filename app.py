from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import json
import os
from datetime import datetime
from database import init_db, db, MenuItem, Order  # 新增匯入

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SESSION_SECRET", "your-secret-key-here")
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# 初始化資料庫
init_db(app)

@app.route("/api/menu", methods=["GET"])
def get_menu():
    items = MenuItem.query.filter_by(available=1).order_by(MenuItem.category, MenuItem.name).all()
    menu = [item.to_dict() for item in items]
    return jsonify(menu)

@app.route("/api/orders", methods=["GET"])
def get_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    order_list = [order.to_dict() for order in orders]
    for order in order_list:
        order['items'] = json.loads(order['items'])
    return jsonify(order_list)

@app.route("/api/orders/pending", methods=["GET"])
def get_pending_orders():
    orders = Order.query.filter(Order.status != 'completed').order_by(Order.created_at.asc()).all()
    order_list = [order.to_dict() for order in orders]
    for order in order_list:
        order['items'] = json.loads(order['items'])
    return jsonify(order_list)

@app.route("/api/orders", methods=["POST"])
def create_order():
    data = request.json
    items = data.get("items", [])
    total_amount = data.get("total_amount", 0)
    notes = data.get("notes", "")

    # 生成訂單編號
    count = db.session.query(Order).count()
    order_number = f"ORD{datetime.now().strftime('%Y%m%d')}{count + 1:04d}"

    # 建立新訂單
    order = Order(
        order_number=order_number,
        items=json.dumps(items),
        total_amount=total_amount,
        status="pending",
        notes=notes
    )
    db.session.add(order)
    db.session.commit()

    order_data = order.to_dict()
    order_data['items'] = items  # 還原為列表

    socketio.emit("new_order", order_data)
    return jsonify(order_data), 201

@app.route("/api/orders/<int:order_id>/status", methods=["PUT"])
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    data = request.json
    new_status = data.get("status")

    if new_status not in ["pending", "received", "cooking", "ready", "completed"]:
        return jsonify({"error": "Invalid status"}), 400

    order.status = new_status
    db.session.commit()

    order_data = order.to_dict()
    order_data['items'] = json.loads(order_data['items'])

    socketio.emit("order_updated", order_data)
    return jsonify(order_data)

# 管理路由（/admin）更新
@app.route("/admin", methods=["GET", "POST"])
def admin_menu():
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "add_or_update":
            category = request.form["category"]
            name = request.form["name"]
            price = float(request.form["price"])
            description = request.form["description"]
            item_id = request.form.get("item_id")
            
            if item_id:
                # 修改
                item = MenuItem.query.get(item_id)
                if item:
                    item.category = category
                    item.name = name
                    item.price = price
                    item.description = description
                    item.available = 1
            else:
                # 新增
                item = MenuItem(category=category, name=name, price=price, description=description, available=1)
                db.session.add(item)
            
            db.session.commit()
        
        elif action == "delete":
            item_id = request.form["item_id"]
            item = MenuItem.query.get(item_id)
            if item:
                db.session.delete(item)
                db.session.commit()
        
        return redirect(url_for("admin_menu"))
    
    # GET：顯示菜單
    items = MenuItem.query.order_by(MenuItem.category, MenuItem.id).all()
    menu_items = [item.to_dict() for item in items]
    return render_template("admin.html", menu_items=menu_items)

# 其他路由（如 /, /waiter, /kitchen）保持不變

if __name__ == "__main__":
    socketio.run(app, host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "5000")), debug=True, allow_unsafe_werkzeug=True)
