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
    
    dosen_list = data['DOSEN'].dropna().unique().tolist()  # Ambil nama dosen unik tanpa NaN
    return dosen_list, data

# Fungsi untuk mencari jadwal kosong berdasarkan dosen yang dipilih
# Fungsi untuk mencari jadwal kosong berdasarkan dosen yang dipilih
def cari_jadwal_kosong(dosen_list, data):
    jam_mulai = time_to_datetime("08:00")  # Jam mulai yang kita tentukan (08:00)
    jam_selesai = time_to_datetime("15:00")  # Jam selesai yang kita tentukan (15:00)
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

    # Tambahkan nama dosen yang dipilih pada hasil jadwal kosong
    return dosen_list, waktu_kosong


# Halaman Upload untuk file jadwal dosen
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
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

            return render_template('index.html', dosen_list=dosen_list)

    return render_template('upload.html')

# Halaman utama untuk memilih dosen dan mencari jadwal kosong
@app.route('/', methods=['GET', 'POST'])
def index():
    dosen_list = session.get('dosen_list', [])
    data = pd.read_json(session.get('data', '{}'))  # Mengambil data jadwal dosen yang telah disimpan

    if request.method == 'POST':
        # Ambil nama dosen yang dipilih
        selected_dosen = [request.form.get(f'dosen{i}') for i in range(1, 5)]

        # Filter dosen yang tidak dipilih (kosong)
        selected_dosen = [dosen for dosen in selected_dosen if dosen]

        if selected_dosen:
            # Mencari jadwal kosong berdasarkan dosen yang dipilih
            dosen_pilihan, jadwal_kosong = cari_jadwal_kosong(selected_dosen, data)

            # Menyusun hasil output berdasarkan urutan dropdown
            dosen_dict = {
                'dosen_pembimbing_1': selected_dosen[0] if len(selected_dosen) > 0 else '',
                'dosen_pembimbing_2': selected_dosen[1] if len(selected_dosen) > 1 else '',
                'dosen_penguji_1': selected_dosen[2] if len(selected_dosen) > 2 else '',
                'dosen_penguji_2': selected_dosen[3] if len(selected_dosen) > 3 else '',
            }

            return render_template('index.html', dosen_list=dosen_list, jadwal_kosong=jadwal_kosong, dosen_pilihan=dosen_dict)

    return render_template('index.html', dosen_list=dosen_list)



if __name__ == '__main__':
    app.run(debug=True)
