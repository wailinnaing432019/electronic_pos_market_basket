import mysql.connector
import random
from datetime import datetime, timedelta

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "electrical_pos"
}

try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    print("Adding 3000 new transactions spread over the last 6 months...")

    # ယနေ့ရက်စွဲ
    end_date = datetime.now()
    # လွန်ခဲ့သော ၆ လ (၁၈၀ ရက်)
    start_date = end_date - timedelta(days=180)

    for _ in range(3000):
        # ၆ လအတွင်း ကျပန်းရက်စွဲတစ်ခု ဖန်တီးခြင်း
        random_days = random.randint(0, 180)
        random_seconds = random.randint(0, 86400)
        trans_time = start_date + timedelta(days=random_days, seconds=random_seconds)
        
        # Transaction အသစ်ထည့်ခြင်း
        cursor.execute("INSERT INTO transactions (trans_date) VALUES (%s)", (trans_time,))
        t_id = cursor.lastrowid
        
        r = random.random()
        items = []

        # Pattern များ (အရင်အတိုင်း patterns ကို သုံးထားပါတယ်)
        if r < 0.30: 
            items = [1, 2, 5] # Power Set
            if random.random() < 0.5: items.append(3)
        elif r < 0.55:
            items = [17, 20, 22] # Wiring Set
            if random.random() < 0.4: items.append(24)
        elif r < 0.75:
            items = [34, 36, 37] # Tools Set
        elif r < 0.90:
            items = [26, 27] # Kitchen Set
        else:
            # ကျပန်းပစ္စည်း ၁ ခုမှ ၄ ခုအထိ
            items = random.sample(range(1, 41), random.randint(1, 4))
            
        # ပစ္စည်းတစ်ခုချင်းစီအတွက် ကျပန်းအရေအတွက် (၁ ခုမှ ၃ ခု)
        for p_id in set(items):
            qty = random.randint(1, 3)
            cursor.execute("""
                INSERT INTO transaction_items (trans_id, product_id, quantity) 
                VALUES (%s, %s, %s)
            """, (t_id, p_id, qty))

    conn.commit()
    print(f"Successfully added 3000 transactions with varied timestamps!")

except mysql.connector.Error as err:
    print(f"Error: {err}")
finally:
    if conn.is_connected():
        cursor.close()
        conn.close()