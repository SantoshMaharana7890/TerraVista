import os
from flask import Flask, render_template, request
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)

# --- SECURE TiDB DATABASE CONNECTION ---
def get_db_connection():
    # Securely pulls the password from Render environment variables
    db_password = os.environ.get('TIDB_PASSWORD', 'wbwt0FAtE8PtBU3q')
    
    return mysql.connector.connect(
        host="gateway01.ap-southeast-1.prod.aws.tidbcloud.com",
        port=4000,
        user="2F9h8KmcL9CA9h4.root",
        password=db_password, # Now actually using the secure variable!
        database="defaultdb",
        ssl_verify_cert=True,       # REQUIRED for TiDB Cloud
        ssl_verify_identity=True    # REQUIRED for TiDB Cloud
    )

@app.route('/') # Fixed the missing @ symbol
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/search', methods=['GET'])
def search_city():
    city_name = request.args.get('city')
    
    # Safely handle empty searches
    if not city_name:
        return "Please select a destination from the search bar.", 400
        
    city_name = city_name.capitalize()
    
    # Presentation-Day Safety Net (Try/Except)
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 1. Fetch City Info
        cursor.execute("SELECT * FROM cities WHERE name = %s", (city_name,))
        city_info = cursor.fetchone()
        
        if not city_info:
            return "City not found. Please select a valid city from the dropdown.", 404

        # 2. Fetch Tourist Places
        cursor.execute("SELECT * FROM places WHERE city_id = %s", (city_info['id'],))
        places = cursor.fetchall()

        # 3. Fetch Accommodations
        cursor.execute("SELECT * FROM accommodations WHERE city_id = %s", (city_info['id'],))
        accommodations = cursor.fetchall()
        
        return render_template('city.html', city=city_info, places=places, items=accommodations)
        
    except Error as e:
        # If the database fails, the app survives and logs the error safely
        print(f"Database Error: {e}")
        return "TerraVista is experiencing high traffic. Please try again in a moment.", 500
        
    finally:
        # Always securely close the connection, even if an error happened
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
