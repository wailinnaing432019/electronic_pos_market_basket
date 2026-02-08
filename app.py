from flask import flash,Flask, render_template, session, redirect, url_for, request
import mysql.connector
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import numpy as np
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'electrical_pos_secret_key' # Session သုံးဖို့ secret key လိုအပ်ပါတယ်

def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="electrical_pos"
    )


# Security Decorator: Login ဝင်ထားမှ ပေးဝင်မယ့် logic
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('ကျေးဇူးပြု၍ Admin Login အရင်ဝင်ပါ', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Admin Login ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        user = request.form['username']
        pw = request.form['password']
        
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admins WHERE username = %s", (user,))
        admin = cursor.fetchone()
        db.close()

        if admin and check_password_hash(admin['password'], pw):
            session['admin_id'] = admin['admin_id']
            session['admin_name'] = admin['username']
            flash('Login အောင်မြင်ပါသည်', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Username သို့မဟုတ် Password မှားယွင်းနေပါသည်', 'danger')
            
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_name', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # ၁။ လအလိုက် အရောင်းရငွေ (Predictive Analysis)
    cursor.execute("""
        SELECT DATE_FORMAT(t.trans_date, '%Y-%m') as month, 
               SUM(ti.quantity * p.price) as monthly_revenue
        FROM transactions t
        JOIN transaction_items ti ON t.trans_id = ti.trans_id
        JOIN products p ON ti.product_id = p.product_id
        GROUP BY month ORDER BY month ASC
    """)
    sales_data = cursor.fetchall()
    
    months = [data['month'] for data in sales_data]
    revenues = [float(data['monthly_revenue']) for data in sales_data]

    # ၂။ Linear Regression Prediction
    prediction = 0
    if len(revenues) >= 2:
        x = np.arange(len(revenues))
        y = np.array(revenues)
        m, c = np.polyfit(x, y, 1)
        prediction = (m * len(revenues)) + c
    elif len(revenues) == 1:
        prediction = revenues[0]
        
    # ၃။ Basic Stats
    cursor.execute("SELECT COUNT(*) as total_orders FROM transactions")
    orders_count = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) as total_products FROM products")
    products_count = cursor.fetchone()
    
    dashboard_stats = {
        'orders': orders_count if orders_count else {'total_orders': 0},
        'products': products_count if products_count else {'total_products': 0}
    }

    # ၄။ Association Rules (အရေးကြီးဆုံးအပိုင်း - Empty List Default ထားမယ်)
    cursor.execute("SELECT antecedent, consequent, confidence FROM recommendation_rules ORDER BY confidence DESC")
    all_rules = cursor.fetchall()
    if not all_rules:
        all_rules = [] # Database မှာ data မရှိရင် empty list ပေးထားမှ JSON serializable ဖြစ်မယ်

    # ၅။ Category Trends
    cursor.execute("""
        SELECT c.cat_name, COUNT(ti.product_id) as sale_count
        FROM transaction_items ti
        JOIN products p ON ti.product_id = p.product_id
        JOIN categories c ON p.cat_id = c.cat_id
        GROUP BY c.cat_id
        ORDER BY sale_count DESC
    """)
    category_trends = cursor.fetchall()

    # ၆။ Low Stock Prediction (Mining based on Sales Velocity)
    cursor.execute("""
        SELECT 
            p.product_name, 
            p.stock_quantity,
            COALESCE(SUM(ti.quantity) / 30, 0) as daily_velocity
        FROM products p
        LEFT JOIN transaction_items ti ON p.product_id = ti.product_id
        LEFT JOIN transactions t ON ti.trans_id = t.trans_id 
            AND t.trans_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        GROUP BY p.product_id, p.product_name, p.stock_quantity
        HAVING (p.stock_quantity / NULLIF(COALESCE(SUM(ti.quantity) / 30, 0), 0)) <= 7 
        OR p.stock_quantity <= 5
        ORDER BY p.stock_quantity ASC
        LIMIT 5
    """)
    stock_alerts = cursor.fetchall()
    db.close()
    
    return render_template('admin/dashboard.html', 
                           sales_labels=months, 
                           sales_values=revenues,
                           next_month_prediction=max(0, round(prediction, 2)),
                           stats=dashboard_stats, 
                           all_rules=all_rules, 
                           category_trends=category_trends
                           , stock_alerts=stock_alerts)

# --- Product Management (View All & Category Selection) ---
@app.route('/admin/products')
@admin_required
def admin_products():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # ပစ္စည်းစာရင်းကို Category Name ပါတွဲယူမယ်
    cursor.execute("""
        SELECT p.*, c.cat_name 
        FROM products p 
        LEFT JOIN categories c ON p.cat_id = c.cat_id 
        ORDER BY p.product_id DESC
    """)
    products = cursor.fetchall()
    
    # Category list ကို Manual ရွေးဖို့ ဆွဲထုတ်မယ်
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()
    
    db.close()
    return render_template('admin/products.html', products=products, categories=categories)

# --- Add Product (Create) ---

# ပုံသိမ်းမည့်နေရာ သတ်မှတ်ချက်
UPLOAD_FOLDER = 'static/uploads/products'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
@app.route('/admin/product/add', methods=['POST'])
@admin_required
def add_product():
    name = request.form['name']
    price = request.form['price']
    cat_id = request.form['cat_id'] # Manual ရွေးလိုက်တဲ့ ID
    stock_quantity = request.form['stock_quantity'] 
    file = request.files.get('image')

    filename = 'default.jpg' # ပုံမတင်ရင် သုံးမယ့် ပုံသေအမည်
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_FOLDER, filename))
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO products (product_name, price, cat_id, stock_quantity, image_url) VALUES (%s, %s,%s,%s, %s)", 
                   (name, price, cat_id, stock_quantity, filename))
    db.commit()
    db.close()
    flash('Product အသစ်ထည့်သွင်းပြီးပါပြီ', 'success')
    return redirect(url_for('admin_products'))

# --- Update Product (Edit) ---
@app.route('/admin/product/edit/<int:id>', methods=['POST'])
@admin_required
def edit_product(id):
    name = request.form['name']
    price = request.form['price']
    cat_id = request.form['cat_id'] # Manual ရွေးလိုက်တဲ့ ID
    stock_quantity = request.form['stock_quantity'] 
    file = request.files.get('image')
    
    db = get_db()
    cursor = db.cursor()

    if file and file.filename != '':
        filename = secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        # ပုံအသစ်ပါရင် image_url ပါ update လုပ်မယ်
        cursor.execute("""
            UPDATE products SET product_name=%s, price=%s, cat_id=%s, image_url=%s, stock_quantity=%s
            WHERE product_id=%s
        """, (name, price, cat_id, filename, stock_quantity, id))
    else:
        # ပုံမပါရင် နဂိုပုံအတိုင်း ထားမယ်
        cursor.execute("""
            UPDATE products SET product_name=%s, price=%s, cat_id=%s, stock_quantity=%s
            WHERE product_id=%s
        """, (name, price, cat_id, stock_quantity, id))
        
 
    db.commit()
    db.close()
    flash('Product ကို ပြင်ဆင်ပြီးပါပြီ', 'success')
    return redirect(url_for('admin_products'))

# --- Delete Product (Delete) ---
@app.route('/admin/product/delete/<int:id>')
@admin_required
def delete_product(id):
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM products WHERE product_id = %s", (id,))
        db.commit()
        flash('Product ကို ဖျက်လိုက်ပါပြီ', 'success')
    except mysql.connector.Error:
        flash('ဤပစ္စည်းသည် Order စာရင်းထဲတွင် ရှိနေသောကြောင့် ဖျက်၍မရပါ', 'danger')
    db.close()
    return redirect(url_for('admin_products'))


@app.route('/admin/orders')
@admin_required
def admin_orders():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    # Order တွေနဲ့ ၎င်းတို့၏ စုစုပေါင်းတန်ဖိုးကို ဆွဲထုတ်ခြင်း
    query = """
        SELECT t.trans_id, t.trans_date, t.status, SUM(ti.quantity * p.price) as total_amount
        FROM transactions t
        JOIN transaction_items ti ON t.trans_id = ti.trans_id
        JOIN products p ON ti.product_id = p.product_id
        GROUP BY t.trans_id ORDER BY t.trans_date DESC
    """
    cursor.execute(query)
    orders = cursor.fetchall()
    db.close()
    return render_template('admin/orders.html', orders=orders)
 
@app.route('/admin/order/status/<int:id>', methods=['POST'])
@admin_required
def update_order_status(id):
    new_status = request.form.get('status')
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # ၁။ လက်ရှိ Order ရဲ့ Status ကို အရင်စစ်မယ်
    cursor.execute("SELECT status FROM transactions WHERE trans_id = %s", (id,))
    order = cursor.fetchone()

    if not order:
        db.close()
        flash('Order မတွေ့ရှိပါ', 'danger')
        return redirect(url_for('admin_orders'))

    # ၂။ Guard: Completed ဖြစ်ပြီးသား Order ကို ပြန်ပြင်ခွင့်မပြုပါ
    if order['status'] == 'Completed':
        db.close()
        flash('Completed ဖြစ်ပြီးသား Order ကို Status ပြန်ပြောင်း၍မရပါ', 'warning')
        return redirect(url_for('admin_orders'))

    # ၃။ Status အသစ်အပေါ် မူတည်ပြီး Stock ကို ကိုင်တွယ်ခြင်း
    # အရင်ဆုံး Order ထဲမှာပါတဲ့ ပစ္စည်းတွေကို ယူမယ်
    cursor.execute("SELECT product_id, quantity FROM transaction_items WHERE trans_id = %s", (id,))
    items = cursor.fetchall()

    if new_status == 'Completed':
        # Stock လျော့မယ်
        for item in items:
            cursor.execute("""
                UPDATE products 
                SET stock_quantity = stock_quantity - %s 
                WHERE product_id = %s
            """, (item['quantity'], item['product_id']))
            
    elif new_status == 'Cancelled' and order['status'] == 'Completed':
        # အကယ်၍ အရင်က Completed ဖြစ်ခဲ့မှသာ (အခု logic မှာတော့ guard ကြောင့် ဒါမဖြစ်နိုင်တော့ပါ)
        # ဒါပေမဲ့ safety အနေနဲ့ stock ပြန်ပေါင်းပေးမယ်
        for item in items:
            cursor.execute("""
                UPDATE products 
                SET stock_quantity = stock_quantity + %s 
                WHERE product_id = %s
            """, (item['quantity'], item['product_id']))

    # ၄။ Transaction Status ကို Update လုပ်မယ်
    cursor.execute("UPDATE transactions SET status = %s WHERE trans_id = %s", (new_status, id))
    
    db.commit()
    db.close()
    
    flash(f'Order #{id} ရဲ့ Status ကို {new_status} သို့ ပြောင်းလဲပြီးပါပြီ', 'info')
    return redirect(url_for('admin_orders'))

@app.route('/admin/order_details/<int:id>')
@admin_required
def order_details(id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    # JOIN သုံးပြီး ပစ္စည်းနာမည်နဲ့ ဈေးနှုန်းတွေကို ဆွဲထုတ်မယ်
    query = """
        SELECT p.product_name, ti.quantity, p.price, (ti.quantity * p.price) as subtotal
        FROM transaction_items ti
        JOIN products p ON ti.product_id = p.product_id
        WHERE ti.trans_id = %s
    """
    cursor.execute(query, (id,))
    items = cursor.fetchall()
    db.close()
    return {"items": items} # JSON အနေနဲ့ ပြန်ပေးမယ်

# customer side
@app.route('/')
def index():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # Categories အားလုံးကို နာမည်အစဉ်လိုက် ယူမယ်
    cursor.execute("SELECT * FROM categories ORDER BY cat_id")
    all_categories = cursor.fetchall()
    
    # Products အားလုံးကို ယူမယ်
    cursor.execute("SELECT * FROM products")
    all_products = cursor.fetchall()
    
    db.close()
    return render_template('index.html', categories=all_categories, products=all_products)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # JOIN သုံးပြီး cat_name ကိုပါ တစ်ခါတည်း ယူမယ်
    cursor.execute("""
        SELECT p.*, c.cat_name 
        FROM products p
        JOIN categories c ON p.cat_id = c.cat_id
        WHERE p.product_id = %s
    """, (product_id,))
    product = cursor.fetchone()

    # Recommendations ယူတဲ့အပိုင်း (အရင်အတိုင်းပဲ)
    cursor.execute("""
        SELECT p.product_id, p.product_name, p.price, r.confidence 
        FROM recommendation_rules r
        JOIN products p ON r.consequent = p.product_name
        WHERE r.antecedent = %s ORDER BY r.confidence DESC LIMIT 3
    """, (product['product_name'],))
    recs = cursor.fetchall()
    
    db.close()
    return render_template('product.html', product=product, recommendations=recs)

# Cart ထဲပစ္စည်းထည့်တဲ့ Route ကိုပြင်မယ်
@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'cart_dict' not in session:
        session['cart_dict'] = {}
    
    # ပစ္စည်းရှိပြီးသားဆိုရင် quantity ၁ တိုးမယ်၊ မရှိရင် ၁ လို့သတ်မှတ်မယ်
    cart = session['cart_dict']
    product_id_str = str(product_id)
    if product_id_str in cart:
        cart[product_id_str] += 1
    else:
        cart[product_id_str] = 1
    
    session['cart_dict'] = cart
    return redirect(url_for('view_cart'))

# Quantity လျှော့တဲ့ Route အသစ်
@app.route('/reduce_item/<int:product_id>')
def reduce_item(product_id):
    cart = session.get('cart_dict', {})
    pid = str(product_id)
    if pid in cart:
        cart[pid] -= 1
        if cart[pid] < 1:
            del cart[pid] # ၀ ဖြစ်သွားရင် ဖျက်လိုက်မယ်
    session['cart_dict'] = cart
    return redirect(url_for('view_cart'))

@app.route('/cart')
def view_cart():
    # session['cart_dict'] ကို အသုံးပြုမည် (ဥပမာ- {'1': 2, '5': 1})
    cart_dict = session.get('cart_dict', {})
    if not cart_dict:
        return render_template('cart.html', items=[], total=0, recommendations=[])
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # Cart ထဲရှိ Product ID များယူခြင်း
    ids = list(cart_dict.keys())
    format_strings = ','.join(['%s'] * len(ids))
    cursor.execute(f"SELECT * FROM products WHERE product_id IN ({format_strings})", tuple(ids))
    db_products = cursor.fetchall()
    
    cart_items = []
    total_price = 0
    item_names = [] # Recommendation စစ်ရန်

    for p in db_products:
        pid_str = str(p['product_id'])
        qty = cart_dict[pid_str]
        subtotal = p['price'] * qty
        
        # Product object ထဲသို့ quantity နှင့် subtotal ထည့်ခြင်း
        p['quantity'] = qty
        p['subtotal'] = subtotal
        
        total_price += subtotal
        item_names.append(p['product_name'])
        cart_items.append(p)
    
    # --- Recommendation Logic (ယခင်အတိုင်း) ---
    recommendations = []
    seen_recommendations = set()
    cursor.execute("SELECT * FROM recommendation_rules ORDER BY confidence DESC")
    all_rules = cursor.fetchall()
    
    for rule in all_rules:
        rule_antecedents = [x.strip() for x in rule['antecedent'].split(',')]
        if all(ant in item_names for ant in rule_antecedents):
            consequent = rule['consequent']
            if consequent not in item_names and consequent not in seen_recommendations:
                cursor.execute("SELECT * FROM products WHERE product_name = %s", (consequent,))
                p_details = cursor.fetchone()
                if p_details:
                    p_details['confidence'] = rule['confidence']
                    recommendations.append(p_details)
                    seen_recommendations.add(consequent)
        if len(recommendations) >= 4: break

    db.close()
    return render_template('cart.html', items=cart_items, total=total_price, recommendations=recommendations)

@app.route('/checkout', methods=['POST'])
def checkout():
    cart = session.get('cart', {})
    if not cart:
        flash("လှည်းထဲမှာ ပစ္စည်းမရှိသေးပါ", "warning")
        return redirect(url_for('cart_view'))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    try:
        # ၁။ ပစ္စည်းတစ်ခုချင်းစီရဲ့ Stock ကို အရင်စစ်မယ်
        for product_id, item in cart.items():
            cursor.execute("SELECT product_name, stock_quantity FROM products WHERE product_id = %s", (product_id,))
            product = cursor.fetchone()

            if product['stock_quantity'] < item['quantity']:
                flash(f"တောင်းပန်ပါတယ်၊ {product['product_name']} က လက်ကျန် {product['stock_quantity']} ခုပဲ ရှိပါတော့တယ်", "danger")
                return redirect(url_for('cart_view'))

        # ၂။ Stock အဆင်ပြေမှ Transaction ထဲ ထည့်မယ်
        cursor.execute("INSERT INTO transactions (status) VALUES ('pending')")
        trans_id = cursor.lastrowid

        for product_id, item in cart.items():
            cursor.execute("""
                INSERT INTO transaction_items (trans_id, product_id, quantity) 
                VALUES (%s, %s, %s)
            """, (trans_id, product_id, item['quantity']))

        db.commit()
        session.pop('cart', None)
        flash("Order တင်ခြင်း အောင်မြင်ပါတယ်", "success")

    except Exception as e:
        db.rollback()
        flash("အမှားတစ်ခု ဖြစ်သွားပါတယ်", "danger")
    finally:
        db.close()

    return redirect(url_for('index'))
     
if __name__ == '__main__':
    app.run(debug=True, port=8000)