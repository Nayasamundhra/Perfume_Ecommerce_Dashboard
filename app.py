from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import mysql.connector

app = Flask(__name__)
CORS(app)

# MySQL Configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Nayasa!123',
    'database': 'perfume_dash'
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

# Route for the index page
@app.route('/')
def index():
    conn = get_db_connection()
    if conn is None:
        return render_template('index.html', error="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT COUNT(*) as order_count FROM orders')
    orders_count = cursor.fetchone()

    cursor.execute('SELECT COUNT(*) as perfume_count FROM perfume')
    perfume_count = cursor.fetchone()

    cursor.execute('SELECT SUM(sales_amount) as total_sales FROM sales_data')
    total_sales = cursor.fetchone()

    cursor.close()
    conn.close()
    
    return render_template('index.html', 
                           orders_count=orders_count, 
                           perfume_count=perfume_count, 
                           total_sales=total_sales)
@app.route('/best_selling_perfume', methods=['GET'])
def best_selling_perfume():
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor(dictionary=True)
    
    try:
        query = '''
            SELECT p.perfume_name, SUM(s.quantity_sold) AS total_sold
            FROM sales_data s
            INNER JOIN perfume p ON s.perfume_id = p.perfume_id
            GROUP BY s.perfume_id
            ORDER BY total_sold DESC
            LIMIT 1
        '''
        cursor.execute(query)
        best_seller = cursor.fetchone()
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

    return jsonify(best_seller)
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
@app.route('/sales_data_overview', methods=['GET'])  # Change the route name
def get_sales_data_overview():
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor(dictionary=True)
    
    try:
        query = '''
            SELECT month_name, SUM(sales_amount) AS total_sales
            FROM sales_data
            GROUP BY month_name
            ORDER BY FIELD(month_name, 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December')
        '''
        cursor.execute(query)
        sales_data = cursor.fetchall()
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

    return jsonify(sales_data)



@app.route('/order')
def order_page():
    return render_template('order.html')

# Fetch all orders
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

# Delete an order
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

@app.route('/manage_perfume')
def manage_perfume():
    return render_template('manage_perfume.html')

# Fetch all perfume
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

# Add a new perfume
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

        if not all([perfume_id, perfume_name, brand_name, price, stock_level, category]):
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
            INSERT INTO perfume (perfume_id, perfume_name, brand_id, price, stock_level, category) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        try:
            cursor.execute(query, (perfume_id, perfume_name, brand_id, price, stock_level, category))
            conn.commit()
        except mysql.connector.IntegrityError:
            return jsonify({'error': 'Perfume ID already exists!'}), 400
        
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Perfume added successfully!'})

# Update perfume (Fixed the logic)
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

# Delete a perfume
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
    



@app.route('/analytics')
def analytics():
    return render_template('analytics.html')
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

@app.route('/customer')
def customer():
    return render_template('customer.html')

@app.route('/discounts')
def discounts():
    return render_template('discounts.html')

@app.route('/inventory')
def inventory():
    return render_template('inventory.html')


# Route for supplier page
@app.route('/supplier')
def supplier():
    return render_template('supplier.html')  # Ensure supplier.html is inside the 'templates' folder

# Fetch all supplier
@app.route('/get_supplier', methods=['GET'])
def get_supplier():
    conn = get_db_connection()
    if conn is None:
        print("Database connection failed")  # Debugging
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute('SELECT * FROM supplier')  # Make sure 'supplier' matches the actual table name
        supplier = cursor.fetchall()
        print("Fetched suppliers:", supplier)  # Debugging
    except mysql.connector.Error as err:
        print(f"SQL Error: {err}")  # Debugging SQL errors
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

    return jsonify(supplier)

# Add a new supplier
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


# Update supplier (Fixed the logic)
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
