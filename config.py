import os

# المجلدات
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
CV_FOLDER = os.path.join(UPLOAD_FOLDER, 'cvs')
VIDEO_FOLDER = os.path.join(UPLOAD_FOLDER, 'videos')
COMPANY_LOGOS = os.path.join(UPLOAD_FOLDER, 'logos')

# إنشاء المجلدات إذا لم تكن موجودة
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CV_FOLDER, exist_ok=True)
os.makedirs(VIDEO_FOLDER, exist_ok=True)
os.makedirs(COMPANY_LOGOS, exist_ok=True)

# قيود الحجم (بايت)
MAX_CV_SIZE = 5 * 1024 * 1024  # 5MB
MAX_VIDEO_SIZE = 60 * 1024 * 1024  # 60MB
MAX_LOGO_SIZE = 2 * 1024 * 1024  # 2MB

# الامتدادات المسموحة
ALLOWED_CV = {'pdf', 'doc', 'docx'}
ALLOWED_VIDEO = {'mp4', 'avi', 'mov', 'mkv'}
ALLOWED_IMAGES = {'png', 'jpg', 'jpeg', 'gif'}

# قاعدة البيانات
DATABASE = os.path.join(BASE_DIR, 'بوابتي_للتوظيف.db')

# إعدادات الأمان
SECRET_KEY = 'بوابتي-للتوظيف-اليمن-2024-سر-آمن'

# إعدادات الموقع
SITE_NAME = 'بوابتي للتوظيف'
SITE_DESCRIPTION = 'أفضل منصة توظيف يمنية تربط الشركات بأفضل الكفاءات'
CONTACT_EMAIL = 'info@bawabti.com'
CONTACT_PHONE = '+967 1 234 567'

# فئات الوظائف
JOB_CATEGORIES = [
    'تكنولوجيا المعلومات',
    'المبيعات والتسويق',
    'المحاسبة والمالية',
    'الموارد البشرية',
    'الهندسة',
    'التعليم',
    'الصحة',
    'السياحة والفنادق',
    'الإدارة',
    'أخرى'
]

# أنواع الوظائف
JOB_TYPES = [
    'دوام كامل',
    'دوام جزئي',
    'عمل حر',
    'تدريب',
    'عن بُعد'
]

# مستويات الخبرة
EXPERIENCE_LEVELS = [
    'مبتدئ (أقل من سنة)',
    'مبتدئ - متوسط (1-3 سنوات)',
    'متوسط (3-5 سنوات)',
    'متقدم (5-10 سنوات)',
    'خبير (أكثر من 10 سنوات)'
]
