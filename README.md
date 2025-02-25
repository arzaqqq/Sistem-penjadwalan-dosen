# Panduan Instalasi dan Menjalankan Proyek

## 📋 Prasyarat
- Git
- Python 3.8+
- pip (Python Package Installer)

## 🚀 Langkah Instalasi

### 1. Clone Repositori
Ada dua cara untuk men-download proyek:

#### Metode Git Clone
```bash
git clone [URL_REPOSITORI_ANDA]
cd [NAMA_FOLDER_PROYEK]
```

#### Metode Download ZIP
1. Klik tombol "Code" di halaman repositori GitHub
2. Pilih "Download ZIP"
3. Ekstrak file zip ke folder yang diinginkan

### 2. Persiapan Lingkungan Virtual (Opsional tapi Direkomendasikan)
```bash
# Buat virtual environment
python -m venv venv

# Aktifkan virtual environment
# Untuk Windows
venv\Scripts\activate

# Untuk macOS/Linux
source venv/bin/activate
```

### 3. Install Dependensi
```bash
# Pastikan Anda sudah di dalam folder proyek dan virtual environment aktif
pip install -r requirements.txt
```

## 🖥️ Menjalankan Proyek
```bash
# Jalankan aplikasi
python app.py
```

## 🛠️ Troubleshooting Umum

### Masalah Instalasi Dependensi
- Pastikan pip sudah terupdate: 
  ```bash
  python -m pip install --upgrade pip
  ```
- Periksa koneksi internet
- Pastikan versi Python kompatibel

### Kesalahan Umum
- **ModuleNotFoundError**: Pastikan semua dependensi terinstall dengan benar
- **Versi Python**: Gunakan Python 3.8 atau lebih baru
- Aktifkan virtual environment sebelum install dependensi

## 📝 Catatan Penting
- Selalu gunakan virtual environment
- Perbarui `requirements.txt` jika menambahkan library baru
- Simpan versi Python dan dependensi yang digunakan


