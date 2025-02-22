import os
from flask import Flask, render_template, request, session, send_from_directory
import pandas as pd
from werkzeug.utils import secure_filename
from datetime import datetime

# Konfigurasi tambahan untuk upload
UPLOAD_FOLDER = 'uploads'
TEMPLATE_FOLDER = 'static/templates'
ALLOWED_EXTENSIONS = {'csv', 'xlsx'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(TEMPLATE_FOLDER):
    os.makedirs(TEMPLATE_FOLDER)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Max 16MB file
app.secret_key = 'secret_key_for_session'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Fungsi untuk mengonversi waktu ke format datetime
def time_to_datetime(time_str):
    try:
        return datetime.strptime(time_str.strip(), "%H:%M")
    except:
        return None

# Fungsi untuk mencari jadwal kosong berdasarkan dosen yang dipilih
def cari_jadwal_kosong(dosen_list, data):
    if data.empty:
        return []
        
    jam_mulai = time_to_datetime("09:00")  # Jam mulai 
    jam_selesai = time_to_datetime("17:00")  # Jam selesai 
    waktu_kosong = []

    # Loop untuk setiap hari
    for hari in ['SENIN', 'SELASA', 'RABU', 'KAMIS', 'JUMAT']:
        jadwal_hari = []
        
        # Menyusun jadwal untuk setiap dosen yang dipilih pada hari tersebut
        for _, row in data.iterrows():
            if row['DOSEN'] in dosen_list and pd.notna(row[hari]) and row[hari] != '':
                try:
                    start_time, end_time = row[hari].split('-')
                    start_time = time_to_datetime(start_time)
                    end_time = time_to_datetime(end_time)
                    if start_time and end_time:  # Hanya tambahkan jika kedua waktu valid
                        jadwal_hari.append((start_time, end_time))
                except:
                    continue
        
        if not jadwal_hari:  # Jika tidak ada jadwal pada hari tersebut
            waktu_kosong.append((jam_mulai.strftime('%H:%M'), 
                               jam_selesai.strftime('%H:%M'), 
                               hari))
            continue

        jadwal_hari.sort()  # Mengurutkan berdasarkan waktu mulai

        # Cek waktu kosong di antara jadwal yang ada
        prev_end_time = jam_mulai
        for start, end in jadwal_hari:
            if start > prev_end_time:
                waktu_kosong.append((prev_end_time.strftime('%H:%M'), 
                                   start.strftime('%H:%M'), 
                                   hari))
            prev_end_time = max(prev_end_time, end)

        # Cek waktu kosong setelah jadwal terakhir hingga jam selesai
        if prev_end_time < jam_selesai:
            waktu_kosong.append((prev_end_time.strftime('%H:%M'), 
                               jam_selesai.strftime('%H:%M'), 
                               hari))

    return waktu_kosong

# Route untuk download template
@app.route('/download-template')
def download_template():
    try:
        return send_from_directory('static/templates', 
                                 'template_jadwal.xlsx', 
                                 as_attachment=True)
    except FileNotFoundError:
        return "Template file not found", 404

# Route untuk halaman upload
# Tambahkan ini di route upload
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    error_message = None
    preview_data = None
    
    # Cek apakah ada preview data di session
    if 'preview_data' in session and 'preview_columns' in session:
        preview_data = session['preview_data']
        columns = session['preview_columns']
    
    if request.method == 'POST':
        if 'file' not in request.files:
            error_message = 'Tidak ada file yang dipilih'
            return render_template('upload.html', error=error_message)
        
        file = request.files['file']
        
        if file.filename == '':
            error_message = 'Tidak ada file yang dipilih'
            return render_template('upload.html', error=error_message)
        
        if file and allowed_file(file.filename):
            try:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                if filename.endswith('.csv'):
                    preview_data = pd.read_csv(filepath)
                else:
                    preview_data = pd.read_excel(filepath)
                
                required_columns = ['DOSEN', 'SENIN', 'SELASA', 'RABU', 'KAMIS', 'JUMAT']
                missing_columns = [col for col in required_columns if col not in preview_data.columns]
                
                if missing_columns:
                    error_message = f"Kolom yang diperlukan tidak ditemukan: {', '.join(missing_columns)}"
                    os.remove(filepath)
                    return render_template('upload.html', error=error_message)
                
                preview_data = preview_data.fillna('')
                
                dosen_list = preview_data['DOSEN'].unique().tolist()
                session['dosen_list'] = dosen_list
                session['data'] = preview_data.to_json()
                
                # Simpan preview data ke session
                preview_dict = preview_data.to_dict('records')
                columns = preview_data.columns.tolist()
                session['preview_data'] = preview_dict
                session['preview_columns'] = columns
                
                return render_template('upload.html', 
                                     preview_data=preview_dict,
                                     columns=columns,
                                     success='File berhasil diupload!')
                
            except Exception as e:
                error_message = f"Error saat memproses file: {str(e)}"
                if os.path.exists(filepath):
                    os.remove(filepath)
        else:
            error_message = 'Format file tidak diizinkan. Gunakan CSV atau Excel (.xlsx)'
    
    return render_template('upload.html', 
                         error=error_message,
                         preview_data=preview_data,
                         columns=session.get('preview_columns', None))

# Modifikasi route index untuk menampilkan preview
@app.route('/', methods=['GET', 'POST'])
def index():
    dosen_list = session.get('dosen_list', [])
    data = pd.read_json(session.get('data', '{}'))
    preview_data = session.get('preview_data', None)
    preview_columns = session.get('preview_columns', None)

    dosen_pilihan = session.get('dosen_pilihan', {
        'dosen_pembimbing_1': '',
        'dosen_pembimbing_2': '',
        'dosen_penguji_1': '',
        'dosen_penguji_2': ''
    })

    if request.method == 'POST':
        dosen_pembimbing_1 = request.form.get('dosen1')
        dosen_pembimbing_2 = request.form.get('dosen2')
        dosen_penguji_1 = request.form.get('dosen3')
        dosen_penguji_2 = request.form.get('dosen4')

        dosen_dict = {
            'dosen_pembimbing_1': dosen_pembimbing_1,
            'dosen_pembimbing_2': dosen_pembimbing_2,
            'dosen_penguji_1': dosen_penguji_1,
            'dosen_penguji_2': dosen_penguji_2,
        }

        selected_dosen = [dosen for dosen in dosen_dict.values() if dosen]
        if selected_dosen:
            jadwal_kosong = cari_jadwal_kosong(selected_dosen, data)
            session['dosen_pilihan'] = dosen_dict

            return render_template('index.html', 
                                 dosen_list=dosen_list, 
                                 jadwal_kosong=jadwal_kosong, 
                                 dosen_pilihan=dosen_dict,
                                 preview_data=preview_data,
                                 columns=preview_columns)

    return render_template('index.html', 
                         dosen_list=dosen_list, 
                         dosen_pilihan=dosen_pilihan,
                         preview_data=preview_data,
                         columns=preview_columns)


if __name__ == '__main__':
    app.run(debug=True)
