import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
CV_FOLDER = os.path.join(UPLOAD_FOLDER, 'cvs')
VIDEO_FOLDER = os.path.join(UPLOAD_FOLDER, 'videos')

MAX_CV_SIZE = 5 * 1024 * 1024        # 5 MB
MAX_VIDEO_SIZE = 60 * 1024 * 1024    # 60 MB

ALLOWED_CV = {'pdf', 'doc', 'docx'}
ALLOWED_VIDEO = {'mp4', '3gp', 'mov'}

DATABASE = os.path.join(BASE_DIR, 'jobs.db')
