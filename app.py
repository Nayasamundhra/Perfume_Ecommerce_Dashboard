from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import subprocess
import os
import binascii
from datetime import datetime
import pytz 
from functools import wraps

app = Flask(__name__)
CORS(app)
app.secret_key = binascii.hexlify(os.urandom(24)).decode()

# MySQL Configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Nayasa!123',  # Keep original password
    'database': 'perfume_dash',
    'pool_name': 'perfume_dash_pool',
    'pool_size': 5
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

# Helper Functions
def get_user_id():
    return session.get('user_id', 1)  # Default to user ID 1 if not logged in

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or session.get('user_type') != 'admin':
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# Customer required decorator
def customer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or session.get('user_type') != 'customer':
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# Authentication Routes
@app.route('/')
def index():
    return redirect(url_for('login_page'))

@app.route('/login_page')
def login_page():
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        # Check if the credentials match the admin credentials
        if email == "admin@admin" and password == "123123123":
            session['logged_in'] = True
            session['user_type'] = 'admin'
            session['user_id'] = 0  # Admin user_id
            return jsonify({'redirect': '/admin/dashboard'})
        
        # For other users, check against the database
        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        try:
            # Check if user exists in the database
            cursor.execute("SELECT user_id, name, email, password FROM sign_det WHERE email = %s", (email,))
            user = cursor.fetchone()
            
            if user and user['password'] == password:  # Note: Should use password hashing instead of plain text
                session['logged_in'] = True
                session['user_type'] = 'customer'
                session['user_id'] = user['user_id']
                return jsonify({'redirect': '/customer/home'})
            else:
                return jsonify({'error': 'Invalid credentials. Please sign up first.'}), 401
                
        except mysql.connector.Error as err:
            return jsonify({'error': f'Database error: {str(err)}'}), 500
        finally:
            cursor.close()
            conn.close()

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('user_type', None)
    session.pop('user_id', None)
    return redirect(url_for('login_page'))

@app.route('/sign_up')
def sign_up():
    return render_template('sign_up.html')


@app.route('/sign_up', methods=['POST'])
def sign_up_submit():
    if request.method == 'POST':
        data = request.json
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')  # Password stored as plain text

        # Input validation
        if not all([name, email, password]):
            return jsonify({'error': 'All fields are required'}), 400

        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        try:
            # Check if user already exists
            cursor.execute("SELECT * FROM sign_det WHERE email = %s", (email,))
            if cursor.fetchone():
                return jsonify({'error': 'Email already registered'}), 409

            # Insert the new user with plain text password
            cursor.execute(
                "INSERT INTO sign_det (name, email, password) VALUES (%s, %s, %s)",
                (name, email, password)  # Password stored as plain text
            )
            conn.commit()
            
            # Get the new user's ID
            user_id = cursor.lastrowid
            
            # Log the user in
            session['logged_in'] = True
            session['user_type'] = 'customer'
            session['user_id'] = user_id

            return jsonify({'success': True, 'redirect': '/customer/home'})
            
        except mysql.connector.Error as err:
            conn.rollback()
            return jsonify({'error': f'Database error: {str(err)}'}), 500
        finally:
            cursor.close()
            conn.close()

# Admin Dashboard Routes
@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    if conn is None:
        return render_template('admin/index.html', error="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT COUNT(*) as order_count FROM orders')
    orders_count = cursor.fetchone()

    cursor.execute('SELECT COUNT(*) as perfume_count FROM perfume')
    perfume_count = cursor.fetchone()

    cursor.execute('SELECT SUM(sales_amount) as total_sales FROM sales_data')
    total_sales = cursor.fetchone()

    cursor.close()
    conn.close()
    
    return render_template('admin/index.html', 
                           orders_count=orders_count, 
                           perfume_count=perfume_count, 
                           total_sales=total_sales)

@app.route('/admin/inventory')
@login_required
@admin_required
def admin_inventory():
    return render_template('admin/inventory.html')

@app.route('/admin/order')
@login_required
@admin_required
def admin_order():
    return render_template('admin/order.html')

@app.route('/admin/supplier')
@login_required
@admin_required
def admin_supplier():
    return render_template('admin/supplier.html')

@app.route('/admin/analytics')
@login_required
@admin_required
def admin_analytics():
    return render_template('admin/analytics.html')

@app.route('/admin/customer')
@login_required
@admin_required
def admin_customer():
    return render_template('admin/customer.html')

@app.route('/admin/discounts')
@login_required
@admin_required
def admin_discounts():
    return render_template('admin/discounts.html')

@app.route('/admin/manage_perfume')
@login_required
@admin_required
def admin_manage_perfume():
    return render_template('admin/manage_perfume.html')

# Customer Dashboard Routes
@app.route('/customer/home')
@login_required
@customer_required
def customer_home():
    return render_template('customer/Home.html')


@app.route('/customer/order-history')
@login_required
@customer_required
def customer_order_history():
    return render_template('customer/order-history.html')

@app.route('/customer/profile')
@login_required
@customer_required
def customer_profile():
    return render_template('customer/profile.html')

@app.route('/customer/feedback')
@login_required
@customer_required
def customer_feedback():
    return render_template('customer/feedback.html')

@app.route('/customer/checkout')
@login_required
@customer_required
def customer_checkout():
    return render_template('customer/checkout.html')

@app.route('/customer/cart')
@login_required
@customer_required
def customer_cart():
    return render_template('customer/cart.html')

# Integrating functionality from the second app.py file
@app.route('/run_tests')
def run_tests():
    try:
        # Run the test script
        result = subprocess.run(["python", "test_dashboard.py"], capture_output=True, text=True)
        return f"<pre>Test Output:\n{result.stdout}\n{result.stderr}</pre>"
    except Exception as e:
        return f"Error running tests: {str(e)}"

@app.route('/best_selling_perfume', methods=['GET'])
def best_selling_perfume():
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor()
        # Query to find the best-selling perfume
        query = """
            SELECT 
                product_name, 
                SUM(quantity) AS total_quantity 
            FROM 
                orders 
            GROUP BY 
                product_name 
            ORDER BY 
                total_quantity DESC 
            LIMIT 1;
        """
        cursor.execute(query)
        result = cursor.fetchone()  # Fetch the top result

        if result:
            best_selling = {
                'perfume_name': result[0],  # product_name
                'total_quantity': result[1]  # total_quantity
            }
            return jsonify(best_selling)
        else:
            return jsonify({'error': 'No orders found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        if conn:
            conn.close()

    

@app.route('/stock_alerts', methods=['GET'])
def stock_alerts():
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor(dictionary=True)
    
    try:
        query = '''
            SELECT perfume_name, stock_level
            FROM perfume
            WHERE stock_level < 10
        '''
        cursor.execute(query)
        low_stock_perfumes = cursor.fetchall()
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

    return jsonify(low_stock_perfumes)

@app.route('/customer_stats')
def customer_stats():
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500

    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM users")
    total_customers = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM orders WHERE status='Delivered'")
    delivered_orders = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM orders WHERE status='Pending'")
    pending_orders = cur.fetchone()[0]

    cur.close()
    conn.close()

    return jsonify({
        'total_customers': total_customers,
        'delivered_orders': delivered_orders,
        'pending_orders': pending_orders
    })

@app.route('/sales_data_overview', methods=['GET'])
def get_sales_data_overview():
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute('SELECT month_name, sales_amount FROM sales_data ORDER BY sale_id ASC')
        sales_data = cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"SQL Error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

    return jsonify(sales_data)

@app.route('/customer_growth', methods=['GET'])
def customer_growth():
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor(dictionary=True)
    
    try:
        # Fetch customer count per month
        cursor.execute("SELECT month_name, SUM(sales_amount) FROM sales_data GROUP BY month_name")
        customer_data = cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"SQL Error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

    return jsonify(customer_data)

@app.route('/order_distribution', methods=['GET'])
def order_distribution():
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor(dictionary=True)

    try:
        # Fetch order count based on status
        cursor.execute('''
            SELECT 
                SUM(CASE WHEN status = 'Delivered' THEN 1 ELSE 0 END) AS delivered,
                SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END) AS cancelled
            FROM orders
        ''')
        order_data = cursor.fetchone()
    except mysql.connector.Error as err:
        print(f"SQL Error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

    return jsonify(order_data)

# Order management endpoints
@app.route('/orders', methods=['GET'])
def get_orders():
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM orders')
    orders = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify(orders)

@app.route('/delete_order/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    cursor.execute('DELETE FROM orders WHERE order_id = %s', (order_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'message': 'Order deleted successfully'})

# Perfume management endpoints
@app.route('/get_perfume', methods=['GET'])
def get_perfume():
    conn = get_db_connection()
    if conn is None:
        print("Database connection failed")
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute('SELECT perfume.perfume_id, perfume.perfume_name, brand.brand_name, perfume.price, perfume.stock_level, perfume.category from perfume inner join brand on perfume.brand_id=brand.brand_id')
        perfume = cursor.fetchall()
        print("Fetched Perfumes:", perfume)
    except mysql.connector.Error as err:
        print(f"SQL Error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

    return jsonify(perfume)

@app.route('/add_perfume', methods=['POST'])
def add_perfume():
        data = request.json
        if not data:
            return jsonify({"error": "No data received"}), 400
        
        perfume_id = data.get('perfume_id')
        perfume_name = data.get('perfume_name')
        brand_name = data.get('brand_name')
        price = data.get('price')
        stock_level=data.get('stock_level')
        category = data.get('category')
        description =data.get('description')
        image=data.get('image')

        if not all([perfume_id, perfume_name, brand_name, price, stock_level, category,description,image]):
            return jsonify({'error': 'Missing required fields'}), 400

        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()

        # Ensure brand exists
        cursor.execute("SELECT brand_id FROM brand WHERE brand_name = %s", (brand_name,))
        brand = cursor.fetchone()

        if not brand:
            cursor.execute("INSERT INTO brand (brand_name) VALUES (%s)", (brand_name,))
            conn.commit()
            brand_id = cursor.lastrowid  # Get new brand_id
        else:
            brand_id = brand[0]

        # Insert the perfume with manual perfume_id
        query = """
            INSERT INTO perfume (perfume_id, perfume_name, brand_id, price, stock_level, category,description,image_url) 
            VALUES (%s, %s, %s, %s, %s, %s,%s,%s)
        """
        try:
            cursor.execute(query, (perfume_id, perfume_name, brand_id, price, stock_level, category,description,image))
            conn.commit()
        except mysql.connector.IntegrityError:
            return jsonify({'error': 'Perfume ID already exists!'}), 400
        
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Perfume added successfully!'})

@app.route('/api/perfumes/<int:perfume_id>', methods=['PUT'])
def update_perfume(perfume_id):
    data = request.json
    perfume_name = data.get('perfume_name')
    brand_name = data.get('brand_name')
    price = data.get('price')
    stock_level = data.get('stock_level')
    category = data.get('category')

    if not all([perfume_name, brand_name, price, stock_level, category]):
        return jsonify({'error': 'Missing required fields'}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()

    # Ensure brand exists
    cursor.execute("SELECT brand_id FROM brand WHERE brand_name = %s", (brand_name,))
    brand = cursor.fetchone()

    if not brand:
        cursor.execute("INSERT INTO brand (brand_name) VALUES (%s)", (brand_name,))
        conn.commit()
        brand_id = cursor.lastrowid  # Get new brand_id
    else:
        brand_id = brand[0]

    # Update the perfume details
    query = """
        UPDATE perfume 
        SET perfume_name = %s, brand_id = %s, price = %s, stock_level = %s, category = %s 
        WHERE perfume_id = %s
    """
    cursor.execute(query, (perfume_name, brand_id, price, stock_level, category, perfume_id))
    conn.commit()

    if cursor.rowcount == 0:
        return jsonify({"error": "Perfume not found"}), 404

    cursor.close()
    conn.close()

    return jsonify({'message': 'Perfume updated successfully'})

@app.route('/api/perfumes/<int:perfume_id>', methods=['DELETE'])
def delete_perfume(perfume_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()

    # Check if perfume exists
    cursor.execute("SELECT * FROM perfume WHERE perfume_id = %s", (perfume_id,))
    perfume = cursor.fetchone()
    if not perfume:
        return jsonify({"error": "Perfume not found"}), 404

    # Delete the perfume
    cursor.execute("DELETE FROM perfume WHERE perfume_id = %s", (perfume_id,))
    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"message": "Perfume deleted successfully!"})

# API Endpoints for Customer-Facing Features
# API Endpoints for Customer-Facing Features
@app.route('/api/customer/perfumes', methods=['GET'])
def get_customer_perfumes():
    category = request.args.get('category', 'all')
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            if category == "all":
                cursor.execute("SELECT * FROM perfume")
            else:
                cursor.execute("SELECT * FROM perfume WHERE category = %s", (category,))
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

@app.route('/api/customer/perfumes/<int:perfume_id>', methods=['GET'])
def get_customer_perfume_by_id(perfume_id):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM perfume WHERE perfume_id = %s", (perfume_id,))
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

@app.route('/api/customer/add-to-cart', methods=['POST'])
def add_to_cart():
    data = request.json
    user_id = get_user_id()
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

@app.route('/api/customer/cart', methods=['GET'])
def get_customer_cart():
    user_id = get_user_id()
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT c.cart_id, p.perfume_id, p.perfume_name AS name, p.price, p.image_url, c.quantity, (p.price * c.quantity) AS total_price "
                "FROM cart c JOIN perfume p ON c.perfume_id = p.perfume_id WHERE c.user_id = %s",
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

@app.route('/api/customer/order-history', methods=['GET'])
def get_customer_order_history():
    user_id = get_user_id()
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Fetch orders for the current user
            cursor.execute("""
                SELECT order_id, customer_name, product_name, quantity, 
                       total_amt, status, order_date, payment_method, shipping_address
                FROM orders
                WHERE user_id = %s
            """, (user_id,))
            
            orders = cursor.fetchall()
            cursor.close()
            conn.close()
            
            # Convert Decimal objects to float for JSON serialization
            for order in orders:
                if 'total_amt' in order:
                    order['total_amt'] = float(order['total_amt'])
            
            return jsonify(orders)
        except Error as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Database connection failed"}), 500    

@app.route('/api/customer/update-cart/<int:cart_id>', methods=['PUT'])
def update_customer_cart(cart_id):
    data = request.json
    quantity = data.get('quantity')
    user_id = get_user_id()
    
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

@app.route('/api/customer/remove-from-cart/<int:cart_id>', methods=['DELETE'])
def remove_from_customer_cart(cart_id):
    user_id = get_user_id()
    
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

@app.route('/api/customer/cart-count', methods=['GET'])
def get_customer_cart_count():
    user_id = get_user_id()
    
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

@app.route('/api/customer/place-order', methods=['POST'])
def place_customer_order():
    data = request.json
    user_id = get_user_id()
    shipping_address = data.get('shipping_address')
    payment_method = data.get('payment_method')
    customer_name = data.get('customer_name')
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # Get cart items
            cursor.execute(
                """SELECT c.cart_id, p.perfume_id, p.perfume_name, p.price, c.quantity, 
                (p.price * c.quantity) AS total_price 
                FROM cart c JOIN perfume p ON c.perfume_id = p.perfume_id 
                WHERE c.user_id = %s""",
                (user_id,)
            )
            cart_items = cursor.fetchall()
            
            if not cart_items:
                return jsonify({"error": "Cart is empty"}), 400
        
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S') 
            
            # Process each item in cart
            for item in cart_items:
                # Insert order for each item
                cursor.execute(
                    """INSERT INTO orders 
                    (customer_name, product_name, quantity, total_amt, status, payment_method, shipping_address, user_id) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (customer_name, item['perfume_name'], item['quantity'], item['total_price'], 
                     'Pending', payment_method, shipping_address, user_id)
                )
            
            # Clear the user's cart
            cursor.execute("DELETE FROM cart WHERE user_id = %s", (user_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({"message": "Order placed successfully"}), 201
        except Error as e:
            conn.rollback()
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Database connection failed"}), 500

# Analytics endpoints
@app.route('/sales_data', methods=['GET'])
def get_sales_data():
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute('SELECT month_name, sales_amount FROM sales_data ORDER BY sale_id ASC')
        sales_data = cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"SQL Error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

    return jsonify(sales_data)

# Supplier management endpoints
@app.route('/get_supplier', methods=['GET'])
def get_supplier():
    conn = get_db_connection()
    if conn is None:
        print("Database connection failed")
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute('SELECT * FROM supplier')
        supplier = cursor.fetchall()
        print("Fetched suppliers:", supplier)
    except mysql.connector.Error as err:
        print(f"SQL Error: {err}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

    return jsonify(supplier)

@app.route('/add_supplier', methods=['POST'])
def add_supplier():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data received"}), 400
        
        supplier_id = data.get('supplier_id')
        supplier_name = data.get('supplier_name')
        contact = data.get('contact')
        pending_payment = data.get('pending_payment')
        status = data.get('status')

        if not all([supplier_id, supplier_name, contact, pending_payment, status]):
            return jsonify({"error": "Missing required fields"}), 400

        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        query = "INSERT INTO supplier (supplier_id, supplier_name, contact, pending_payment, status) VALUES (%s, %s, %s, %s, %s)"
        values = (supplier_id, supplier_name, contact, pending_payment, status)

        cursor.execute(query, values)
        conn.commit()
        
        return jsonify({"message": "Supplier added successfully!"})
    
    except mysql.connector.Error as db_err:
        return jsonify({"error": f"MySQL Error: {db_err}"}), 500
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/edit_supplier/<int:supplier_id>', methods=['PUT'])
def edit_supplier(supplier_id):
    data = request.json
    
    if not data:
        return jsonify({"error": "No data received"}), 400

    supplier_name = data.get('supplier_name')
    contact = data.get('contact')
    pending_payment = data.get('pending_payment')
    status = data.get('status')

    if not all([supplier_name, contact, pending_payment, status]):
        return jsonify({"error": "Missing required fields"}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor()
    
    try:
        query = '''
            UPDATE supplier
            SET supplier_name = %s, contact = %s, pending_payment = %s, status = %s
            WHERE supplier_id = %s
        '''
        values = (supplier_name, contact, pending_payment, status, supplier_id)
        cursor.execute(query, values)
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({"error": "Supplier not found"}), 404
        
        return jsonify({'message': 'Supplier updated successfully'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        cursor.close()
        conn.close()

@app.route('/get_supplier/<int:id>', methods=['GET'])
def get_supplier_by_id(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM supplier WHERE supplier_id = %s", (id,))
    supplier = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if supplier:
        return jsonify(supplier)
    return jsonify({"error": "Supplier not found"}), 404

@app.route('/delete_supplier/<int:id>', methods=['DELETE'])
def delete_supplier(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM supplier WHERE supplier_id = %s", (id,))
    supplier = cursor.fetchone()
    
    if not supplier:
        return jsonify({"error": "Supplier not found"}), 404
    
    cursor.execute("DELETE FROM supplier WHERE supplier_id = %s", (id,))
    conn.commit()
    
    return jsonify({"message": "Supplier deleted successfully!"})
if __name__ == '__main__':
    app.run(debug=True)