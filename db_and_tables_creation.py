import mysql.connector
import random

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "electrical_pos"
}

try:
    # Database အရင်ချိတ်ပြီး မရှိရင် ဆောက်မယ်
    conn = mysql.connector.connect(host=db_config['host'], user=db_config['user'], password=db_config['password'])
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS electrical_pos")
    cursor.execute("USE electrical_pos")

    # ၁။ Tables များ အသစ်ပြန်ဆောက်ခြင်း (အဟောင်းရှိရင် ဖျက်မယ် - ရှင်းရှင်းလင်းလင်းဖြစ်အောင်)
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
    tables = ["recommendation_rules", "transaction_items", "transactions", "products", "categories"]
    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

    # Categories Table
    cursor.execute("CREATE TABLE categories (cat_id INT AUTO_INCREMENT PRIMARY KEY, cat_name VARCHAR(100))")

    # Products Table (Price ပါဝင်သည်)
    cursor.execute("""
        CREATE TABLE products (
            product_id INT AUTO_INCREMENT PRIMARY KEY,
            product_name VARCHAR(255),
            price DECIMAL(12, 2),
            cat_id INT,
            stock_quantity INT DEFAULT 0,
            image_url VARCHAR(255) DEFAULT 'default.jpg',
            FOREIGN KEY (cat_id) REFERENCES categories(cat_id)
        )
    """)

    # Transactions Table
    cursor.execute("CREATE TABLE transactions (trans_id INT AUTO_INCREMENT PRIMARY KEY, trans_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")

    # Transaction Items Table
    cursor.execute("""
        CREATE TABLE transaction_items (
            detail_id INT AUTO_INCREMENT PRIMARY KEY,
            trans_id INT,
            product_id INT,
            quantity INT,
            FOREIGN KEY (trans_id) REFERENCES transactions(trans_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)

    # Recommendation Rules Table (Mining ရလဒ်သိမ်းရန်)
    cursor.execute("""
        CREATE TABLE recommendation_rules (
            rule_id INT AUTO_INCREMENT PRIMARY KEY,
            antecedent VARCHAR(255),
            consequent VARCHAR(255),
            confidence FLOAT,
            lift FLOAT
        )
    """)

    # ၂။ Categories ၅ ခု ခွဲလိုက်ပါမယ်
    categories = ['Power Solutions', 'Lighting', 'Wiring Accessories', 'Home Appliances', 'Tools & Safety']
    for cat in categories:
        cursor.execute("INSERT INTO categories (cat_name) VALUES (%s)", (cat,))
    
    # ၃။ Products ၄၀ (ID 1 ကနေ 40 အထိ အစဉ်လိုက်ဖြစ်အောင် သတိထားပါ)
    products = [
        # Power Solutions (1-8)
        ('Inverter 1000W', 250000, 1), ('Deep Cycle Battery', 450000, 1), ('Solar Panel 100W', 125000, 1),
        ('Inverter 2000W', 480000, 1), ('Solar Controller', 35000, 1), ('Battery Charger', 55000, 1),
        ('Solar Cable 10m', 15000, 1), ('DC Breaker', 12000, 1),
        # Lighting (9-16)
        ('LED Bulb 9W', 3500, 2), ('LED Bulb 12W', 4500, 2), ('Fluorescent Tube', 8500, 2),
        ('Flashlight', 15000, 2), ('Emergency Light', 25000, 2), ('Street Light', 45000, 2),
        ('Ceiling Light', 35000, 2), ('Sensor Light', 12000, 2),
        # Wiring Accessories (17-24)
        ('Wire 1.5mm', 45000, 3), ('Wire 2.5mm', 75000, 3), ('Power Strip', 12000, 3),
        ('Wall Switch', 2500, 3), ('Circuit Breaker', 18000, 3), ('Electric Tape', 1000, 3),
        ('Multi Socket', 6500, 3), ('Gang Box', 1200, 3),
        # Home Appliances (25-32)
        ('Electric Fan', 55000, 4), ('Electric Kettle', 28000, 4), ('Rice Cooker', 45000, 4),
        ('Iron', 32000, 4), ('Toaster', 38000, 4), ('Blender', 52000, 4),
        ('Hair Dryer', 18000, 4), ('Extension Coil', 15000, 4),
        # Tools & Safety (33-40)
        ('Digital Multimeter', 35000, 5), ('Drill Machine', 85000, 5), ('Screwdriver Set', 15000, 5),
        ('Safety Gloves', 5500, 5), ('Safety Goggles', 4500, 5), ('Soldering Iron', 12000, 5),
        ('Pliers', 7500, 5), ('Hammer', 8500, 5)
    ]
    cursor.executemany("INSERT INTO products (product_name, price, cat_id, stock_quantity, image_url) VALUES (%s, %s, %s, 100, 'default.jpg')", products)

    # ၄။ ပိုမိုအားကောင်းသော Patterns များ ထည့်သွင်းခြင်း
    print("Generating 2000 patterned transactions...")
    for _ in range(2000):
        cursor.execute("INSERT INTO transactions (trans_date) VALUES (NOW())")
        t_id = cursor.lastrowid
        
        r = random.random()
        items = []

        # Pattern A: Solar Full Set (Inverter, Battery, Controller, Panel)
        if r < 0.30: 
            items = [1, 2, 5] # Inverter + Battery + Controller
            if random.random() < 0.5: items.append(3) # 50% Panel ထပ်ပါမယ်

        # Pattern B: House Wiring Set (Wire, Switch, Tape, Gang Box)
        elif r < 0.55:
            items = [17, 20, 22] # Wire + Switch + Tape
            if random.random() < 0.4: items.append(24) # 40% Gang Box ပါမယ်

        # Pattern C: Safety & Tools (Drill, Gloves, Goggles)
        elif r < 0.75:
            items = [34, 36, 37] # Drill + Gloves + Goggles

        # Pattern D: Kitchen Set (Kettle, Rice Cooker)
        elif r < 0.90:
            items = [26, 27]

        # Pattern E: Totally Random (အစစ်အမှန်ဖြစ်အောင် random လည်း နည်းနည်းပါရမယ်)
        else:
            items = random.sample(range(1, 41), random.randint(1, 3))
            
        for p_id in set(items): # set() သုံးခြင်းဖြင့် ပစ္စည်း ID မထပ်အောင်လုပ်မယ်
            cursor.execute("INSERT INTO transaction_items (trans_id, product_id, quantity) VALUES (%s, %s, 1)", (t_id, p_id))
    conn.commit()
    print("Database Reset and 2000 Transactions Inserted Successfully!")

except mysql.connector.Error as err:
    print(f"Error: {err}")
finally:
    if conn.is_connected():
        cursor.close()
        conn.close()