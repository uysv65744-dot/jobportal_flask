from flask import Flask, request, jsonify, send_from_directory, render_template, redirect, url_for
from flask_cors import CORS
import os
import sqlite3
from werkzeug.utils import secure_filename
import config

app = Flask(__name__)
CORS(app)

app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
app.config['CV_FOLDER'] = config.CV_FOLDER
app.config['VIDEO_FOLDER'] = config.VIDEO_FOLDER
app.config['MAX_CONTENT_LENGTH'] = config.MAX_VIDEO_SIZE + config.MAX_CV_SIZE

os.makedirs(app.config['CV_FOLDER'], exist_ok=True)
os.makedirs(app.config['VIDEO_FOLDER'], exist_ok=True)

# قاعدة بيانات SQLite صغيرة
def get_db_connection():
    conn = sqlite3.connect(config.DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        company TEXT,
        location TEXT,
        description TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS applicants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER,
        full_name TEXT,
        email TEXT,
        phone TEXT,
        cv_path TEXT,
        video_path TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

init_db()


def allowed_file(filename, allowed_exts):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in allowed_exts


@app.route('/')
def index():
    conn = get_db_connection()
    jobs = conn.execute('SELECT * FROM jobs ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('index.html', jobs=jobs)


@app.route('/api/jobs/', methods=['GET'])
def api_jobs():
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM jobs ORDER BY created_at DESC').fetchall()
    jobs = [dict(row) for row in rows]
    conn.close()
    return jsonify(jobs)


@app.route('/api/upload', methods=['POST'])
def api_upload():
    full_name = request.form.get('full_name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    job_id = request.form.get('job_id')

    if not full_name or not email:
        return jsonify({'error': 'يرجى إدخال الاسم والبريد الإلكتروني'}), 400

    cv_file = request.files.get('cv')
    video_file = request.files.get('intro_video')

    cv_path = None
    video_path = None

    # رفع السيرة الذاتية
    if cv_file:
        filename = secure_filename(cv_file.filename)
        if not allowed_file(filename, config.ALLOWED_CV):
            return jsonify({'error': 'نوع السيرة الذاتية غير مدعوم'}), 400
        cv_file.seek(0, os.SEEK_END)
        if cv_file.tell() > config.MAX_CV_SIZE:
            return jsonify({'error': 'حجم السيرة الذاتية كبير (5MB كحد أقصى)'}), 400
        cv_file.seek(0)
        save_name = f"cv_{int(__import__('time').time())}_{filename}"
        save_path = os.path.join(app.config['CV_FOLDER'], save_name)
        cv_file.save(save_path)
        cv_path = f"/uploads/cvs/{save_name}"

    # رفع الفيديو
    if video_file:
        filename = secure_filename(video_file.filename)
        if not allowed_file(filename, config.ALLOWED_VIDEO):
            return jsonify({'error': 'نوع الفيديو غير مدعوم'}), 400
        video_file.seek(0, os.SEEK_END)
        if video_file.tell() > config.MAX_VIDEO_SIZE:
            return jsonify({'error': 'حجم الفيديو كبير (60MB كحد أقصى)'}), 400
        video_file.seek(0)
        save_name = f"video_{int(__import__('time').time())}_{filename}"
        save_path = os.path.join(app.config['VIDEO_FOLDER'], save_name)
        video_file.save(save_path)
        video_path = f"/uploads/videos/{save_name}"

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO applicants (job_id, full_name, email, phone, cv_path, video_path) VALUES (?, ?, ?, ?, ?, ?)',
                (job_id, full_name, email, phone, cv_path, video_path))
    conn.commit()
    conn.close()

    return jsonify({'message': 'تم رفع الطلب بنجاح ✅', 'cv': cv_path, 'video': video_path}), 201


@app.route('/uploads/cvs/<path:filename>')
def uploaded_cv(filename):
    return send_from_directory(app.config['CV_FOLDER'], filename)


@app.route('/uploads/videos/<path:filename>')
def uploaded_video(filename):
    return send_from_directory(app.config['VIDEO_FOLDER'], filename)


@app.route('/add_job', methods=['POST'])
def add_job():
    title = request.form.get('title')
    company = request.form.get('company')
    location = request.form.get('location')
    description = request.form.get('description')
    if not title:
        return redirect(url_for('index'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO jobs (title, company, location, description) VALUES (?, ?, ?, ?)',
                (title, company, location, description))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
