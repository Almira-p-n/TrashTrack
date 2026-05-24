from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class ScanHistory(db.Model):
    __tablename__ = 'scan_history'
    id = db.Column(db.Integer, primary_key=True)
    sampah_nama = db.Column(db.String(100), nullable=False)
    kategori = db.Column(db.String(20), nullable=False)  # merah, kuning, hijau
    confidence = db.Column(db.Integer, default=0)
    gambar_path = db.Column(db.String(200))
    tanggal = db.Column(db.DateTime, default=datetime.now)  # Waktu lokal Indonesia
    
    def to_dict(self):
        return {
            'id': self.id,
            'sampah_nama': self.sampah_nama,
            'kategori': self.kategori,
            'confidence': self.confidence,
            'gambar_path': self.gambar_path,
            'tanggal': self.tanggal.strftime('%d %b %Y - %H:%M WIB')
        }