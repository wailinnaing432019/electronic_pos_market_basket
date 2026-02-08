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

    # ၁။ အကုန်လုံးကို Update လုပ်ဖို့ trans_id တွေကို အရင်ယူမယ်
    cursor.execute("SELECT trans_id FROM transactions")
    ids = cursor.fetchall()

    print(f"Updating {len(ids)} transactions to random dates in the last 6 months...")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=180) # လွန်ခဲ့သော ၁၈၀ ရက်

    for (t_id,) in ids:
        # ကျပန်းရက်စွဲတစ်ခု ဖန်တီးမယ်
        random_days = random.randint(0, 180)
        random_seconds = random.randint(0, 86400)
        new_date = start_date + timedelta(days=random_days, seconds=random_seconds)
        
        # အဆိုပါ ID ကို ရက်စွဲအသစ်နဲ့ Update လုပ်မယ်
        cursor.execute("UPDATE transactions SET trans_date = %s WHERE trans_id = %s", (new_date, t_id))

    conn.commit()
    print("All transaction dates updated successfully!")

except mysql.connector.Error as err:
    print(f"Error: {err}")
finally:
    if conn.is_connected():
        cursor.close()
        conn.close()