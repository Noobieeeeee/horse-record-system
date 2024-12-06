import os
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Ensure the 'images' folder exists
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'images')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Configure file upload settings
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# In-memory database (for example purposes)
records = []

# Pagination configuration
ITEMS_PER_PAGE = 8

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Route to display records
@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    paginated_records = records[start:end]
    total_pages = (len(records) // ITEMS_PER_PAGE) + (1 if len(records) % ITEMS_PER_PAGE != 0 else 0)
    return render_template('index.html', records=paginated_records, page=page, total_pages=total_pages)

# Route to add a new record
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

    # Add record to the in-memory list
    record = {
        'id': len(records) + 1,
        'horse_number': horse_number,
        'name': name,
        'address': address,
        'organization': organization,
        'age': age,
        'image': image
    }
    records.append(record)
    
    return redirect(url_for('index'))

# Route to edit a record
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_record(id):
    record = next((r for r in records if r['id'] == id), None)
    if request.method == 'POST':
        record['horse_number'] = request.form['horse_number']
        record['name'] = request.form['name']
        record['address'] = request.form['address']
        record['organization'] = request.form['organization']
        record['age'] = request.form['age']

        # Handle image upload
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file and allowed_file(image_file.filename):
                image_filename = secure_filename(image_file.filename)
                image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
                record['image'] = image_filename

        return redirect(url_for('index'))
    
    return render_template('edit.html', record=record)

# Route to delete a record
@app.route('/delete/<int:id>', methods=['GET'])
def delete_record(id):
    global records
    records = [r for r in records if r['id'] != id]
    return redirect(url_for('index'))

# Route to show details of a record
@app.route('/details/<int:id>', methods=['GET'])
def details(id):
    record = next((r for r in records if r['id'] == id), None)
    return render_template('details.html', record=record)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
