from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from database import db, ScanHistory
from classifier import TrashClassifier

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'trashtack-secret-2024-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trashtrack.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Initialize
db.init_app(app)
classifier = TrashClassifier()

# Create directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/examples/merah', exist_ok=True)
os.makedirs('static/examples/kuning', exist_ok=True)
os.makedirs('static/examples/hijau', exist_ok=True)

# Create database tables
with app.app_context():
    db.create_all()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scan', methods=['GET', 'POST'])
def scan():
    if request.method == 'POST':
        file = None
        manual_nama = request.form.get('nama_barang', '').strip()  # Ambil nama manual
        
        # Handle file upload
        if 'gambar' in request.files:
            file = request.files['gambar']
        elif 'gambar_data' in request.form:
            import base64
            from io import BytesIO
            from werkzeug.datastructures import FileStorage
            
            img_data = request.form['gambar_data']
            header, encoded = img_data.split(",", 1)
            data = base64.b64decode(encoded)
            file = FileStorage(stream=BytesIO(data), filename="scan_manual.jpg", content_type='image/jpeg')
        
        if not file or file.filename == '':
            flash('❌ Tidak ada gambar yang dipilih!', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = secure_filename(f"{timestamp}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # 🔥 KLASSIFIKASI BERDASARKAN NAMA MANUAL (100% Akurat)
            hasil = classifier.classify(filepath, original_filename=manual_nama)
            
            relative_path = f"uploads/{filename}"
            scan_entry = ScanHistory(
                sampah_nama=hasil['nama'],
                kategori=hasil['kategori'],
                confidence=hasil['confidence'],
                gambar_path=relative_path
            )
            db.session.add(scan_entry)
            db.session.commit()
            
            flash(f"✅ Berhasil! {hasil['nama']} → Tong {hasil['kategori'].upper()}", 'success')
            return redirect(url_for('result', scan_id=scan_entry.id))
        else:
            flash('❌ Format file salah! Gunakan JPG, JPEG, atau PNG.', 'error')
            return redirect(request.url)
    
    return render_template('scan.html')

@app.route('/result/<int:scan_id>')
def result(scan_id):
    scan = ScanHistory.query.get_or_404(scan_id)
    kategori_info = classifier.get_kategori_info(scan.kategori)
    return render_template('result.html', scan=scan, kategori_info=kategori_info)

@app.route('/detail/<int:scan_id>')
def detail(scan_id):
    scan = ScanHistory.query.get_or_404(scan_id)
    kategori_info = classifier.get_kategori_info(scan.kategori)
    return render_template('detail.html', scan=scan, kategori_info=kategori_info)

@app.route('/history')
def history():
    scans = ScanHistory.query.order_by(ScanHistory.tanggal.desc()).all()
    
    # Statistics
    stats = {
        'total': len(scans),
        'merah': len([s for s in scans if s.kategori == 'merah']),
        'kuning': len([s for s in scans if s.kategori == 'kuning']),
        'hijau': len([s for s in scans if s.kategori == 'hijau'])
    }
    
    return render_template('history.html', scans=scans, stats=stats)

@app.route('/education')
def education():
    kategori = {
        'merah': classifier.get_kategori_info('merah'),
        'kuning': classifier.get_kategori_info('kuning'),
        'hijau': classifier.get_kategori_info('hijau')
    }
    return render_template('education.html', kategori=kategori)

@app.route('/update/<int:scan_id>', methods=['POST'])
def update_classification(scan_id):
    """Fitur koreksi manual"""
    scan = ScanHistory.query.get_or_404(scan_id)
    scan.kategori = request.form['kategori']
    scan.confidence = 100
    
    # Update nama berdasarkan kategori yang dipilih
    nama_map = {
        'merah': 'Limbah B3 (Dikoreksi)',
        'kuning': 'Sampah Anorganik (Dikoreksi)',
        'hijau': 'Sampah Organik (Dikoreksi)'
    }
    scan.sampah_nama = nama_map.get(scan.kategori, scan.sampah_nama)
    
    db.session.commit()
    flash('✅ Hasil klasifikasi berhasil dikoreksi!', 'success')
    return redirect(url_for('result', scan_id=scan_id))

@app.route('/history/delete/<int:scan_id>', methods=['POST'])
def delete_history(scan_id):
    scan = ScanHistory.query.get_or_404(scan_id)
    try:
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], scan.gambar_path.replace('uploads/', ''))
        if os.path.exists(full_path):
            os.remove(full_path)
    except:
        pass
    db.session.delete(scan)
    db.session.commit()
    flash('🗑️ Riwayat berhasil dihapus!', 'success')
    return redirect(url_for('history'))

@app.route('/history/delete_all', methods=['POST'])
def delete_all_history():
    # Delete all records
    ScanHistory.query.delete()
    db.session.commit()
    
    # Delete all uploaded files
    upload_folder = app.config['UPLOAD_FOLDER']
    for filename in os.listdir(upload_folder):
        filepath = os.path.join(upload_folder, filename)
        if os.path.isfile(filepath):
            os.remove(filepath)
    
    flash('🗑️ Semua riwayat dan gambar berhasil dihapus!', 'success')
    return redirect(url_for('history'))

if __name__ == '__main__':
    import os
    
    # Koyeb/Cloud akan memberikan PORT environment variable.
    # Jika tidak ada (artinya jalan di laptop), pakai port 5000.
    port = int(os.environ.get('PORT', 5000))
    
    # Jalankan app di 0.0.0.0 agar bisa diakses dari luar
    # HAPUS ssl_context=context karena Cloud sudah urus HTTPS-nya
    app.run(host='0.0.0.0', port=port)