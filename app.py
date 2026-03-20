import os
from flask import Flask, render_template, request
import mysql.connector

app = Flask(__name__)

# --- SECURE TiDB DATABASE CONNECTION ---
def get_db_connection():
    # os.environ pulls the secret password securely from Render. 
    # The second string is a fallback so it still works instantly on your local laptop!
    db_password = os.environ.get('TIDB_PASSWORD', 'wbwt0FAtE8PtBU3q')
    return mysql.connector.connect(
        host="gateway01.ap-southeast-1.prod.aws.tidbcloud.com",
        port=4000,
        user="2F9h8KmcL9CA9h4.root",
        password="wbwt0FAtE8PtBU3q",
        database="defaultdb"
    )

@app.route('/')
def home():
    # Renders the main frontpage
    return render_template('index.html')

@app.route('/about')
def about():
    # Renders the updated About Us page
    return render_template('about.html')

@app.route('/search', methods=['GET'])
def search_city():
    city_name = request.args.get('city')
    
    # Capitalize just in case the user bypassed the dropdown and typed 'mumbai'
    if city_name:
        city_name = city_name.capitalize()
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 1. Fetch City Info
    cursor.execute("SELECT * FROM cities WHERE name = %s", (city_name,))
    city_info = cursor.fetchone()
    
    if not city_info:
        conn.close()
        return "City not found. Please select a valid city from the dropdown.", 404

    # 2. Fetch Tourist Places for this exact city
    cursor.execute("SELECT * FROM places WHERE city_id = %s", (city_info['id'],))
    places = cursor.fetchall()

    # 3. Fetch Accommodations (Hotels, Lodges, Restaurants, Cafes) for this exact city
    cursor.execute("SELECT * FROM accommodations WHERE city_id = %s", (city_info['id'],))
    accommodations = cursor.fetchall()
    
    conn.close()
    
    return render_template('city.html', city=city_info, places=places, items=accommodations)

if __name__ == '__main__':
    # Binds to the port Render assigns, or defaults to 5000 locally
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
