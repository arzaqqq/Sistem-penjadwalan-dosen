from flask import Flask, render_template, request, jsonify
import pandas as pd
import sqlite3
from werkzeug.utils import secure_filename
import os

# Inisialisasi Flask
app = Flask(__name__)

# Tentukan folder untuk menyimpan file upload
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'csv', 'xlsx'}

# Fungsi untuk memeriksa ekstensi file yang valid
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Fungsi untuk menyimpan data ke dalam database SQLite
def save_to_db(data):
    conn = sqlite3.connect('jadwal_dosen.db')
    c = conn.cursor()
    # Membuat tabel jika belum ada
    c.execute('''CREATE TABLE IF NOT EXISTS jadwal_dosen (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dosen TEXT,
                    hari TEXT,
                    waktu_mulai TEXT,
                    waktu_selesai TEXT,
                    mata_kuliah TEXT,
                    ruangan TEXT)''')
    
    # Hapus data lama
    c.execute("DELETE FROM jadwal_dosen")
    
    for index, row in data.iterrows():
        c.execute('''
            INSERT INTO jadwal_dosen (dosen, hari, waktu_mulai, waktu_selesai, mata_kuliah, ruangan)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (row['Dosen'], row['Hari'], row['Waktu Mulai'], row['Waktu Selesai'], row['Mata Kuliah'], row['Ruangan']))
    
    conn.commit()
    conn.close()

# Halaman upload jadwal dosen
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Mengambil file yang di-upload
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Membaca file dan menyimpan ke database
            if filename.endswith('.csv'):
                data = pd.read_csv(filepath)
            elif filename.endswith('.xlsx'):
                data = pd.read_excel(filepath)
            
            save_to_db(data)

            return jsonify({'success': 'Data berhasil di-upload dan disimpan.'})
        else:
            return jsonify({'error': 'File tidak valid.'})
    
    return render_template('upload.html')

# Halaman untuk mencari jadwal kosong
@app.route('/cari_jadwal', methods=['GET'])
def cari_jadwal():
    dosen_list = request.args.getlist('dosen')
    if len(dosen_list) in [2, 4]:  # Mencari untuk 2 atau 4 dosen
        kosong = cari_jadwal_kosong(dosen_list)
        return jsonify(kosong)
    return jsonify({'error': 'Masukkan 2 atau 4 dosen.'})

# Fungsi untuk mengambil jadwal dosen dari database
def get_jadwal_dosen(dosen):
    conn = sqlite3.connect('jadwal_dosen.db')
    c = conn.cursor()
    c.execute("SELECT * FROM jadwal_dosen WHERE dosen = ?", (dosen,))
    rows = c.fetchall()
    conn.close()
    return rows

# Fungsi untuk mencari jadwal kosong berdasarkan 2 atau 4 dosen
def cari_jadwal_kosong(dosen_list):
    jadwal_dosen = {}
    for dosen in dosen_list:
        jadwal_dosen[dosen] = get_jadwal_dosen(dosen)
    
    waktu_kosong = []
    # Menemukan celah waktu kosong
    for i in range(len(jadwal_dosen[dosen_list[0]])):
        waktu_tertentu = []
        for dosen in dosen_list:
            waktu_tertentu.append(jadwal_dosen[dosen][i])
        
        if all(is_conflict(waktu_tertentu[i], waktu_tertentu[i+1]) == False for i in range(len(waktu_tertentu)-1)):
            waktu_kosong.append(waktu_tertentu)
    
    return waktu_kosong

# Fungsi untuk memeriksa konflik antara dua jadwal
def is_conflict(waktu1, waktu2):
    return waktu1[4] > waktu2[3] or waktu2[4] > waktu1[3]

if __name__ == '__main__':
    app.run(debug=True)
