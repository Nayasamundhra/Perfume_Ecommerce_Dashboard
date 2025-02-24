from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import mysql.connector
from mysql.connector import Error
from flask_cors import CORS
import json
from datetime import datetime
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management
CORS(app)

# Database Configuration with connection pooling
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="12345678",
            database="scentova",
            pool_name="scentova_pool",
            pool_size=5
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# Simplified session handling - no login required
def get_user_id():
    # For demonstration, we'll use a fixed user ID if not in session
    return session.get('user_id', 1)  # Default to user ID 1 if not logged in

# Serve HTML Pages
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/cart")
def cart():
    return render_template("cart.html")  # Serve cart.html

@app.route("/profile")
def profile():
    return render_template("profile.html")  # Serve profile.html

@app.route("/feedback")
def feedback():
    return render_template("feedback.html")  # Serve feedback.html

@app.route("/checkout")
def checkout():
    return render_template("checkout.html")  # Serve checkout.html

@app.route("/order-history")
def order_history_page():
    return render_template("order-history.html")  # Serve order-history.html

# API Endpoints
@app.route('/api/perfumes', methods=['GET'])
def get_perfumes():
    category = request.args.get('category', 'all')
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            if category == "all":
                cursor.execute("SELECT * FROM perfumes")
            else:
                cursor.execute("SELECT * FROM perfumes WHERE category = %s", (category,))
            perfumes = cursor.fetchall()
            
            # Convert Decimal objects to float for JSON serialization
            for perfume in perfumes:
                if 'price' in perfume:
                    perfume['price'] = float(perfume['price'])
                    
            cursor.close()
            conn.close()
            return jsonify(perfumes)
        except Error as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Database connection failed"}), 500

@app.route('/api/perfumes/<int:perfume_id>', methods=['GET'])
def get_perfume(perfume_id):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM perfumes WHERE perfume_id = %s", (perfume_id,))
            perfume = cursor.fetchone()
            
            if perfume and 'price' in perfume:
                perfume['price'] = float(perfume['price'])
                
            cursor.close()
            conn.close()
            
            if perfume:
                return jsonify(perfume)
            return jsonify({"error": "Perfume not found"}), 404
        except Error as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Database connection failed"}), 500

@app.route('/api/add-to-cart', methods=['POST'])
def add_to_cart():
    data = request.json
    user_id = get_user_id()  # Use the simplified user_id getter
    perfume_id = data.get('perfume_id')
    quantity = data.get('quantity')
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Check if item already exists in cart
            cursor.execute(
                "SELECT cart_id, quantity FROM cart WHERE user_id = %s AND perfume_id = %s",
                (user_id, perfume_id)
            )
            existing_item = cursor.fetchone()
            
            if existing_item:
                # Update quantity if item exists
                new_quantity = existing_item[1] + quantity
                cursor.execute(
                    "UPDATE cart SET quantity = %s WHERE cart_id = %s",
                    (new_quantity, existing_item[0])
                )
            else:
                # Insert new item if it doesn't exist
                cursor.execute(
                    "INSERT INTO cart (user_id, perfume_id, quantity) VALUES (%s, %s, %s)",
                    (user_id, perfume_id, quantity)
                )
            
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({"message": "Item added to cart"}), 201
        except Error as e:
            conn.rollback()
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Database connection failed"}), 500

@app.route('/api/cart', methods=['GET'])
def get_cart():
    user_id = get_user_id()  # Use the simplified user_id getter
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT c.cart_id, p.perfume_id, p.name, p.price, p.image_url, c.quantity, (p.price * c.quantity) AS total_price "
                "FROM cart c JOIN perfumes p ON c.perfume_id = p.perfume_id WHERE c.user_id = %s",
                (user_id,)
            )
            cart_items = cursor.fetchall()
            cursor.close()
            conn.close()
            
            # Convert Decimal objects to float for JSON serialization
            for item in cart_items:
                if 'price' in item:
                    item['price'] = float(item['price'])
                if 'total_price' in item:
                    item['total_price'] = float(item['total_price'])
            
            return jsonify(cart_items)
        except Error as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Database connection failed"}), 500

@app.route('/api/order-history', methods=['GET'])
def get_order_history():
    user_id = get_user_id()  # Use the simplified user_id getter
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Fetch orders and their items
            cursor.execute("""
                SELECT o.order_id, o.order_date, o.shipping_address, o.payment_method, o.total_amount,
                       GROUP_CONCAT(CONCAT(p.name, ' x ', oi.quantity) SEPARATOR ', ') AS items
                FROM orders o
                JOIN order_items oi ON o.order_id = oi.order_id
                JOIN perfumes p ON oi.perfume_id = p.perfume_id
                WHERE o.user_id = %s
                GROUP BY o.order_id
            """, (user_id,))
            
            orders = cursor.fetchall()
            cursor.close()
            conn.close()
            
            # Convert Decimal objects to float for JSON serialization
            for order in orders:
                if 'total_amount' in order:
                    order['total_amount'] = float(order['total_amount'])
            
            return jsonify(orders)
        except Error as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Database connection failed"}), 500    

@app.route('/api/update-cart/<int:cart_id>', methods=['PUT'])
def update_cart(cart_id):
    data = request.json
    quantity = data.get('quantity')
    user_id = get_user_id()  # Use the simplified user_id getter
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Update the cart item
            cursor.execute(
                "UPDATE cart SET quantity = %s WHERE cart_id = %s AND user_id = %s",
                (quantity, cart_id, user_id)
            )
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({"message": "Cart updated"}), 200
        except Error as e:
            conn.rollback()
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Database connection failed"}), 500

@app.route('/api/remove-from-cart/<int:cart_id>', methods=['DELETE'])
def remove_from_cart(cart_id):
    user_id = get_user_id()  # Use the simplified user_id getter
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Remove the cart item
            cursor.execute("DELETE FROM cart WHERE cart_id = %s AND user_id = %s", (cart_id, user_id))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({"message": "Item removed from cart"}), 200
        except Error as e:
            conn.rollback()
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Database connection failed"}), 500

@app.route('/api/cart-count', methods=['GET'])
def get_cart_count():
    user_id = get_user_id()  # Use the simplified user_id getter
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT SUM(quantity) AS count FROM cart WHERE user_id = %s", 
                (user_id,)
            )
            result = cursor.fetchone()
            count = result[0] if result[0] is not None else 0
            cursor.close()
            conn.close()
            return jsonify({"count": count})
        except Error as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Database connection failed"}), 500

@app.route('/api/place-order', methods=['POST'])
def place_order():
    data = request.json
    user_id = get_user_id()  # Use the simplified user_id getter
    shipping_address = data.get('shipping_address')
    payment_method = data.get('payment_method')  # Get payment method from request
    total_amount = data.get('total_amount')
    items = data.get('items')

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Insert order into orders table
            cursor.execute(
                "INSERT INTO orders (user_id, shipping_address, payment_method, total_amount) VALUES (%s, %s, %s, %s)",
                (user_id, shipping_address, payment_method, total_amount)
            )
            order_id = cursor.lastrowid

            # Insert cart items into order_items table
            for item in items:
                cursor.execute(
                    "INSERT INTO order_items (order_id, perfume_id, quantity, price) VALUES (%s, %s, %s, %s)",
                    (order_id, item['perfume_id'], item['quantity'], item['price'])
                )

            # Clear the user's cart
            cursor.execute("DELETE FROM cart WHERE user_id = %s", (user_id,))

            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({"message": "Order placed successfully", "order_id": order_id}), 201
        except Error as e:
            conn.rollback()
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Database connection failed"}), 500
    

if __name__ == '__main__':
    app.run(debug=True)