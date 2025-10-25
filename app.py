from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from database import db, MenuItem, Order
import json
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'your_database_uri'  # 替換為你的 Render PostgreSQL URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'  # 替換為你的密鑰
db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/waiter')
def waiter():
    return render_template('waiter.html')

@app.route('/kitchen')
def kitchen():
    return render_template('kitchen.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/api/menu', methods=['GET'])
def get_menu():
    try:
        menu_items = MenuItem.query.filter_by(available=1).all()
        print(f"Retrieved {len(menu_items)} menu items")
        return jsonify([item.to_dict() for item in menu_items])
    except Exception as e:
        print(f"Menu query error: {str(e)}")
        return jsonify({'error': '無法獲取菜單'}), 500

@app.route('/api/orders', methods=['GET'])
def get_orders():
    try:
        filter_status = request.args.get('filter', 'all')
        print(f"Fetching orders with filter: {filter_status}")
        query = Order.query
        if filter_status != 'all':
            query = query.filter_by(status=filter_status)
        orders = query.order_by(Order.created_at.desc()).all()
        print(f"Retrieved {len(orders)} orders")
        return jsonify([order.to_dict() for order in orders])
    except Exception as e:
        print(f"Order query error: {str(e)}")
        return jsonify({'error': '無法獲取訂單'}), 500

@app.route('/api/orders', methods=['POST'])
def create_order():
    try:
        data = request.get_json()
        items = data.get('items', [])
        notes = data.get('notes', '')
        total_amount = sum(item['price'] * item['quantity'] for item in items)
        
        order_number = datetime.now().strftime('%Y%m%d%H%M%S')
        order = Order(
            order_number=order_number,
            items=json.dumps(items),
            total_amount=total_amount,
            status='pending',
            notes=notes
        )
        db.session.add(order)
        db.session.commit()
        
        print(f"New order created: {order.order_number}")
        socketio.emit('new_order', order.to_dict())
        return jsonify({'message': '訂單創建成功', 'order': order.to_dict()}), 201
    except Exception as e:
        print(f"Order creation error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': '無法創建訂單'}), 500

@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    try:
        data = request.get_json()
        new_status = data.get('status')
        if not new_status:
            return jsonify({'error': '未提供狀態'}), 400
        
        order = Order.query.get_or_404(order_id)
        order.status = new_status
        order.updated_at = datetime.utcnow()
        db.session.commit()
        
        print(f"Order {order.order_number} status updated to {new_status}")
        socketio.emit('order_updated', order.to_dict())
        return jsonify(order.to_dict())
    except Exception as e:
        print(f"Order status update error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': '無法更新訂單狀態'}), 500

@app.route('/api/orders/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    try:
        order = Order.query.get_or_404(order_id)
        db.session.delete(order)
        db.session.commit()
        
        print(f"Order {order.order_number} deleted")
        socketio.emit('order_deleted', {'order_id': order_id})
        return jsonify({'message': '訂單已刪除'})
    except Exception as e:
        print(f"Order deletion error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': '無法刪除訂單'}), 500

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    socketio.run(app, debug=True)
