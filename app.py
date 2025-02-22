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
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    error_message = None
    preview_data = None
    
    if request.method == 'POST':
        # Check if file is present in request
        if 'file' not in request.files:
            error_message = 'Tidak ada file yang dipilih'
            return render_template('upload.html', error=error_message)
        
        file = request.files['file']
        
        # Check if file is selected
        if file.filename == '':
            error_message = 'Tidak ada file yang dipilih'
            return render_template('upload.html', error=error_message)
        
        if file and allowed_file(file.filename):
            try:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                # Read file for preview based on extension
                if filename.endswith('.csv'):
                    preview_data = pd.read_csv(filepath)
                else:
                    preview_data = pd.read_excel(filepath)
                
                # Basic validation of required columns
                required_columns = ['DOSEN', 'SENIN', 'SELASA', 'RABU', 'KAMIS', 'JUMAT']
                missing_columns = [col for col in required_columns if col not in preview_data.columns]
                
                if missing_columns:
                    error_message = f"Kolom yang diperlukan tidak ditemukan: {', '.join(missing_columns)}"
                    os.remove(filepath)  # Hapus file yang tidak valid
                    return render_template('upload.html', error=error_message)
                
                # Clean the data
                preview_data = preview_data.fillna('')  # Replace NaN with empty string
                
                # Extract dosen list dan simpan di session
                dosen_list = preview_data['DOSEN'].unique().tolist()
                session['dosen_list'] = dosen_list
                session['data'] = preview_data.to_json()
                
                # Convert preview data to dict for template
                preview_dict = preview_data.to_dict('records')
                columns = preview_data.columns.tolist()
                
                return render_template('upload.html', 
                                     preview_data=preview_dict,
                                     columns=columns,
                                     success='File berhasil diupload!')
                
            except Exception as e:
                error_message = f"Error saat memproses file: {str(e)}"
                # Jika terjadi error, hapus file yang sudah diupload
                if os.path.exists(filepath):
                    os.remove(filepath)
        else:
            error_message = 'Format file tidak diizinkan. Gunakan CSV atau Excel (.xlsx)'
    
    # GET request atau jika ada error
    return render_template('upload.html', 
                         error=error_message,
                         preview_data=preview_data.to_dict('records') if preview_data is not None else None,
                         columns=preview_data.columns.tolist() if preview_data is not None else None)
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
