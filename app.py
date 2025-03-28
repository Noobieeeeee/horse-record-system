import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO
# import serial
import threading
import time
from werkzeug.security import generate_password_hash, check_password_hash

# app = Flask(__name__)
app = Flask(__name__, static_folder='static')
app.secret_key = '5f4dcc3b5aa765d61d8327deb882cf99b8b7f7e8e8b9b7f7'  # Replace with your actual secret key
socketio = SocketIO(app)

current_time = "--:--:--"


# Ensure the 'images' folder exists
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'images')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Configure file upload settings
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# SQLite database setup
DATABASE = os.path.join(app.root_path, 'database.db')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def init_db():
    """Initialize the SQLite database with the required tables."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            horse_number TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            address TEXT,
            organization TEXT,
            age INTEGER,
            image TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS race_times (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rider_id INTEGER,
            time TEXT,
            FOREIGN KEY (rider_id) REFERENCES records (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# routing reader here
# Function to read UART data and send it to the web clients via SocketIO

#commented here xyxyxyx
# def read_uart():
#     global current_time
#     # Configure the serial connection
#     ser = serial.Serial(
#         port='/dev/serial0',  # Serial port (UART) on Raspberry Pi
#         baudrate=115200,      # Baud rate (must match ESP32)
#         parity=serial.PARITY_NONE,
#         stopbits=serial.STOPBITS_ONE,
#         bytesize=serial.EIGHTBITS,
#         timeout=1
#     )

#     print("Waiting for data from ESP32...")

#     try:
#         while True:
#             if ser.in_waiting > 0:  # Check if data is available
#                 data = ser.readline().decode('utf-8').strip()  # Read and decode the data
#                 current_time = data  # Store the received data
#                 print(f"Received elapsed time: {current_time} seconds")
#                 # Emit the time to all connected clients
#                 socketio.emit('update_time', {'time': current_time})
#     except KeyboardInterrupt:
#         print("Program terminated.")
#     except serial.SerialException as e:
#         print(f"Serial error: {e}")
#     finally:
#         ser.close()  # Close the serial connection when done


@socketio.on('connect')
def handle_connect():
    print("Client connected")
    # Emit the latest time immediately after connection
    socketio.emit('update_time', {'time': current_time})

# Start UART reading in a separate thread

# uart_thread = threading.Thread(target=read_uart)
# uart_thread.daemon = True
# uart_thread.start()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('You have been logged out', 'success')
    return redirect(url_for('login'))

@app.route('/update_settings', methods=['POST'])
def update_settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    new_username = request.form['username']
    current_password = request.form['current_password']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT password FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    
    if not user or not check_password_hash(user[0], current_password):
        flash('Current password is incorrect', 'error')
        conn.close()
        return redirect(url_for('index'))
    
    if new_password:
        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            conn.close()
            return redirect(url_for('index'))
        new_password_hash = generate_password_hash(new_password)
        cursor.execute('UPDATE users SET username = ?, password = ? WHERE id = ?', (new_username, new_password_hash, session['user_id']))
    else:
        cursor.execute('UPDATE users SET username = ? WHERE id = ?', (new_username, session['user_id']))
    
    conn.commit()
    conn.close()
    
    session['username'] = new_username
    flash('Settings updated successfully', 'success')
    return redirect(url_for('index'))

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    page = request.args.get('page', 1, type=int)
    start = (page - 1) * 7  # Display 7 items per page
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Order by horse_number numerically and limit to 7 items per page
    cursor.execute('SELECT * FROM records ORDER BY CAST(horse_number AS INTEGER) ASC LIMIT ? OFFSET ?', (7, start))
    rows = cursor.fetchall()
    
    cursor.execute('SELECT COUNT(*) FROM records')
    total_records = cursor.fetchone()[0]
    conn.close()
    
    # Convert tuples to dictionaries
    paginated_records = [
        {
            'id': row[0],
            'horse_number': row[1],
            'name': row[2],
            'address': row[3],
            'organization': row[4],
            'age': row[5],
            'image': row[6],
        }
        for row in rows
    ]

    total_pages = (total_records // 7) + (1 if total_records % 7 != 0 else 0)  # Adjusted for 7 items per page
    total_racers = get_total_racers()  # Get the total number of racers
    racers = get_all_racers()  # Get all racers for the race controls
    return render_template('index.html', records=paginated_records, page=page, total_pages=total_pages, total_racers=total_racers, racers=racers, get_title=get_title, get_announcement=get_announcement)

@app.route('/add', methods=['POST'])
def add_item():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    horse_number = request.form['horse_number']
    name = request.form['name']
    address = request.form['address']
    organization = request.form['organization']
    age = request.form['age']

    # Handle image upload
    image = None
    if 'image' in request.files:
        image_file = request.files['image']
        if image_file and allowed_file(image_file.filename):
            image_filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
            image = image_filename

    # Insert record into SQLite database
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''        
            INSERT INTO records (horse_number, name, address, organization, age, image)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (horse_number, name, address, organization, age, image))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    except sqlite3.IntegrityError:
        # Handle the case where horse_number already exists
        conn.close()
        error_message = "Error: Horse number already exists!"
        return render_template('index.html', error_message=error_message)


# Route to edit a record
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_record(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    if request.method == 'POST':
        horse_number = request.form['horse_number']
        name = request.form['name']
        address = request.form['address']
        organization = request.form['organization']
        age = request.form['age']

        # Handle image upload
        image = None
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file and allowed_file(image_file.filename):
                image_filename = secure_filename(image_file.filename)
                image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
                image = image_filename

        if image:
            cursor.execute('''
                UPDATE records SET horse_number = ?, name = ?, address = ?, organization = ?, age = ?, image = ?
                WHERE id = ?
            ''', (horse_number, name, address, organization, age, image, id))
        else:
            cursor.execute('''
                UPDATE records SET horse_number = ?, name = ?, address = ?, organization = ?, age = ?
                WHERE id = ?
            ''', (horse_number, name, address, organization, age, id))

        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    # Fetch record to edit
    cursor.execute('SELECT * FROM records WHERE id = ?', (id,))
    row = cursor.fetchone()
    conn.close()

    # Convert tuple to dictionary
    record = {
        'id': row[0],
        'horse_number': row[1],
        'name': row[2],
        'address': row[3],
        'organization': row[4],
        'age': row[5],
        'image': row[6],
    }
    return render_template('edit.html', record=record)


@app.route('/delete/<int:id>', methods=['GET'])
def delete_record(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM records WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))


@app.route('/details/<int:id>', methods=['GET'])
def details(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM records WHERE id = ?', (id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        record = {
            'id': row[0],
            'horse_number': row[1],
            'name': row[2],
            'address': row[3],
            'organization': row[4],
            'age': row[5],
            'image': row[6],
        }
    else:
        record = None

    return render_template('details.html', record=record)

@app.route('/get_final_leaderboard_data')
def get_final_leaderboard_data():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Fetch top 20 racers ordered by time
    cursor.execute('''
        SELECT name, organization, time
        FROM records
        ORDER BY 
            CASE WHEN time IS NULL THEN 1 ELSE 0 END,
            CAST(time AS FLOAT) ASC
        LIMIT 20
    ''')
    records = cursor.fetchall()
    conn.close()

    # Prepare leaderboard data
    leaderboard1 = []
    leaderboard2 = []

    for i in range(20):
        if i < len(records):
            time_formatted = seconds_to_time_format(records[i][2])  # Format the time
            entry = {
                'rank': i + 1,
                'name': records[i][0],
                'organization': records[i][1],
                'time': time_formatted if time_formatted else '--:--:--'
            }
        else:
            entry = {
                'rank': i + 1,
                'name': '---',
                'organization': '---',
                'time': '--:--:--'
            }
        
        # Add to respective leaderboard
        if i < 10:
            leaderboard1.append(entry)
        else:
            leaderboard2.append(entry)
    # print(leaderboard1,leaderboard2)
    return jsonify({'leaderboard1': leaderboard1, 'leaderboard2': leaderboard2})



@app.route('/leaderboard_v2') # new leaderboard with 20 racers - to be used for final leaderboard
def leaderboard_v2():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Fetch top 20 racers ordered by time
    cursor.execute('''
        SELECT r.name, r.organization, rt.time 
        FROM records r
        LEFT JOIN race_times rt ON r.id = rt.rider_id
        WHERE rt.time IS NOT NULL
        ORDER BY rt.time ASC
        LIMIT 20
    ''')
    records = cursor.fetchall()
    conn.close()
    
    # Prepare data for the template, padding with empty entries if less than 20
    leaderboard_data = []
    for i in range(20):
        if i < len(records):
            leaderboard_data.append({
                'rank': i + 1,
                'name': records[i][0],
                'organization': records[i][1],
                'time': records[i][2] if records[i][2] else '--:--:--'
            })
        else:
            leaderboard_data.append({
                'rank': i + 1,
                'name': '---',
                'organization': '---',
                'time': '--:--:--'
            })
    
    return render_template('finalLeaderboard.html', leaderboard_data=leaderboard_data,get_title=get_title, get_announcement=get_announcement)

@app.route('/leaderboard_v1') # old leaderboard with 10 racers
def leaderboard_v1():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Fetch top 10 racers ordered by time
    cursor.execute('''
        SELECT r.name, r.organization, rt.time 
        FROM records r
        LEFT JOIN race_times rt ON r.id = rt.rider_id
        WHERE rt.time IS NOT NULL
        ORDER BY rt.time ASC
        LIMIT 10
    ''')
    records = cursor.fetchall()
    conn.close()
    
    # Prepare data for the template, padding with empty entries if less than 10
    leaderboard_data = []
    for i in range(10):
        if i < len(records):
            leaderboard_data.append({
                'rank': i + 1,
                'name': records[i][0],
                'organization': records[i][1],
                'time': records[i][2] if records[i][2] else '--:--:--'
            })
        else:
            leaderboard_data.append({
                'rank': i + 1,
                'name': '---',
                'organization': '---',
                'time': '--:--:--'
            })
    # print(leaderboard_data)
    
    return render_template('leadboard.html', leaderboard_data=leaderboard_data,get_title=get_title, get_announcement=get_announcement)

@app.route('/race')
def race():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    racers = get_all_racers()
    return render_template('race.html', racers=racers)

def get_all_racers():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM records ORDER BY horse_number ASC')
    records = cursor.fetchall()
    conn.close()
    return [{'id': record[0], 'name': record[1]} for record in records]

def get_total_racers():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM records')
    total = cursor.fetchone()[0]
    conn.close()
    return total

def seconds_to_time_format(seconds):
    """Convert seconds to MM:SS:ms format"""
    if seconds is None:
        return '--:--:--'
    
    try:
        seconds = float(seconds)
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes:02d}:{remaining_seconds:05.2f}"
    except (ValueError, TypeError):
        return '--:--:--'

@app.route('/get_leaderboard_data')
def get_leaderboard_data():
    page = request.args.get('page', 1, type=int)
    items_per_page = request.args.get('items_per_page', 10, type=int)
    
    # Ensure items_per_page is a multiple of 10
    if items_per_page % 10 != 0:
        items_per_page = (items_per_page // 10 + 1) * 10  # Round up to the nearest multiple of 10
    
    start = (page - 1) * items_per_page

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Fetch paginated records
    cursor.execute('''
        SELECT name, organization, time
        FROM records
        ORDER BY 
            CASE WHEN time IS NULL THEN 1 ELSE 0 END,
            CAST(time AS FLOAT) ASC
        LIMIT ? OFFSET ?
    ''', (items_per_page, start))
    records = cursor.fetchall()
    
    # Fetch total number of records
    cursor.execute('SELECT COUNT(*) FROM records')
    total_items = cursor.fetchone()[0]
    conn.close()
    
    # Format leaderboard data
    leaderboard_data = []
    for i, record in enumerate(records, start=start + 1):
        time_formatted = seconds_to_time_format(record[2])  # Format the time
        leaderboard_data.append({
            'rank': i,
            'name': record[0],
            'organization': record[1],
            'time': time_formatted
        })
    
    # Pad the leaderboard_data with placeholder entries if there are fewer than items_per_page records
    while len(leaderboard_data) < items_per_page:
        leaderboard_data.append({
            'rank': len(leaderboard_data) + 1 + start,
            'name': '---',
            'organization': '---',
            'time': '--:--:--'
        })
    
    return jsonify({'items': leaderboard_data, 'totalItems': total_items})
    

@app.route('/get_racer_details/<int:id>')
def get_racer_details(id):
    print("hello- race-ready is clicked") 
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT r.*, rt.time 
        FROM records r
        LEFT JOIN race_times rt ON r.id = rt.rider_id
        WHERE r.id = ?
        ORDER BY rt.id DESC
        LIMIT 1
    ''', (id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        racer_data = {
            'name': row[2],
            'age': row[5],
            'organization': row[4],
            'address': row[3],
            'image': url_for('static', filename=f'images/{row[6]}') if row[6] else url_for('static', filename='images/collectors/stock.png'),
            # 'time': seconds_to_time_format(row[7])
        }
        return jsonify(racer_data)
    
    return jsonify({'error': 'Racer not found'}), 404

@app.route('/announcement', methods=['POST'])
def update_announcement():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    new_announcement = request.form['announcement']
    # Save the new announcement to a file or database
    with open('announcement.txt', 'w') as f:
        f.write(new_announcement)
    return redirect(url_for('index'))

@app.route('/title', methods=['POST'])
def update_title():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    new_title = request.form['title']
    # Save the new title to a file or database
    with open('title.txt', 'w') as f:
        f.write(new_title)
    return redirect(url_for('index'))

def get_announcement():
    try:
        with open('announcement.txt', 'r') as f:
            return f.read()
    except FileNotFoundError:
        return "This is a sample announcement"

def get_title():
    try:
        with open('title.txt', 'r') as f:
            return f.read()
    except FileNotFoundError:
        return "HORSE RACING ASSOCIATION"
    
@app.route('/get_title')
def get_title_route():
    return jsonify({'title': get_title()})

@app.route('/get_announcement')
def get_announcement_route():
    return jsonify({'announcement': get_announcement()})

if __name__ == '__main__':
    init_db()  # Ensure the database and table are created
    
    # Define the host and port
    host = '0.0.0.0'  # This makes it accessible on all network interfaces
    port = 5000
    
    # Get all IP addresses where the server is accessible
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print(f"\nServer is running at:")
    print(f"- http://127.0.0.1:{port}")
    print(f"- http://{local_ip}:{port}")
    print(f"(Press Ctrl+C to quit)\n")
    
    socketio.run(app, host=host, port=port, debug=True, allow_unsafe_werkzeug=True)
