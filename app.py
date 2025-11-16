from flask import Flask, request, jsonify, send_from_directory, render_template, redirect, url_for, session, flash
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
import os
import sqlite3
from werkzeug.utils import secure_filename
from datetime import datetime
import re

app = Flask(__name__)

# ==============================
# ⚙️ الإعدادات
# ==============================

# المجلدات
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
CV_FOLDER = os.path.join(UPLOAD_FOLDER, 'cvs')
VIDEO_FOLDER = os.path.join(UPLOAD_FOLDER, 'videos')

# إنشاء المجلدات إذا لم تكن موجودة
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CV_FOLDER, exist_ok=True)
os.makedirs(VIDEO_FOLDER, exist_ok=True)

# قيود الحجم (بايت)
MAX_CV_SIZE = 5 * 1024 * 1024  # 5MB
MAX_VIDEO_SIZE = 60 * 1024 * 1024  # 60MB

# الامتدادات المسموحة
ALLOWED_CV = {'pdf', 'doc', 'docx'}
ALLOWED_VIDEO = {'mp4', 'avi', 'mov', 'mkv'}

# قاعدة البيانات
DATABASE = os.path.join(BASE_DIR, 'بوابتي_للتوظيف.db')

# إعدادات التطبيق
app.config['SECRET_KEY'] = 'بوابتي-للتوظيف-اليمن-2024-سر-آمن'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CV_FOLDER'] = CV_FOLDER
app.config['VIDEO_FOLDER'] = VIDEO_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_VIDEO_SIZE + MAX_CV_SIZE
app.config['DATABASE'] = DATABASE

CORS(app)

# Rate Limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

# ==============================
# 🗄️ قاعدة البيانات
# ==============================

def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # جدول المستخدمين (شركات)
    cur.execute('''CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        phone TEXT,
        location TEXT,
        description TEXT,
        logo_path TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT 1
    )''')
    
    # جدول الوظائف
    cur.execute('''CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        title TEXT NOT NULL,
        category TEXT,
        job_type TEXT,
        salary_range TEXT,
        location TEXT,
        description TEXT,
        requirements TEXT,
        benefits TEXT,
        experience_level TEXT,
        deadline DATE,
        is_active BOOLEAN DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (company_id) REFERENCES companies (id)
    )''')
    
    # جدول المتقدمين
    cur.execute('''CREATE TABLE IF NOT EXISTS applicants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT,
        cv_path TEXT,
        video_path TEXT,
        cover_letter TEXT,
        status TEXT DEFAULT 'جديد',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (job_id) REFERENCES jobs (id)
    )''')
    
    # إضافة بيانات تجريبية
    try:
        # شركة تجريبية
        cur.execute('''INSERT OR IGNORE INTO companies 
                     (name, email, password, phone, location, description) 
                     VALUES (?, ?, ?, ?, ?, ?)''',
                   ('شركة تطوير يمن', 'info@yemen-dev.com', 
                    generate_password_hash('123456'), '+967123456789', 
                    'صنعاء', 'شركة رائدة في مجال التطوير البرمجي في اليمن'))
        
        # وظائف تجريبية
        cur.execute('''INSERT OR IGNORE INTO jobs 
                     (company_id, title, category, job_type, salary_range, location, description, requirements) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                   (1, 'مطور ويب', 'تكنولوجيا المعلومات', 'دوام كامل', 
                    '500,000 - 800,000 ريال', 'صنعاء', 
                    'مطلوب مطور ويب مبتدئ للانضمام لفريقنا المتميز', 
                    'خبرة في HTML, CSS, JavaScript\nشهادة جامعية في تخصص الحاسوب'))
        
        cur.execute('''INSERT OR IGNORE INTO jobs 
                     (company_id, title, category, job_type, salary_range, location, description) 
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                   (1, 'مدير مبيعات', 'المبيعات والتسويق', 'دوام كامل', 
                    '600,000 - 900,000 ريال', 'تعز', 
                    'مطلوب مدير مبيعات لديه خبرة في السوق اليمني'))
    
    except:
        pass
    
    conn.commit()
    conn.close()

init_db()

# ==============================
# 🛠️ الدوال المساعدة
# ==============================

def allowed_file(filename, allowed_exts):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in allowed_exts

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'company_id' not in session:
            return redirect(url_for('company_login'))
        return f(*args, **kwargs)
    return decorated_function

# ==============================
# 🏠 الصفحات الرئيسية
# ==============================

@app.route('/')
def index():
    conn = get_db_connection()
    featured_jobs = conn.execute('''
        SELECT j.*, c.name as company_name 
        FROM jobs j 
        JOIN companies c ON j.company_id = c.id 
        WHERE j.is_active = 1 
        ORDER BY j.created_at DESC 
        LIMIT 6
    ''').fetchall()
    
    stats = {
        'total_jobs': conn.execute('SELECT COUNT(*) FROM jobs WHERE is_active = 1').fetchone()[0],
        'total_companies': conn.execute('SELECT COUNT(*) FROM companies WHERE is_active = 1').fetchone()[0],
        'total_applicants': conn.execute('SELECT COUNT(*) FROM applicants').fetchone()[0]
    }
    conn.close()
    
    return render_template('index.html', 
                         featured_jobs=featured_jobs, 
                         stats=stats)

@app.route('/jobs')
def jobs():
    category = request.args.get('category', '')
    job_type = request.args.get('type', '')
    location = request.args.get('location', '')
    
    conn = get_db_connection()
    
    query = '''
        SELECT j.*, c.name as company_name, c.location as company_location 
        FROM jobs j 
        JOIN companies c ON j.company_id = c.id 
        WHERE j.is_active = 1
    '''
    params = []
    
    if category:
        query += ' AND j.category = ?'
        params.append(category)
    if job_type:
        query += ' AND j.job_type = ?'
        params.append(job_type)
    if location:
        query += ' AND (j.location LIKE ? OR c.location LIKE ?)'
        params.append(f'%{location}%')
        params.append(f'%{location}%')
    
    query += ' ORDER BY j.created_at DESC'
    jobs_list = conn.execute(query, params).fetchall()
    
    categories = conn.execute('SELECT DISTINCT category FROM jobs WHERE category IS NOT NULL').fetchall()
    job_types = conn.execute('SELECT DISTINCT job_type FROM jobs WHERE job_type IS NOT NULL').fetchall()
    
    conn.close()
    
    return render_template('jobs.html', 
                         jobs=jobs_list, 
                         categories=categories,
                         job_types=job_types,
                         selected_category=category,
                         selected_type=job_type,
                         selected_location=location)

# ==============================
# 👥 تسجيل الشركات
# ==============================

@app.route('/company/register', methods=['GET', 'POST'])
def company_register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phone')
        location = request.form.get('location')
        description = request.form.get('description')
        
        if not name or not email or not password:
            flash('يرجى ملء جميع الحقول الإلزامية', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('كلمة المرور يجب أن تكون 6 أحرف على الأقل', 'error')
            return render_template('register.html')
        
        hashed_password = generate_password_hash(password)
        
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute('''INSERT INTO companies (name, email, password, phone, location, description) 
                         VALUES (?, ?, ?, ?, ?, ?)''',
                       (name, email, hashed_password, phone, location, description))
            conn.commit()
            company_id = cur.lastrowid
            conn.close()
            
            session['company_id'] = company_id
            session['company_name'] = name
            flash('تم تسجيل الشركة بنجاح!', 'success')
            return redirect(url_for('company_dashboard'))
            
        except sqlite3.IntegrityError:
            conn.close()
            flash('البريد الإلكتروني أو اسم الشركة مسجل مسبقاً', 'error')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/company/login', methods=['GET', 'POST'])
def company_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = get_db_connection()
        company = conn.execute('SELECT * FROM companies WHERE email = ? AND is_active = 1', (email,)).fetchone()
        conn.close()
        
        if company and check_password_hash(company['password'], password):
            session['company_id'] = company['id']
            session['company_name'] = company['name']
            flash('تم تسجيل الدخول بنجاح!', 'success')
            return redirect(url_for('company_dashboard'))
        else:
            flash('البريد الإلكتروني أو كلمة المرور غير صحيحة', 'error')
    
    return render_template('login.html')

@app.route('/company/logout')
def company_logout():
    session.clear()
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('index'))

# ==============================
# 🎛️ لوحة تحكم الشركة
# ==============================

@app.route('/company/dashboard')
@login_required
def company_dashboard():
    conn = get_db_connection()
    
    company_id = session['company_id']
    
    # إحصائيات الشركة
    stats = {
        'total_jobs': conn.execute('SELECT COUNT(*) FROM jobs WHERE company_id = ?', (company_id,)).fetchone()[0],
        'active_jobs': conn.execute('SELECT COUNT(*) FROM jobs WHERE company_id = ? AND is_active = 1', (company_id,)).fetchone()[0],
        'total_applicants': conn.execute('''SELECT COUNT(*) FROM applicants a 
                                         JOIN jobs j ON a.job_id = j.id 
                                         WHERE j.company_id = ?''', (company_id,)).fetchone()[0],
        'new_applicants': conn.execute('''SELECT COUNT(*) FROM applicants a 
                                       JOIN jobs j ON a.job_id = j.id 
                                       WHERE j.company_id = ? AND a.status = 'جديد' ''', (company_id,)).fetchone()[0]
    }
    
    # أحدث الوظائف
    jobs_list = conn.execute('''
        SELECT * FROM jobs 
        WHERE company_id = ? 
        ORDER BY created_at DESC 
        LIMIT 5
    ''', (company_id,)).fetchall()
    
    # أحدث المتقدمين
    recent_applicants = conn.execute('''
        SELECT a.*, j.title as job_title 
        FROM applicants a 
        JOIN jobs j ON a.job_id = j.id 
        WHERE j.company_id = ? 
        ORDER BY a.created_at DESC 
        LIMIT 10
    ''', (company_id,)).fetchall()
    
    conn.close()
    
    return render_template('company_dashboard.html',
                         stats=stats,
                         jobs=jobs_list,
                         applicants=recent_applicants)

# ==============================
# 💼 إدارة الوظائف
# ==============================

@app.route('/company/jobs')
@login_required
def company_jobs():
    conn = get_db_connection()
    jobs_list = conn.execute('''
        SELECT * FROM jobs 
        WHERE company_id = ? 
        ORDER BY created_at DESC
    ''', (session['company_id'],)).fetchall()
    conn.close()
    return render_template('company_jobs.html', jobs=jobs_list)

@app.route('/company/jobs/add', methods=['GET', 'POST'])
@login_required
def add_job():
    if request.method == 'POST':
        title = request.form.get('title')
        category = request.form.get('category')
        job_type = request.form.get('job_type')
        salary_range = request.form.get('salary_range')
        location = request.form.get('location')
        description = request.form.get('description')
        requirements = request.form.get('requirements')
        benefits = request.form.get('benefits')
        experience_level = request.form.get('experience_level')
        deadline = request.form.get('deadline')
        
        if not title:
            flash('يرجى إدخال عنوان الوظيفة', 'error')
            return render_template('add_job.html')
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''INSERT INTO jobs 
                     (company_id, title, category, job_type, salary_range, location, 
                      description, requirements, benefits, experience_level, deadline) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                   (session['company_id'], title, category, job_type, salary_range, location,
                    description, requirements, benefits, experience_level, deadline))
        conn.commit()
        conn.close()
        
        flash('تم إضافة الوظيفة بنجاح!', 'success')
        return redirect(url_for('company_jobs'))
    
    return render_template('add_job.html')

# ==============================
# 👤 إدارة المتقدمين
# ==============================

@app.route('/company/applicants')
@login_required
def company_applicants():
    conn = get_db_connection()
    applicants = conn.execute('''
        SELECT a.*, j.title as job_title, c.name as company_name 
        FROM applicants a 
        JOIN jobs j ON a.job_id = j.id 
        JOIN companies c ON j.company_id = c.id 
        WHERE j.company_id = ? 
        ORDER BY a.created_at DESC
    ''', (session['company_id'],)).fetchall()
    conn.close()
    return render_template('company_applicants.html', applicants=applicants)

@app.route('/company/applicants/<int:applicant_id>/update_status', methods=['POST'])
@login_required
def update_applicant_status(applicant_id):
    new_status = request.form.get('status')
    
    conn = get_db_connection()
    conn.execute('UPDATE applicants SET status = ? WHERE id = ?', (new_status, applicant_id))
    conn.commit()
    conn.close()
    
    flash('تم تحديث حالة المتقدم بنجاح', 'success')
    return redirect(url_for('company_applicants'))

# ==============================
# 📤 التقديم على الوظائف (للمتقدمين)
# ==============================

@app.route('/apply/<int:job_id>', methods=['GET', 'POST'])
def apply_job(job_id):
    conn = get_db_connection()
    job = conn.execute('''
        SELECT j.*, c.name as company_name 
        FROM jobs j 
        JOIN companies c ON j.company_id = c.id 
        WHERE j.id = ? AND j.is_active = 1
    ''', (job_id,)).fetchone()
    
    if not job:
        conn.close()
        flash('الوظيفة غير متاحة', 'error')
        return redirect(url_for('jobs'))
    
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        cover_letter = request.form.get('cover_letter')
        
        cv_file = request.files.get('cv')
        video_file = request.files.get('intro_video')
        
        if not full_name or not email:
            flash('يرجى إدخال الاسم والبريد الإلكتروني', 'error')
            return render_template('apply_job.html', job=job)
        
        cv_path = None
        video_path = None
        
        # رفع السيرة الذاتية
        if cv_file and cv_file.filename:
            filename = secure_filename(cv_file.filename)
            if not allowed_file(filename, ALLOWED_CV):
                flash('نوع السيرة الذاتية غير مدعوم', 'error')
                return render_template('apply_job.html', job=job)
            
            cv_file.seek(0, os.SEEK_END)
            if cv_file.tell() > MAX_CV_SIZE:
                flash('حجم السيرة الذاتية كبير (5MB كحد أقصى)', 'error')
                return render_template('apply_job.html', job=job)
            cv_file.seek(0)
            
            save_name = f"cv_{int(datetime.now().timestamp())}_{filename}"
            save_path = os.path.join(app.config['CV_FOLDER'], save_name)
            cv_file.save(save_path)
            cv_path = f"/uploads/cvs/{save_name}"
        
        # رفع الفيديو
        if video_file and video_file.filename:
            filename = secure_filename(video_file.filename)
            if not allowed_file(filename, ALLOWED_VIDEO):
                flash('نوع الفيديو غير مدعوم', 'error')
                return render_template('apply_job.html', job=job)
            
            video_file.seek(0, os.SEEK_END)
            if video_file.tell() > MAX_VIDEO_SIZE:
                flash('حجم الفيديو كبير (60MB كحد أقصى)', 'error')
                return render_template('apply_job.html', job=job)
            video_file.seek(0)
            
            save_name = f"video_{int(datetime.now().timestamp())}_{filename}"
            save_path = os.path.join(app.config['VIDEO_FOLDER'], save_name)
            video_file.save(save_path)
            video_path = f"/uploads/videos/{save_name}"
        
        # حفظ بيانات المتقدم
        cur = conn.cursor()
        cur.execute('''INSERT INTO applicants (job_id, full_name, email, phone, cv_path, video_path, cover_letter) 
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                   (job_id, full_name, email, phone, cv_path, video_path, cover_letter))
        conn.commit()
        conn.close()
        
        flash('تم تقديم طلبك بنجاح! سنقوم بمراجعته قريباً.', 'success')
        return redirect(url_for('job_details', job_id=job_id))
    
    conn.close()
    return render_template('apply_job.html', job=job)

@app.route('/job/<int:job_id>')
def job_details(job_id):
    conn = get_db_connection()
    job = conn.execute('''
        SELECT j.*, c.name as company_name, c.location as company_location, 
               c.description as company_description, c.phone as company_phone 
        FROM jobs j 
        JOIN companies c ON j.company_id = c.id 
        WHERE j.id = ? AND j.is_active = 1
    ''', (job_id,)).fetchone()
    conn.close()
    
    if not job:
        flash('الوظيفة غير متاحة', 'error')
        return redirect(url_for('jobs'))
    
    return render_template('job_details.html', job=job)

# ==============================
# 📱 واجهات API للتطبيق
# ==============================

@app.route('/api/jobs/', methods=['GET'])
def api_jobs():
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT j.*, c.name as company_name 
        FROM jobs j 
        JOIN companies c ON j.company_id = c.id 
        WHERE j.is_active = 1 
        ORDER BY j.created_at DESC
    ''').fetchall()
    jobs_list = [dict(row) for row in rows]
    conn.close()
    return jsonify(jobs_list)

@app.route('/api/upload', methods=['POST'])
@limiter.limit("10 per minute")
def api_upload():
    try:
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        job_id = request.form.get('job_id')
        cover_letter = request.form.get('cover_letter')

        if not full_name or not email:
            return jsonify({'error': 'يرجى إدخال الاسم والبريد الإلكتروني'}), 400

        cv_file = request.files.get('cv')
        video_file = request.files.get('intro_video')

        cv_path = None
        video_path = None

        # رفع السيرة الذاتية
        if cv_file and cv_file.filename:
            filename = secure_filename(cv_file.filename)
            if not allowed_file(filename, ALLOWED_CV):
                return jsonify({'error': 'نوع السيرة الذاتية غير مدعوم'}), 400
            
            cv_file.seek(0, os.SEEK_END)
            if cv_file.tell() > MAX_CV_SIZE:
                return jsonify({'error': 'حجم السيرة الذاتية كبير (5MB كحد أقصى)'}), 400
            cv_file.seek(0)
            
            save_name = f"cv_{int(datetime.now().timestamp())}_{filename}"
            save_path = os.path.join(app.config['CV_FOLDER'], save_name)
            cv_file.save(save_path)
            cv_path = f"/uploads/cvs/{save_name}"

        # رفع الفيديو
        if video_file and video_file.filename:
            filename = secure_filename(video_file.filename)
            if not allowed_file(filename, ALLOWED_VIDEO):
                return jsonify({'error': 'نوع الفيديو غير مدعوم'}), 400
            
            video_file.seek(0, os.SEEK_END)
            if video_file.tell() > MAX_VIDEO_SIZE:
                return jsonify({'error': 'حجم الفيديو كبير (60MB كحد أقصى)'}), 400
            video_file.seek(0)
            
            save_name = f"video_{int(datetime.now().timestamp())}_{filename}"
            save_path = os.path.join(app.config['VIDEO_FOLDER'], save_name)
            video_file.save(save_path)
            video_path = f"/uploads/videos/{save_name}"

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''INSERT INTO applicants (job_id, full_name, email, phone, cv_path, video_path, cover_letter) 
                      VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (job_id, full_name, email, phone, cv_path, video_path, cover_letter))
        conn.commit()
        applicant_id = cur.lastrowid
        conn.close()

        return jsonify({
            'success': True,
            'message': 'تم تقديم طلبك بنجاح! سنقوم بمراجعته قريباً.', 
            'cv': cv_path, 
            'video': video_path,
            'applicant_id': applicant_id
        }), 201

    except Exception as e:
        return jsonify({'error': f'حدث خطأ أثناء معالجة الطلب: {str(e)}'}), 500

@app.route('/upload_cv', methods=['POST'])
@limiter.limit("20 per minute")
def upload_cv():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'لم يتم استقبال أي ملف'}), 400

    filename = secure_filename(file.filename)
    if not allowed_file(filename, ALLOWED_CV):
        return jsonify({'error': 'نوع السيرة الذاتية غير مدعوم'}), 400

    file.seek(0, os.SEEK_END)
    if file.tell() > MAX_CV_SIZE:
        return jsonify({'error': 'حجم الملف كبير (5MB كحد أقصى)'}), 400
    file.seek(0)

    save_name = f"cv_{int(datetime.now().timestamp())}_{filename}"
    save_path = os.path.join(app.config['CV_FOLDER'], save_name)
    file.save(save_path)

    return jsonify({
        'message': 'تم رفع السيرة الذاتية بنجاح ✅',
        'path': f"/uploads/cvs/{save_name}"
    }), 200

@app.route('/upload_video', methods=['POST'])
@limiter.limit("10 per minute")
def upload_video():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'لم يتم استقبال أي ملف'}), 400

    filename = secure_filename(file.filename)
    if not allowed_file(filename, ALLOWED_VIDEO):
        return jsonify({'error': 'نوع الفيديو غير مدعوم'}), 400

    file.seek(0, os.SEEK_END)
    if file.tell() > MAX_VIDEO_SIZE:
        return jsonify({'error': 'حجم الفيديو كبير (60MB كحد أقصى)'}), 400
    file.seek(0)

    save_name = f"video_{int(datetime.now().timestamp())}_{filename}"
    save_path = os.path.join(app.config['VIDEO_FOLDER'], save_name)
    file.save(save_path)

    return jsonify({
        'message': 'تم رفع الفيديو بنجاح 🎥',
        'path': f"/uploads/videos/{save_name}"
    }), 200

# ==============================
# 📱 واجهة التقديم للموبايل
# ==============================

@app.route('/mobile/apply')
def mobile_apply():
    """واجهة التقديم للموبايل"""
    job_id = request.args.get('job_id', '1')
    job_title = request.args.get('job_title', 'وظيفة عامة')
    company_name = request.args.get('company_name', 'شركة')
    location = request.args.get('location', 'غير محدد')
    job_type = request.args.get('job_type', 'دوام كامل')
    
    return render_template('mobile_apply.html',
                         job_id=job_id,
                         job_title=job_title,
                         company_name=company_name,
                         location=location,
                         job_type=job_type)

# ==============================
# 🗂️ خدمة الملفات
# ==============================

@app.route('/uploads/cvs/<path:filename>')
def uploaded_cv(filename):
    return send_from_directory(app.config['CV_FOLDER'], filename)

@app.route('/uploads/videos/<path:filename>')
def uploaded_video(filename):
    return send_from_directory(app.config['VIDEO_FOLDER'], filename)

# ==============================
# 📈 إحصائيات API
# ==============================

@app.route('/api/stats')
def api_stats():
    conn = get_db_connection()
    
    total_jobs = conn.execute('SELECT COUNT(*) FROM jobs WHERE is_active = 1').fetchone()[0]
    total_companies = conn.execute('SELECT COUNT(*) FROM companies WHERE is_active = 1').fetchone()[0]
    total_applicants = conn.execute('SELECT COUNT(*) FROM applicants').fetchone()[0]
    recent_applications = conn.execute('''
        SELECT COUNT(*) FROM applicants 
        WHERE created_at >= datetime('now', '-7 days')
    ''').fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'total_jobs': total_jobs,
        'total_companies': total_companies,
        'total_applicants': total_applicants,
        'recent_applications': recent_applications
    })

# ==============================
# 🛠️ إصلاح المسارات الأساسية
# ==============================

@app.route('/favicon.ico')
def favicon():
    return '', 404

@app.route('/static/images/yemen-pattern.png')
def yemen_pattern():
    return '', 404

# ==============================
# 🧪 صفحات تجريبية
# ==============================

@app.route('/jobs-simple')
def jobs_simple():
    return '''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>الوظائف - بوابتي للتوظيف</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
            h1 { color: #ce1126; }
        </style>
    </head>
    <body>
        <h1>🎯 بوابتي للتوظيف</h1>
        <h2>صفحة الوظائف (تجريبية)</h2>
        <p>هذه صفحة تجريبية - سيتم تطويرها قريباً</p>
        <a href="/">العودة للرئيسية</a>
    </body>
    </html>
    '''

@app.route('/company/login-simple')
def login_simple():
    return '''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>تسجيل الدخول - بوابتي للتوظيف</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
            h1 { color: #ce1126; }
            form { max-width: 400px; margin: 0 auto; text-align: right; }
            input, button { width: 100%; padding: 10px; margin: 5px 0; }
        </style>
    </head>
    <body>
        <h1>🎯 بوابتي للتوظيف</h1>
        <h2>تسجيل الدخول (تجريبي)</h2>
        <form>
            <input type="email" placeholder="البريد الإلكتروني"><br>
            <input type="password" placeholder="كلمة المرور"><br>
            <button type="submit">تسجيل الدخول</button>
        </form>
        <a href="/">العودة للرئيسية</a>
    </body>
    </html>
    '''

@app.route('/test')
def test_page():
    return jsonify({
        'status': 'success',
        'message': 'التطبيق شغال بنجاح!',
        'routes': {
            'home': '/',
            'jobs': '/jobs', 
            'login': '/company/login',
            'register': '/company/register',
            'api_stats': '/api/stats',
            'mobile_apply': '/mobile/apply',
            'test': '/test'
        }
    })

# ==============================
# 🚀 تشغيل السيرفر
# ==============================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 60)
    print("🎯 بوابتي للتوظيف - منصة التوظيف اليمنية")
    print("🌐 التشغيل على:", f"http://0.0.0.0:{port}")
    print("📧 البريد: info@bawabti.com")
    print("📞 الهاتف: +967 1 234 567")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=False)
