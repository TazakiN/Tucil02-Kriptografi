# Steganografi Audio dengan Multiple-LSB

Aplikasi desktop Python untuk menyembunyikan dan mengekstrak pesan rahasia dalam file audio MP3 menggunakan teknik Multiple-LSB Steganography.

## ✨ Fitur Utama

- **Multiple-LSB Steganography**: Mendukung 1-4 LSB per sample audio
- **Enkripsi**: Extended Vigenère Cipher dengan 256 karakter
- **Random Placement**: Penyisipan data pada posisi acak dengan seed
- **GUI**: Interface berbasis [Tkinter](https://docs.python.org/3/library/tkinter.html)  
- **PSNR Calculation**: Perhitungan kualitas audio hasil steganografi
- **Multi-format**: Mendukung MP3 dan WAV

## 🚀 Quick Start

### Prerequisites

- Python 3.10 atau lebih baru
- [FFmpeg](https://ffmpeg.org/) (untuk memproses file MP3)

### Instalasi

1. Clone atau download proyek ini

2. Buat virtual environment (jika belum ada):

   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # atau
   source .venv/bin/activate  # Linux/Mac
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Install FFmpeg (untuk support MP3):

   - Windows: Download dari [ffmpeg.org](https://ffmpeg.org/download.html)
   - Ubuntu/Debian: `sudo apt install ffmpeg`
   - macOS: `brew install ffmpeg`

### Menjalankan Aplikasi

#### Opsi 1: Menjalankan dari Source Code

```bash
cd src
python app.py
```

#### Opsi 2: Menjalankan File Executable (.exe)

Jika Anda sudah memiliki file executable yang telah dikompilasi (tersedia di folder `dist`):

1. Buka folder `dist` di File Explorer
2. Double-click file `app.exe`
3. Aplikasi akan langsung terbuka tanpa perlu instalasi Python atau dependencies

**Catatan**: File `.exe` sudah mencakup semua dependencies yang diperlukan, sehingga Anda tidak perlu menginstal Python atau library tambahan. Namun, untuk menggunakan fitur MP3, FFmpeg tetap harus terinstal di sistem Anda.

#### Opsi 3: Compile Sendiri menjadi Executable

Jika Anda ingin membuat file executable sendiri:

1. Install PyInstaller:

   ```bash
   pip install pyinstaller
   ```

2. Compile aplikasi:

   ```bash
   pyinstaller --onefile --noconsole --icon=assets/headphones.ico src/app.py
   ```

3. File executable akan tersedia di folder `dist/app.exe`

## 📖 Cara Penggunaan

### Embed Message (Menyisipkan Pesan)

1. **Pilih Cover Audio**: File MP3/WAV yang akan digunakan sebagai cover
2. **Pilih Secret File**: File rahasia yang akan disembunyikan (bisa berupa teks, gambar, PDF, dll.)
3. **Tentukan Output**: Lokasi file hasil steganografi
4. **Konfigurasi Options**:
   - **n-LSB**: Jumlah bit LSB yang digunakan (1-4)
   - **Use Encryption**: Centang untuk mengenkripsi dengan Vigenère Cipher
   - **Use Random Placement**: Centang untuk penyisipan pada posisi acak
5. **Klik "Embed Message"**
6. **Lihat hasil PSNR** untuk mengetahui kualitas audio

### Extract Message (Mengekstrak Pesan)

1. **Pilih Stego Audio**: File audio yang berisi pesan tersembunyi  
2. **Pilih Output Directory**: Folder tempat menyimpan file hasil ekstraksi
3. **Konfigurasi Extract Options**:
   - **n-LSB**: Harus sama dengan yang digunakan saat embed
   - **Decryption Key**: Isi jika file dienkripsi saat embed
   - **Stego Key**: Isi jika menggunakan random placement saat embed
4. **Klik "Extract Message"**
5. **File akan tersimpan** di direktori output

## 🏗️ Struktur Proyek

```text
tucil2-stegano-gui/
├── src/
│   ├── app.py              # Entry point GUI
│   ├── audio_handler.py    # Load/save audio utilities  
│   └── stegano/
│       ├── __init__.py     # Package initialization
│       ├── lsb.py          # Multiple-LSB implementation
│       ├── vigenere.py     # Extended Vigenère Cipher
│       ├── psnr.py         # PSNR calculator
│       └── utils.py        # Helper functions
├── assets/                 # contoh file
├── tests/                  # Test files
├── requirements.txt        # Python dependencies
└── README.md              # Dokumentasi ini
```

## 🔧 Algoritma & Teknik

### Multiple-LSB Steganography

- Menggunakan 1-4 Least Significant Bits dari setiap sample audio
- Metadata format: `[filename_length][filename][data_length][data]`
- Sequential atau random placement

### Extended Vigenère Cipher

- Enkripsi/dekripsi dengan 256 karakter ASCII
- Formula: `cipher = (plain + key) mod 256`
- Kunci direpeat sesuai panjang data

### PSNR Calculation

- Peak Signal-to-Noise Ratio untuk mengukur kualitas audio
- Formula: `PSNR = 20 * log10(MAX / sqrt(MSE))`
- Evaluasi: Excellent (≥40dB), Good (30-40dB), Fair (20-30dB)

## ⚠️ Limitasi & Notes

- **Kapasitas**: Tergantung durasi audio dan n-LSB yang dipilih
- **Kualitas**: PSNR akan menurun dengan bertambahnya n-LSB
- **Format**: MP3 membutuhkan FFmpeg, WAV didukung native
- **Keamanan**: Enkripsi menggunakan Vigenère (tidak sekuat AES)

## 🐛 Troubleshooting

### Import Error: numpy/pydub not found

```bash
pip install -r requirements.txt
```

### FFmpeg tidak ditemukan

- Windows: Tambahkan FFmpeg ke PATH environment
- Linux: `sudo apt install ffmpeg`

### PSNR terlalu rendah

- Kurangi n-LSB (gunakan 1 atau 2)
- Gunakan audio cover dengan durasi lebih panjang

### Kapasitas tidak cukup

- Gunakan audio cover yang lebih panjang
- Tingkatkan n-LSB (dengan konsekuensi PSNR menurun)
- Kompres file secret terlebih dahulu

## 📝 License

Proyek ini dibuat untuk keperluan tugas kuliah Kriptografi.

## 👥 Author

- 13522005 - Ahmad Naufal Ramadan
- 13522032 - Tazkia Nizami
