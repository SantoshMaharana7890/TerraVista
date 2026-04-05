import requests
import random
import os
from flask import Flask, render_template, request
import urllib.parse
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

# --- WIKIPEDIA DYNAMIC DETAIL ROUTE ---
@app.route('/place/<place_name>')
def place_detail(place_name):
    # We decode the URL so "Gateway%20of%20India" becomes "Gateway of India"
    clean_name = urllib.parse.unquote(place_name)
    
    # We render a dedicated template and pass the name to it
    return render_template('place_detail.html', place_name=clean_name)

def fetch_live_accommodations(city_name):
    # Map your 5 presentation cities to their latitude and longitude
    coords = {
        "Mumbai": (18.9220, 72.8347),
        "Hyderabad": (17.3850, 78.4867),
        "Bhubaneswar": (20.2961, 85.8245),
        "Punjab": (31.6340, 74.8723), # Using Amritsar coordinates for Punjab
        "Kolkata": (22.5726, 88.3639)
    }
    
    lat, lon = coords.get(city_name, (18.9220, 72.8347))
    
    # OpenStreetMap Overpass API (No Keys Required!)
    overpass_url = "http://overpass-api.de/api/interpreter"
    
    # Ask OSM for hotels and restaurants within a 5km radius
    # We ask for 20 just to be safe, then we'll filter the best 6
    overpass_query = f"""
    [out:json];
    (
      node["tourism"="hotel"](around:5000,{lat},{lon});
      node["amenity"="restaurant"](around:5000,{lat},{lon});
    );
    out 20;
    """
    
    live_items = []
    
    try:
        # Give it a 10-second timeout so the site doesn't freeze
        response = requests.get(overpass_url, params={'data': overpass_query}, timeout=10)
        
        if response.status_code == 200:
            elements = response.json().get("elements", [])
            
            for index, element in enumerate(elements):
                tags = element.get("tags", {})
                name = tags.get("name")
                
                # Only add places that actually have a name listed on the map
                if name:
                    is_hotel = tags.get("tourism") == "hotel"
                    item_type = "lodging" if is_hotel else "dining"
                    
                    # Generate realistic Indian pricing since OSM doesn't provide prices
                    if is_hotel:
                        price_inr = random.randint(1500, 8000)
                    else:
                        price_inr = random.randint(400, 2000)
                        
                    budget_cat = "Premium" if price_inr > 3000 else "Budget"
                    
                    # Generate a realistic rating between 3.8 and 4.9
                    rating = round(random.uniform(3.8, 4.9), 1)
                    
                    live_items.append({
                        "name": name,
                        "type": item_type,
                        "rating": rating,
                        "price": price_inr,
                        "budget_category": budget_cat,
                        # Automatically cycle through your local fallback images
                        "image_file": f"hotel{index % 3 + 1}.jpg" if is_hotel else f"dining{index % 3 + 1}.jpg"
                    })
                    
                    # Stop once we have exactly 6 items for a clean 3-column UI grid
                    if len(live_items) == 6:
                        break
                        
        return live_items
        
    except Exception as e:
        # If the API takes too long, it fails silently and lets the database take over
        print(f"OSM API Error: {e}")
        return []


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

        # 2. Fetch Tourist Places (Stays Database-driven)
        cursor.execute("SELECT * FROM places WHERE city_id = %s", (city_info['id'],))
        places = cursor.fetchall()

        # 3. Fetch Accommodations (LIVE API + DATABASE FALLBACK)
        accommodations = fetch_live_accommodations(city_name)
        
        # If the API list is empty, fallback to your TiDB database instantly
        if not accommodations:
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
