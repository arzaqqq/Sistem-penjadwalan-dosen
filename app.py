import os
from flask import Flask, render_template, request, session, send_from_directory
import pandas as pd
import json
from werkzeug.utils import secure_filename
from datetime import datetime

# Configuration remains the same
UPLOAD_FOLDER = 'uploads'
TEMPLATE_FOLDER = 'static/templates'
ALLOWED_EXTENSIONS = {'csv', 'xlsx'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(TEMPLATE_FOLDER):
    os.makedirs(TEMPLATE_FOLDER)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.secret_key = 'secret_key_for_session'

def clean_and_sort_dosen_list(dosen_list):
    """Membersihkan dan mengurutkan daftar dosen"""
    # Hapus nilai kosong dan whitespace
    cleaned_list = [dosen.strip() for dosen in dosen_list if dosen and dosen.strip()]
    # Urutkan secara alfabetis
    return sorted(list(set(cleaned_list)))

def create_template_file():
    """Membuat file template jika belum ada"""
    template_path = os.path.join(TEMPLATE_FOLDER, 'template_jadwal.xlsx')
    if not os.path.exists(template_path):
        df = pd.DataFrame(columns=['DOSEN', 'SENIN', 'SELASA', 'RABU', 'KAMIS', 'JUMAT'])
        df.to_excel(template_path, index=False)
    return template_path

# Route untuk download template

@app.route('/download-template')
def download_template():
    try:
        return send_from_directory('static/templates', 
                                 'template_jadwal.xlsx', 
                                 as_attachment=True)
    except FileNotFoundError:
        return "Template file not found", 404

# Helper functions remain the same
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def time_to_datetime(time_str):
    try:
        return datetime.strptime(time_str.strip(), "%H:%M")
    except:
        return None

def cari_jadwal_kosong(dosen_list, data):
    # Convert data back to DataFrame if it's a string
    if isinstance(data, str):
        data = pd.read_json(data)
    elif data is None:
        return []
        
    jam_mulai = time_to_datetime("09:00")
    jam_selesai = time_to_datetime("17:00")
    waktu_kosong = []

    for hari in ['SENIN', 'SELASA', 'RABU', 'KAMIS', 'JUMAT']:
        jadwal_hari = []
        
        for _, row in data.iterrows():
            if row['DOSEN'] in dosen_list and pd.notna(row[hari]) and row[hari] != '':
                try:
                    start_time, end_time = row[hari].split('-')
                    start_time = time_to_datetime(start_time)
                    end_time = time_to_datetime(end_time)
                    if start_time and end_time:
                        jadwal_hari.append((start_time, end_time))
                except:
                    continue
        
        if not jadwal_hari:
            waktu_kosong.append((jam_mulai.strftime('%H:%M'), 
                               jam_selesai.strftime('%H:%M'), 
                               hari))
            continue

        jadwal_hari.sort()

        prev_end_time = jam_mulai
        for start, end in jadwal_hari:
            if start > prev_end_time:
                waktu_kosong.append((prev_end_time.strftime('%H:%M'), 
                                   start.strftime('%H:%M'), 
                                   hari))
            prev_end_time = max(prev_end_time, end)

        if prev_end_time < jam_selesai:
            waktu_kosong.append((prev_end_time.strftime('%H:%M'), 
                               jam_selesai.strftime('%H:%M'), 
                               hari))

    return waktu_kosong

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    error_message = None
    preview_data = session.get('preview_data')
    columns = session.get('preview_columns')
    
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
                    df = pd.read_csv(filepath)
                else:
                    df = pd.read_excel(filepath)
                
                required_columns = ['DOSEN', 'SENIN', 'SELASA', 'RABU', 'KAMIS', 'JUMAT']
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    error_message = f"Kolom yang diperlukan tidak ditemukan: {', '.join(missing_columns)}"
                    os.remove(filepath)
                    return render_template('upload.html', error=error_message)
                
                # Bersihkan data
                df = df.fillna('')
                df['DOSEN'] = df['DOSEN'].str.strip()
                
                # Hapus baris dengan DOSEN kosong
                df = df[df['DOSEN'].str.len() > 0]
                
                # Simpan data yang sudah dibersihkan
                dosen_list = clean_and_sort_dosen_list(df['DOSEN'].unique().tolist())
                session['dosen_list'] = dosen_list
                session['data'] = df.to_json(orient='records')
                
                # Simpan preview data
                preview_data = df.to_dict('records')
                columns = df.columns.tolist()
                session['preview_data'] = preview_data
                session['preview_columns'] = columns
                
                return render_template('upload.html', 
                                     preview_data=preview_data,
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
                         columns=columns)

@app.route('/', methods=['GET', 'POST'])
def index():
    # Get data from session
    dosen_list = session.get('dosen_list', [])
    data_json = session.get('data')
    preview_data = session.get('preview_data')
    columns = session.get('preview_columns')
    
    # Pastikan dosen_list sudah bersih dan terurut
    dosen_list = clean_and_sort_dosen_list(dosen_list)
    
    # Convert JSON string back to DataFrame
    data = pd.DataFrame(json.loads(data_json)) if data_json else pd.DataFrame()
    
    dosen_pilihan = {
        'dosen_pembimbing_1': session.get('dosen_pembimbing_1', ''),
        'dosen_pembimbing_2': session.get('dosen_pembimbing_2', ''),
        'dosen_penguji_1': session.get('dosen_penguji_1', ''),
        'dosen_penguji_2': session.get('dosen_penguji_2', '')
    }
    
    jadwal_kosong = []

    if request.method == 'POST':
        dosen_pembimbing_1 = request.form.get('dosen1', '')
        dosen_pembimbing_2 = request.form.get('dosen2', '')
        dosen_penguji_1 = request.form.get('dosen3', '')
        dosen_penguji_2 = request.form.get('dosen4', '')

        # Simpan pilihan dosen ke session
        session['dosen_pembimbing_1'] = dosen_pembimbing_1
        session['dosen_pembimbing_2'] = dosen_pembimbing_2
        session['dosen_penguji_1'] = dosen_penguji_1
        session['dosen_penguji_2'] = dosen_penguji_2

        dosen_pilihan = {
            'dosen_pembimbing_1': dosen_pembimbing_1,
            'dosen_pembimbing_2': dosen_pembimbing_2,
            'dosen_penguji_1': dosen_penguji_1,
            'dosen_penguji_2': dosen_penguji_2,
        }

        selected_dosen = [dosen for dosen in dosen_pilihan.values() if dosen and dosen.strip()]
        if selected_dosen:
            jadwal_kosong = cari_jadwal_kosong(selected_dosen, data)

    return render_template('index.html', 
                         dosen_list=dosen_list, 
                         jadwal_kosong=jadwal_kosong,
                         dosen_pilihan=dosen_pilihan,
                         preview_data=preview_data,
                         columns=columns)
                         
if __name__ == '__main__':
    app.run(debug=True)