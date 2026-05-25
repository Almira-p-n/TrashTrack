import cv2
import numpy as np
import os

class TrashClassifier:
    def __init__(self):
        self.example_folder = os.path.join(os.path.dirname(__file__), 'static', 'examples')
        self.fallback_names = {
            'merah': 'Limbah B3',
            'kuning': 'Sampah Anorganik',
            'hijau': 'Sampah Organik'
        }
        self.specific_names = {
            'merah': 'Limbah Berbahaya (B3)',
            'kuning': 'Plastik/Kemasan (Anorganik)',
            'hijau': 'Sisa Makanan/Organik'
        }

    def classify(self, file_path, original_filename=''):
        """
        PRIORITAS:
        1. Keyword matching (paling akurat)
        2. Visual matching (backup)
        """
        
        # PRIORITAS 1: Keyword matching - HARUS DICEK DULU!
        keyword_result = self._strong_keyword_match(original_filename)
        if keyword_result:
            print(f"✅ Detected by keyword: {keyword_result['nama']}")
            return keyword_result

        # PRIORITAS 2: Visual matching
        if not os.path.exists(self.example_folder):
            return self._make_result('kuning', 'Sampah Anorganik', 50)

        best_category = None
        best_score = 0
        
        img_user = cv2.imread(file_path)
        if img_user is None:
            return self._make_result('kuning', 'Sampah Anorganik', 50)
        
        img_user = cv2.resize(img_user, (100, 100))
        img_user_gray = cv2.cvtColor(img_user, cv2.COLOR_BGR2GRAY)
        
        # Bandingkan dengan SEMUA contoh
        for category in ['merah', 'kuning', 'hijau']:
            category_path = os.path.join(self.example_folder, category)
            if not os.path.exists(category_path):
                continue
            
            for filename in os.listdir(category_path):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    example_path = os.path.join(category_path, filename)
                    score = self._template_match(img_user_gray, example_path)
                    
                    if score > best_score:
                        best_score = score
                        best_category = category
        
        # Threshold lebih tinggi (0.70) biar tidak gampang salah
        if best_score >= 0.70 and best_category:
            return self._make_result(
                best_category,
                self.specific_names[best_category],
                min(95, int(best_score * 100))
            )
        else:
            # Fallback: kalau tidak yakin, gunakan kategori dengan score tertinggi
            # tapi dengan nama generik
            if best_category:
                return self._make_result(
                    best_category,
                    self.fallback_names[best_category],
                    50
                )
            return self._make_result('kuning', 'Sampah Anorganik', 50)

    def _strong_keyword_match(self, filename):
        """
        KEYWORD MATCHING YANG KUAT - Ini yang paling penting!
        Kalau ada keyword ini di nama file, LANGSUNG tentukan kategori.
        """
        if not filename:
            return None
        
        fn = filename.lower()
        
        # === LIMBAH B3 (MERAH) ===
        b3_keywords = ['baterai', 'aki', 'lampu', 'neon', 'bohlam', 'obat', 'pil', 
                       'tablet', 'kaca', 'cermin', 'pecahan', 'kimia', 'cat', 
                       'pestisida', 'racun', 'merkuri', 'timbal']
        
        for keyword in b3_keywords:
            if keyword in fn:
                print(f"🎯 Keyword match: {keyword} → MERAH (B3)")
                return self._make_result('merah', 'Limbah Berbahaya (B3)', 95)
        
        # === SAMPAH ORGANIK (HIJAU) ===
        organik_keywords = ['daun', 'ranting', 'rumput', 'bunga', 'makanan', 'nasi', 
                           'sayur', 'lauk', 'roti', 'mie', 'buah', 'pisang', 'jeruk',
                           'apel', 'kulit', 'biji', 'tulang', 'duri', 'telur', 
                           'cangkang', 'ampas', 'kopi', 'teh', 'organik']
        
        for keyword in organik_keywords:
            if keyword in fn:
                print(f"🎯 Keyword match: {keyword} → HIJAU (Organik)")
                return self._make_result('hijau', 'Sisa Makanan/Organik', 95)
        
        # === SAMPAH ANORGANIK (KUNING) ===
        anorganik_keywords = ['plastik', 'botol', 'gelas', 'wadah', 'ember', 'kertas', 
                             'buku', 'majalah', 'koran', 'kardus', 'hvs', 'notebook',
                             'kaleng', 'alumunium', 'logam', 'besi', 'styrofoam', 
                             'gabus', 'kemasan', 'snack', 'jajan', 'bungkus', 'kresek',
                             'anorganik']
        
        for keyword in anorganik_keywords:
            if keyword in fn:
                # Khusus snack/jajan/bungkus
                if any(k in fn for k in ['snack', 'jajan', 'bungkus']):
                    print(f"🎯 Keyword match: {keyword} → KUNING (Bungkus Snack)")
                    return self._make_result('kuning', 'Bungkus Snack/Plastik', 95)
                else:
                    print(f"🎯 Keyword match: {keyword} → KUNING (Anorganik)")
                    return self._make_result('kuning', 'Plastik/Kemasan (Anorganik)', 95)
        
        return None

    def _template_match(self, img_user_gray, example_path):
        """Template Matching dengan multiple methods untuk akurasi lebih baik"""
        try:
            img_example = cv2.imread(example_path)
            if img_example is None:
                return 0
            
            img_example = cv2.resize(img_example, (100, 100))
            img_example_gray = cv2.cvtColor(img_example, cv2.COLOR_BGR2GRAY)
            
            # Method 1: TM_CCOEFF_NORMED (paling baik untuk struktur)
            res1 = cv2.matchTemplate(img_user_gray, img_example_gray, cv2.TM_CCOEFF_NORMED)
            score1 = np.max(res1)
            
            # Method 2: TM_SQDIFF_NORMED (inverse - makin kecil makin bagus)
            res2 = cv2.matchTemplate(img_user_gray, img_example_gray, cv2.TM_SQDIFF_NORMED)
            score2 = 1.0 - np.min(res2)  # Invert score
            
            # Average kedua method
            final_score = (score1 + score2) / 2
            
            return final_score
        except Exception as e:
            print(f"Error template match: {e}")
            return 0

    def _make_result(self, kategori, nama, confidence):
        return {
            'nama': nama,
            'kategori': kategori,
            'confidence': int(confidence),
            'deskripsi': self._get_description(kategori)
        }

    def _get_description(self, kategori):
        desc = {
            'merah': 'Limbah Bahan Berbahaya dan Beracun (B3). Memerlukan penanganan khusus.',
            'kuning': 'Sampah Anorganik. Tidak mudah terurai namun bisa didaur ulang.',
            'hijau': 'Sampah Organik. Mudah membusuk dan terurai secara alami.'
        }
        return desc.get(kategori, '')

    def get_kategori_info(self, kategori):
        info = {
            'merah': {
                'nama': 'MERAH (B3/Berbahaya)',
                'warna': '#EF4444',
                'icon': '⚠️',
                'contoh': 'Baterai, Lampu, Kaca, Obat, Bahan Kimia',
                'penjelasan': 'Limbah Bahan Berbahaya dan Beracun (B3) memerlukan penanganan khusus.'
            },
            'kuning': {
                'nama': 'KUNING (Anorganik)',
                'warna': '#EAB308',
                'icon': '♻️',
                'contoh': 'Plastik, Kertas, Kaleng, Botol, Kardus',
                'penjelasan': 'Sampah anorganik yang tidak mudah terurai tetapi bisa didaur ulang.'
            },
            'hijau': {
                'nama': 'HIJAU (Organik)',
                'warna': '#22C55E',
                'icon': '🌱',
                'contoh': 'Daun, Sisa Makanan, Buah, Sayuran, Tulang',
                'penjelasan': 'Sampah organik yang mudah terurai secara alami.'
            }
        }
        return info.get(kategori, info['kuning'])