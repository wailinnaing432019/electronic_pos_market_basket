import mysql.connector
import random

def setup_large_db():
    db_config = {"host": "localhost", "user": "root", "password": "", "database": "electrical_pos"}
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    # ၁။ Foreign Key စစ်တာ ခဏပိတ်ပြီး အကုန်ဖျက်မယ်
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    cursor.execute("DROP TABLE IF EXISTS transaction_items, transactions, products, categories")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

    # ၂။ Tables ပြန်ဆောက်မယ်
    cursor.execute("CREATE TABLE categories (cat_id INT AUTO_INCREMENT PRIMARY KEY, cat_name VARCHAR(100))")
    cursor.execute("CREATE TABLE products (product_id INT AUTO_INCREMENT PRIMARY KEY, product_name VARCHAR(255), cat_id INT, FOREIGN KEY (cat_id) REFERENCES categories(cat_id))")
    cursor.execute("CREATE TABLE transactions (trans_id INT AUTO_INCREMENT PRIMARY KEY, trans_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    cursor.execute("CREATE TABLE transaction_items (detail_id INT AUTO_INCREMENT PRIMARY KEY, trans_id INT, product_id INT, FOREIGN KEY (trans_id) REFERENCES transactions(trans_id), FOREIGN KEY (product_id) REFERENCES products(product_id))")

    # ၃။ Categories ထည့်မယ်
    categories = [("Solar System",), ("Power Tools",), ("Lighting",), ("Cooling",)]
    cursor.executemany("INSERT INTO categories (cat_name) VALUES (%s)", categories)
    conn.commit()

    # ၄။ ပစ္စည်း ၁၅ မျိုး သေချာထည့်မယ် (IDs will be 1 to 15)
    products = [
        ("Solar Panel", 1), ("Inverter", 1), ("Battery", 1), ("Solar Controller", 1), # 1,2,3,4
        ("Electric Drill", 2), ("Drill Bits", 2), ("Safety Gloves", 2), ("Goggles", 2), # 5,6,7,8
        ("LED Bulb", 3), ("Electrical Tape", 3), ("Tester Pen", 3), ("Wire Stripper", 3), # 9,10,11,12
        ("Ceiling Fan", 4), ("Fan Regulator", 4), ("Capacitor", 4) # 13,14,15
    ]
    cursor.executemany("INSERT INTO products (product_name, cat_id) VALUES (%s, %s)", products)
    conn.commit()

    # ၅။ Pattern အလိုက် Transaction ၁၀၀၀ ထည့်မယ်
    patterns = [
        [1, 2, 3, 4],    # Solar Set
        [5, 6, 7, 8],    # Drill Set
        [9, 10, 11, 12], # Wiring Set
        [13, 14, 15]     # Fan Set
    ]

    print("Generating 1000 transactions...")
    for i in range(1000):
        cursor.execute("INSERT INTO transactions () VALUES ()")
        t_id = cursor.lastrowid
        
        # Random pattern တစ်ခုယူပြီး အဲ့ထဲက ပစ္စည်း ၂ ခုမှ ၄ ခုအထိ တွဲဝယ်ခိုင်းမယ်
        base_pattern = random.choice(patterns)
        num_to_pick = random.randint(2, len(base_pattern))
        selected_items = random.sample(base_pattern, num_to_pick)

        for p_id in selected_items:
            cursor.execute("INSERT INTO transaction_items (trans_id, product_id) VALUES (%s, %s)", (t_id, p_id))
            
    conn.commit()
    conn.close()
    print("✅ 1000 Transactions with 15 products generated successfully!")

if __name__ == "__main__":
    setup_large_db()