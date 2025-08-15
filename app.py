import sqlite3
import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime
import uuid

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Database setup
def init_db():
    db_path = 'farmlink.db'
    try:
        with sqlite3.connect(db_path) as conn:
            print("Connected to database successfully!")
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS crops (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    status TEXT NOT NULL,
                    note TEXT,
                    created_at TIMESTAMP
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    buyer TEXT NOT NULL,
                    product TEXT NOT NULL,
                    qty REAL NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP
                )
            ''')
            conn.commit()
            print("Tables created successfully!")
    except sqlite3.DatabaseError as e:
        print(f"Database error: {e}")
        raise
    except Exception as e:
        print(f"Error: {e}")
        raise


# Utility to generate unique IDs
def generate_id(prefix=''):
    return f"{prefix}{uuid.uuid4().hex[:10]}"

# Initialize database
init_db()

# ---------------- HTML Routes ---------------- #
@app.route('/')
def index():
    return render_template('main.html')  # loads templates/main.html

@app.route('/main.html')
def main_page():
    return render_template('main.html')

# ---------------- API Endpoints ---------------- #

# Crops endpoints
@app.route('/api/crops', methods=['GET'])
def get_crops():
    try:
        with sqlite3.connect('farmlink.db') as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('SELECT * FROM crops')
            crops = [dict(row) for row in c.fetchall()]
        return jsonify(crops), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/crops', methods=['POST'])
def add_crop():
    try:
        data = request.get_json()
        if not all(key in data for key in ['name', 'quantity', 'price']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        crop = {
            'id': generate_id('crop_'),
            'name': data['name'],
            'quantity': float(data['quantity']),
            'price': float(data['price']),
            'status': data.get('status', 'Available'),
            'note': data.get('note', ''),
            'created_at': datetime.utcnow()
        }
        
        with sqlite3.connect('farmlink.db') as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO crops (id, name, quantity, price, status, note, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (crop['id'], crop['name'], crop['quantity'], crop['price'], crop['status'], crop['note'], crop['created_at']))
            conn.commit()
        
        return jsonify(crop), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/crops/<id>', methods=['PUT'])
def update_crop(id):
    try:
        data = request.get_json()
        with sqlite3.connect('farmlink.db') as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM crops WHERE id = ?', (id,))
            if not c.fetchone():
                return jsonify({'error': 'Crop not found'}), 404
            
            update_fields = {k: v for k, v in data.items() if k in ['name', 'quantity', 'price', 'status', 'note']}
            if not update_fields:
                return jsonify({'error': 'No valid fields to update'}), 400
                
            query = 'UPDATE crops SET ' + ', '.join(f'{k} = ?' for k in update_fields.keys()) + ' WHERE id = ?'
            c.execute(query, list(update_fields.values()) + [id])
            conn.commit()
            
            c.execute('SELECT * FROM crops WHERE id = ?', (id,))
            crop = dict(c.fetchone())
            return jsonify(crop), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/crops/<id>', methods=['DELETE'])
def delete_crop(id):
    try:
        with sqlite3.connect('farmlink.db') as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM crops WHERE id = ?', (id,))
            if not c.fetchone():
                return jsonify({'error': 'Crop not found'}), 404
                
            c.execute('DELETE FROM crops WHERE id = ?', (id,))
            conn.commit()
        return jsonify({'message': 'Crop deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Orders endpoints
@app.route('/api/orders', methods=['GET'])
def get_orders():
    try:
        with sqlite3.connect('farmlink.db') as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('SELECT * FROM orders')
            orders = [dict(row) for row in c.fetchall()]
        return jsonify(orders), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders', methods=['POST'])
def add_order():
    try:
        data = request.get_json()
        if not all(key in data for key in ['buyer', 'product', 'qty']):
            return jsonify({'error': 'Missing required fields'}), 400
            
        order = {
            'id': generate_id('ord_'),
            'buyer': data['buyer'],
            'product': data['product'],
            'qty': float(data['qty']),
            'status': data.get('status', 'Received'),
            'created_at': datetime.utcnow()
        }
        
        with sqlite3.connect('farmlink.db') as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO orders (id, buyer, product, qty, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (order['id'], order['buyer'], order['product'], order['qty'], order['status'], order['created_at']))
            conn.commit()
            
        return jsonify(order), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders/<id>', methods=['PUT'])
def update_order(id):
    try:
        data = request.get_json()
        with sqlite3.connect('farmlink.db') as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM orders WHERE id = ?', (id,))
            if not c.fetchone():
                return jsonify({'error': 'Order not found'}), 404
                
            update_fields = {k: v for k, v in data.items() if k in ['buyer', 'product', 'qty', 'status']}
            if not update_fields:
                return jsonify({'error': 'No valid fields to update'}), 400
                
            query = 'UPDATE orders SET ' + ', '.join(f'{k} = ?' for k in update_fields.keys()) + ' WHERE id = ?'
            c.execute(query, list(update_fields.values()) + [id])
            conn.commit()
            
            c.execute('SELECT * FROM orders WHERE id = ?', (id,))
            order = dict(c.fetchone())
            return jsonify(order), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders/<id>', methods=['DELETE'])
def delete_order(id):
    try:
        with sqlite3.connect('farmlink.db') as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM orders WHERE id = ?', (id,))
            if not c.fetchone():
                return jsonify({'error': 'Order not found'}), 404
                
            c.execute('DELETE FROM orders WHERE id = ?', (id,))
            conn.commit()
        return jsonify({'message': 'Order deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Sample data endpoint
@app.route('/api/sample-data', methods=['POST'])
def import_sample_data():
    try:
        with sqlite3.connect('farmlink.db') as conn:
            c = conn.cursor()
            sample_crops = [
                (generate_id('crop_'), 'Tomato', 500, 45, 'Available', 'Organic', datetime.utcnow()),
                (generate_id('crop_'), 'Bell Pepper', 200, 85, 'Available', '', datetime.utcnow()),
                (generate_id('crop_'), 'Basmati Rice', 1000, 120, 'Available', 'Premium', datetime.utcnow())
            ]
            sample_orders = [
                (generate_id('ord_'), 'ABC Food', 'Tomato', 100, 'Received', datetime.utcnow()),
                (generate_id('ord_'), 'Spice Traders', 'Basmati Rice', 50, 'Processing', datetime.utcnow())
            ]
            
            c.executemany('''
                INSERT INTO crops (id, name, quantity, price, status, note, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', sample_crops)
            c.executemany('''
                INSERT INTO orders (id, buyer, product, qty, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', sample_orders)
            conn.commit()
            
        return jsonify({'message': 'Sample data imported'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Run app
if __name__ == '__main__':
    app.run(debug=True, port=5001)
