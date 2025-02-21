import os  # Pastikan ini ada di bagian atas file
from flask import Flask, render_template, request, session
import pandas as pd
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)

# Tentukan folder untuk menyimpan file upload dan kunci sesi
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'csv', 'xlsx'}
app.secret_key = 'secret_key_for_session'  # Kunci untuk sesi

# Fungsi untuk memeriksa ekstensi file yang valid
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Fungsi untuk mengonversi waktu ke format datetime
def time_to_datetime(time_str):
    return datetime.strptime(time_str, "%H:%M")

# Fungsi untuk membaca dan mengekstrak nama dosen dari file
def extract_dosen_from_file(file_path):
    if file_path.endswith('.csv'):
        data = pd.read_csv(file_path)
    elif file_path.endswith('.xlsx'):
        data = pd.read_excel(file_path)
    
    # Menghapus spasi ekstra pada kolom DOSEN
    data['DOSEN'] = data['DOSEN'].str.replace('\s+', ' ', regex=True)
    
    dosen_list = data['DOSEN'].dropna().unique().tolist()  # Ambil nama dosen unik tanpa NaN
    dosen_list.sort()  # Mengurutkan nama dosen secara ascending
    
    return dosen_list, data

# Fungsi untuk mencari jadwal kosong berdasarkan dosen yang dipilih
def cari_jadwal_kosong(dosen_list, data):
    jam_mulai = time_to_datetime("09:00")  # Jam mulai 
    jam_selesai = time_to_datetime("17:00")  # Jam selesai 
    waktu_kosong = []

    # Loop untuk setiap hari
    for hari in ['SENIN', 'SELASA', 'RABU', 'KAMIS', 'JUMAT']:
        jadwal_hari = []
        
        # Menyusun jadwal untuk setiap dosen yang dipilih pada hari tersebut
        for index, row in data.iterrows():
            if row['DOSEN'] in dosen_list and pd.notna(row[hari]):
                start_time, end_time = row[hari].split('-')
                start_time = time_to_datetime(start_time)
                end_time = time_to_datetime(end_time)
                jadwal_hari.append((start_time, end_time))
        
        jadwal_hari.sort()  # Mengurutkan berdasarkan waktu mulai

        # Cek waktu kosong di antara jadwal yang ada
        prev_end_time = jam_mulai
        for start, end in jadwal_hari:
            if start > prev_end_time:
                waktu_kosong.append((prev_end_time.strftime('%H:%M'), start.strftime('%H:%M'), hari))
            prev_end_time = max(prev_end_time, end)

        # Cek waktu kosong setelah jadwal terakhir hingga jam selesai
        if prev_end_time < jam_selesai:
            waktu_kosong.append((prev_end_time.strftime('%H:%M'), jam_selesai.strftime('%H:%M'), hari))

    return waktu_kosong  # Hanya mengembalikan waktu kosong


# Halaman Upload untuk file jadwal dosen
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Menghapus sesi yang lama terlebih dahulu
        session.pop('dosen_list', None)
        session.pop('data', None)

        # Mengambil file yang di-upload
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Mengambil nama dosen dan data dari file yang di-upload
            dosen_list, data = extract_dosen_from_file(filepath)

            # Menyimpan nama dosen dalam sesi
            session['dosen_list'] = dosen_list
            session['data'] = data.to_json()  # Menyimpan data dalam format JSON untuk digunakan nanti

            # Inisialisasi variabel dosen_pilihan dengan dictionary kosong
            dosen_pilihan = {
                'dosen_pembimbing_1': '',
                'dosen_pembimbing_2': '',
                'dosen_penguji_1': '',
                'dosen_penguji_2': ''
            }

            return render_template('index.html', dosen_list=dosen_list, dosen_pilihan=dosen_pilihan)

    return render_template('upload.html')

# Halaman utama untuk memilih dosen dan mencari jadwal kosong
@app.route('/', methods=['GET', 'POST'])
def index():
    dosen_list = session.get('dosen_list', [])
    data = pd.read_json(session.get('data', '{}'))  # Mengambil data jadwal dosen yang telah disimpan

    # Inisialisasi variabel dosen_pilihan dengan nilai default jika belum terdefinisi
    dosen_pilihan = session.get('dosen_pilihan', {
        'dosen_pembimbing_1': '',
        'dosen_pembimbing_2': '',
        'dosen_penguji_1': '',
        'dosen_penguji_2': ''
    })

    if request.method == 'POST':
        # Ambil nama dosen yang dipilih dari setiap dropdown
        dosen_pembimbing_1 = request.form.get('dosen1')
        dosen_pembimbing_2 = request.form.get('dosen2')
        dosen_penguji_1 = request.form.get('dosen3')
        dosen_penguji_2 = request.form.get('dosen4')

        # Menyusun dosen yang dipilih dalam kategori
        dosen_dict = {
            'dosen_pembimbing_1': dosen_pembimbing_1,
            'dosen_pembimbing_2': dosen_pembimbing_2,
            'dosen_penguji_1': dosen_penguji_1,
            'dosen_penguji_2': dosen_penguji_2,
        }

        # Mencari jadwal kosong berdasarkan dosen yang dipilih
        selected_dosen = [dosen for dosen in dosen_dict.values() if dosen]
        if selected_dosen:
            jadwal_kosong = cari_jadwal_kosong(selected_dosen, data)
            
            # Update nilai dosen_pilihan dalam sesi
            session['dosen_pilihan'] = dosen_dict

            return render_template('index.html', dosen_list=dosen_list, jadwal_kosong=jadwal_kosong, dosen_pilihan=dosen_dict)

    return render_template('index.html', dosen_list=dosen_list, dosen_pilihan=dosen_pilihan)



if __name__ == '__main__':
    app.run(debug=True)
