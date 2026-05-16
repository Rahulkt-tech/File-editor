from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from pdf_utils import merge_pdfs, split_pdf, rotate_pdf, remove_pages, extract_text_from_pdf
from summariser import summarise_text

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'outputs')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY') or 'change_this_secret_key'

# Simple admin authentication
ADMIN_USER = os.environ.get('ADMIN_USER') or 'admin'
ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH') or generate_password_hash('admin123')

# ---------------- LOGIN REQUIRED DECORATOR ----------------
def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('user'):
            return redirect(url_for('login'))
        return fn(*args, **kwargs)
    return wrapper

# ---------------- LOGIN PAGE ----------------
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if username == ADMIN_USER and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['user'] = username
            return redirect(url_for('dashboard'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        flash('Registration is not supported in this demo. Please login with admin credentials.', 'warning')
        return redirect(url_for('login'))
    return render_template('register.html')

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# ---------------- FILE SAVE ----------------
def is_uploaded_file(f):
    return bool(f and getattr(f, 'filename', '').strip())

def save_upload(f):
    if not is_uploaded_file(f):
        raise ValueError('No uploaded file provided')
    filename = secure_filename(f.filename)
    if not filename:
        raise ValueError('Invalid file name')
    base, ext = os.path.splitext(filename)
    unique_name = f"{base}_{os.urandom(6).hex()}{ext}"
    path = os.path.join(UPLOAD_FOLDER, unique_name)
    f.save(path)
    return path

def safe_send_file(path):
    download_name = os.path.basename(path)
    try:
        return send_file(path, as_attachment=True, download_name=download_name)
    except TypeError:
        return send_file(path, as_attachment=True, attachment_filename=download_name)

# ---------------- PDF MERGE ----------------
@app.route('/merge', methods=['POST'])
@login_required
def web_merge():
    files = [f for f in request.files.getlist('pdfs') if is_uploaded_file(f)]
    if not files:
        flash('No files uploaded', 'warning')
        return redirect(url_for('dashboard'))
    try:
        paths = [save_upload(f) for f in files]
        out = os.path.join(OUTPUT_FOLDER, f"merged_{os.urandom(6).hex()}.pdf")
        merge_pdfs(paths, out)
        return safe_send_file(out)
    except Exception as err:
        flash(f'Error merging PDFs: {err}', 'danger')
        return redirect(url_for('dashboard'))

# ---------------- PDF SPLIT ----------------
@app.route('/split', methods=['POST'])
@login_required
def web_split():
    f = request.files.get('pdf')
    if not is_uploaded_file(f):
        flash('No file uploaded', 'warning')
        return redirect(url_for('dashboard'))
    try:
        start = int(request.form.get('start', '1'))
        end = int(request.form.get('end', '1'))
    except ValueError:
        flash('Invalid page values provided', 'warning')
        return redirect(url_for('dashboard'))
    if start < 1 or end < start:
        flash('Start page must be at least 1 and end page must be greater than or equal to start page', 'warning')
        return redirect(url_for('dashboard'))

    try:
        infile = save_upload(f)
        out = os.path.join(OUTPUT_FOLDER, f"split_{os.urandom(6).hex()}.pdf")
        split_pdf(infile, out, start, end)
        return safe_send_file(out)
    except Exception as err:
        flash(f'Error splitting PDF: {err}', 'danger')
        return redirect(url_for('dashboard'))

# ---------------- PDF ROTATE ----------------
@app.route('/rotate', methods=['POST'])
@login_required
def web_rotate():
    f = request.files.get('pdf')
    if not is_uploaded_file(f):
        flash('No file uploaded', 'warning')
        return redirect(url_for('dashboard'))
    try:
        angle = int(request.form.get('angle', '90'))
    except ValueError:
        flash('Rotation angle must be a number', 'warning')
        return redirect(url_for('dashboard'))
    try:
        infile = save_upload(f)
        out = os.path.join(OUTPUT_FOLDER, f"rotated_{os.urandom(6).hex()}.pdf")
        rotate_pdf(infile, out, angle)
        return safe_send_file(out)
    except Exception as err:
        flash(f'Error rotating PDF: {err}', 'danger')
        return redirect(url_for('dashboard'))

# ---------------- REMOVE PAGES ----------------
@app.route('/remove_pages', methods=['POST'])
@login_required
def web_remove_pages():
    f = request.files.get('pdf')
    pages_spec = request.form.get('pages', '')
    if not is_uploaded_file(f) or not pages_spec.strip():
        flash('Provide file and pages to remove', 'warning')
        return redirect(url_for('dashboard'))
    pages = [int(x.strip()) for x in pages_spec.split(',') if x.strip().isdigit()]
    if not pages:
        flash('Enter one or more valid page numbers to remove', 'warning')
        return redirect(url_for('dashboard'))
    try:
        infile = save_upload(f)
        out = os.path.join(OUTPUT_FOLDER, f"removed_{os.urandom(6).hex()}.pdf")
        remove_pages(infile, out, pages)
        return safe_send_file(out)
    except Exception as err:
        flash(f'Error removing pages: {err}', 'danger')
        return redirect(url_for('dashboard'))

# ---------------- SUMMARISE ----------------
@app.route('/summarise', methods=['POST'])
@login_required
def web_summarise():
    f = request.files.get('pdf')
    if not is_uploaded_file(f):
        flash('No file uploaded', 'warning')
        return redirect(url_for('dashboard'))
    try:
        infile = save_upload(f)
        text = extract_text_from_pdf(infile)
        if not text.strip():
            flash('No extractable text found in the PDF', 'warning')
            return redirect(url_for('dashboard'))
        summary = summarise_text(text, 5)
        out = os.path.join(OUTPUT_FOLDER, f"summary_{os.urandom(6).hex()}.txt")
        with open(out, 'w', encoding='utf-8') as fh:
            fh.write(summary)
        return safe_send_file(out)
    except Exception as err:
        flash(f'Error summarising PDF: {err}', 'danger')
        return redirect(url_for('dashboard'))

# ---------------- MAIN ----------------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
