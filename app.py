import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
from flask import jsonify

# app = Flask(__name__)
app = Flask(__name__, static_folder='static')


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
    """Initialize the SQLite database with the required table."""
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
    conn.commit()
    conn.close()

@app.route('/')
def index():
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
    return render_template('index.html', records=paginated_records, page=page, total_pages=total_pages, total_racers=total_racers)


@app.route('/add', methods=['POST'])
def add_item():
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
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM records WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))


@app.route('/details/<int:id>', methods=['GET'])
def details(id):
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

@app.route('/leaderboard')
def leaderboard():
    return render_template('leaderboard.html')
# In app.py, add this new route:
#honestly have no idea this part works, stay tuned :P

@app.route('/api/leaderboard')
def get_leaderboard():
    page = request.args.get('page', 1, type=int)
    riders_per_page = 10
    offset = (page - 1) * riders_per_page
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Get paginated records
    cursor.execute('''
        SELECT id, horse_number, name, address, organization, age, image 
        FROM records 
        ORDER BY horse_number ASC 
        LIMIT ? OFFSET ?
    ''', (riders_per_page, offset))
    records = cursor.fetchall()
    
    # Get total count for pagination
    cursor.execute('SELECT COUNT(*) FROM records')
    total_records = cursor.fetchone()[0]
    
    # Convert to dictionary format
    riders = []
    for record in records:
        image_url = url_for('static', filename=f'images/{record[6]}') if record[6] else None
        riders.append({
            'id': record[0],
            'horse_number': record[1],
            'name': record[2],
            'address': record[3],
            'organization': record[4],
            'age': record[5],
            'img': image_url
        })
    
    return jsonify({
        'riders': riders,
        'total_records': total_records
    })

@app.route('/race')
def race():
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

if __name__ == '__main__':
    init_db()  # Ensure the database and table are created
    app.run(host='0.0.0.0', port=5000, debug=True)
