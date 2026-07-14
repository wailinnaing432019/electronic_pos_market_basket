import mysql.connector
from werkzeug.security import generate_password_hash

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "electrical_pos"
}

try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
 
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        admin_id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL
    );
    """)
 
    try:
        cursor.execute("ALTER TABLE transactions ADD COLUMN status VARCHAR(20) DEFAULT 'Pending';")
    except:
        print("Status column already exists.")
 
    username = "admin"
    password = "admin123" 
    hashed_password = generate_password_hash(password)

    try:
        cursor.execute("INSERT INTO admins (username, password) VALUES (%s, %s)", (username, hashed_password))
        conn.commit()
        print(f"Admin account created: Username: {username}, Password: {password}")
    except mysql.connector.Error as e:
        if e.errno == 1062: # Duplicate entry error
            print("Admin account already exists.")
        else:
            print(f"Error inserting admin: {e}")

    print("Success! Admin table and Status column are ready.")

except mysql.connector.Error as err:
    print(f"Error: {err}")
finally:
    if conn.is_connected():
        cursor.close()
        conn.close()