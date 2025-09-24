"""
Multiple-LSB Steganography untuk audio
Implementasi embed dan extract dengan 1-4 LSB
"""

import numpy as np
from typing import Optional, Tuple, List
from .utils import (
    bytes_to_bits, bits_to_bytes, get_lsb, set_lsb,
    create_payload, extract_payload, generate_random_positions,
    calculate_capacity
)
from .vigenere import ExtendedVigenereCipher


class MultipleLSBSteganography:
    """
    Kelas untuk steganografi Multiple-LSB pada audio
    """
    
    def __init__(self):
        self.cipher = ExtendedVigenereCipher()
    
    def embed(self, 
              audio_samples: np.ndarray,
              secret_data: bytes,
              n_lsb: int = 1,
              filename: str = "",
              encryption_key: Optional[str] = None,
              use_random_placement: bool = False,
              stego_key: Optional[str] = None) -> Tuple[np.ndarray, str]:
        """
        Embed secret data ke dalam audio samples
        
        Args:
            audio_samples: Audio samples (numpy array)
            secret_data: Data rahasia yang akan disembunyikan
            n_lsb: Jumlah LSB yang digunakan (1-4)
            filename: Nama file rahasia
            encryption_key: Kunci enkripsi (None = tidak dienkripsi)
            use_random_placement: Apakah menggunakan penempatan acak
            stego_key: Kunci untuk seed random placement
            
        Returns:
            Tuple[np.ndarray, str]: (stego_audio_samples, status_message)
            
        Raises:
            ValueError: Jika parameter tidak valid atau kapasitas tidak cukup
        """
        # Validasi parameter
        if n_lsb < 1 or n_lsb > 4:
            raise ValueError("n_lsb harus antara 1-4")
        
        if len(secret_data) == 0:
            raise ValueError("Secret data tidak boleh kosong")
        
        # Konversi ke int16 jika diperlukan
        if audio_samples.dtype != np.int16:
            audio_samples = audio_samples.astype(np.int16)
        
        # Buat payload (metadata + data)
        payload = create_payload(secret_data, filename)
        
        # Enkripsi jika diperlukan
        if encryption_key:
            payload = self.cipher.encrypt(payload, encryption_key)
        
        # Konversi payload ke bits
        payload_bits = bytes_to_bits(payload)
        
        # Hitung kebutuhan samples
        bits_per_sample = n_lsb
        required_samples = (len(payload_bits) + bits_per_sample - 1) // bits_per_sample
        
        # Cek kapasitas
        total_samples = len(audio_samples)
        if required_samples > total_samples:
            max_capacity = calculate_capacity(total_samples, n_lsb)
            payload_size = len(payload)
            raise ValueError(
                f"Kapasitas tidak cukup. Dibutuhkan {payload_size} bytes, "
                f"maksimum {max_capacity} bytes dengan {n_lsb}-LSB"
            )
        
        # Buat salinan audio samples
        stego_samples = audio_samples.copy()
        
        # Tentukan posisi embedding
        if use_random_placement and stego_key:
            positions = generate_random_positions(total_samples, required_samples, stego_key)
        else:
            positions = list(range(required_samples))
        
        # Embed payload bits
        bit_index = 0
        for pos in positions:
            if bit_index >= len(payload_bits):
                break
                
            # Ambil n bits dari payload
            bits_to_embed = 0
            for i in range(n_lsb):
                if bit_index + i < len(payload_bits):
                    bits_to_embed |= (payload_bits[bit_index + i] << (n_lsb - 1 - i))
            
            # Set LSB dari sample
            stego_samples[pos] = set_lsb(stego_samples[pos], bits_to_embed, n_lsb)
            bit_index += n_lsb
        
        # Status message
        encryption_status = "encrypted" if encryption_key else "unencrypted"
        placement_status = "random placement" if use_random_placement else "sequential placement"
        status = f"Embedded {len(secret_data)} bytes ({encryption_status}, {placement_status}, {n_lsb}-LSB)"
        
        return stego_samples, status
    
    def extract(self,
                stego_samples: np.ndarray,
                n_lsb: int = 1,
                decryption_key: Optional[str] = None,
                use_random_placement: bool = False,
                stego_key: Optional[str] = None) -> Tuple[str, bytes, str]:
        """
        Extract secret data dari stego audio
        
        Args:
            stego_samples: Stego audio samples
            n_lsb: Jumlah LSB yang digunakan saat embedding
            decryption_key: Kunci dekripsi (None jika tidak terenkripsi)
            use_random_placement: Apakah menggunakan penempatan acak
            stego_key: Kunci untuk seed random placement
            
        Returns:
            Tuple[str, bytes, str]: (filename, extracted_data, status_message)
            
        Raises:
            ValueError: Jika ekstraksi gagal atau parameter tidak valid
        """
        # Validasi parameter
        if n_lsb < 1 or n_lsb > 4:
            raise ValueError("n_lsb harus antara 1-4")
        
        # Konversi ke int16 jika diperlukan
        if stego_samples.dtype != np.int16:
            stego_samples = stego_samples.astype(np.int16)
        
        total_samples = len(stego_samples)
        
        # Estimasi posisi embedding untuk membaca metadata
        # Kita perlu setidaknya 8 bytes untuk metadata minimal (4+4)
        metadata_bits_needed = 64  # 8 bytes * 8 bits
        metadata_samples_needed = (metadata_bits_needed + n_lsb - 1) // n_lsb
        
        if metadata_samples_needed > total_samples:
            raise ValueError("Audio terlalu pendek untuk mengandung data tersembunyi")
        
        # Tentukan posisi pembacaan
        if use_random_placement and stego_key:
            # Untuk random placement, kita perlu estimasi jumlah sample yang dibutuhkan
            # Kita mulai dengan estimasi untuk metadata, lalu expand sesuai kebutuhan
            estimated_samples = min(total_samples, total_samples // 2)  # Estimasi konservatif
            positions = generate_random_positions(total_samples, estimated_samples, stego_key)
        else:
            positions = list(range(total_samples))
        
        # Extract bits from LSB
        extracted_bits = []
        for pos in positions:
            lsb_value = get_lsb(stego_samples[pos], n_lsb)
            
            # Konversi lsb_value ke bits (MSB first)
            for i in range(n_lsb - 1, -1, -1):
                extracted_bits.append((lsb_value >> i) & 1)
        
        # Coba parse metadata untuk mendapatkan panjang data sebenarnya
        try:
            # Debug informasi
            print(f"Debug: Total extracted bits: {len(extracted_bits)}")
            
            # Pertama, coba baca panjang filename (4 bytes = 32 bits)
            if len(extracted_bits) < 32:
                raise ValueError(f"Tidak cukup bits untuk membaca metadata: {len(extracted_bits)} < 32")
            
            filename_length_bits = extracted_bits[:32]
            filename_length_bytes = bits_to_bytes(filename_length_bits)
            filename_length = int.from_bytes(filename_length_bytes, 'little')
            
            print(f"Debug: Filename length: {filename_length}")
            
            # Validasi filename length (tidak boleh terlalu besar)
            if filename_length > 1000:  # Maksimal 1000 karakter untuk filename
                raise ValueError(f"Filename length tidak valid ({filename_length}), kemungkinan bukan stego audio atau parameter ekstraksi salah")
            
            # Hitung total bits yang dibutuhkan untuk payload lengkap
            # 4 (filename_length) + filename_length + 4 (data_length) + minimal data
            min_payload_bytes = 4 + filename_length + 4
            min_payload_bits = min_payload_bytes * 8
            
            if len(extracted_bits) < min_payload_bits:
                raise ValueError(f"Tidak cukup bits untuk payload lengkap: {len(extracted_bits)} < {min_payload_bits}")
            
            # Baca data_length setelah filename
            data_length_start = 32 + (filename_length * 8)  # Setelah filename_length + filename
            if len(extracted_bits) < data_length_start + 32:
                raise ValueError(f"Tidak cukup bits untuk membaca data length: {len(extracted_bits)} < {data_length_start + 32}")
            
            data_length_bits = extracted_bits[data_length_start:data_length_start + 32]
            data_length_bytes = bits_to_bytes(data_length_bits)
            data_length = int.from_bytes(data_length_bytes, 'little')
            
            print(f"Debug: Data length: {data_length}")
            
            # Validasi data length
            if data_length > 100 * 1024 * 1024:  # Maksimal 100MB
                raise ValueError(f"Data length terlalu besar: {data_length}")
            
            # Hitung total payload size
            total_payload_bytes = 4 + filename_length + 4 + data_length
            total_payload_bits = total_payload_bytes * 8
            
            print(f"Debug: Total payload bits needed: {total_payload_bits}")
            
            if len(extracted_bits) < total_payload_bits:
                raise ValueError(f"Tidak cukup bits untuk payload lengkap: {len(extracted_bits)} < {total_payload_bits}")
            
            # Extract payload lengkap
            payload_bits = extracted_bits[:total_payload_bits]
            payload_bytes = bits_to_bytes(payload_bits)
            
            print(f"Debug: Extracted payload bytes: {len(payload_bytes)}")
            
        except Exception as e:
            raise ValueError(f"Gagal membaca metadata: {str(e)}")
        
        # Dekripsi jika diperlukan
        if decryption_key:
            try:
                payload_bytes = self.cipher.decrypt(payload_bytes, decryption_key)
            except Exception as e:
                raise ValueError(f"Gagal dekripsi: {str(e)}")
        
        # Extract filename dan data
        try:
            filename, extracted_data = extract_payload(payload_bytes)
        except Exception as e:
            raise ValueError(f"Gagal parse payload: {str(e)}")
        
        # Status message
        decryption_status = "decrypted" if decryption_key else "unencrypted"
        placement_status = "random placement" if use_random_placement else "sequential placement"
        status = f"Extracted {len(extracted_data)} bytes ({decryption_status}, {placement_status}, {n_lsb}-LSB)"
        
        return filename, extracted_data, status


def test_lsb_steganography():
    """
    Test function untuk LSB steganography
    """
    # Buat audio samples dummy
    sample_rate = 44100
    duration = 2  # 2 detik
    t = np.linspace(0, duration, sample_rate * duration)
    
    # Sinyal sinus sederhana
    frequency = 440  # A4
    audio_samples = (np.sin(2 * np.pi * frequency * t) * 16000).astype(np.int16)
    
    # Data rahasia
    secret_data = b"Hello, this is a secret message for testing LSB steganography!"
    filename = "secret.txt"
    
    # Test parameter
    n_lsb = 2
    encryption_key = "mysecretkey"
    stego_key = "randomseed"
    
    print("Testing Multiple-LSB Steganography")
    print(f"Original audio shape: {audio_samples.shape}")
    print(f"Secret data: {len(secret_data)} bytes")
    print(f"Using {n_lsb}-LSB with encryption and random placement")
    
    # Initialize steganography
    stegano = MultipleLSBSteganography()
    
    try:
        # Test embedding
        stego_samples, embed_status = stegano.embed(
            audio_samples=audio_samples,
            secret_data=secret_data,
            n_lsb=n_lsb,
            filename=filename,
            encryption_key=encryption_key,
            use_random_placement=True,
            stego_key=stego_key
        )
        
        print(f"Embed status: {embed_status}")
        
        # Test extraction
        extracted_filename, extracted_data, extract_status = stegano.extract(
            stego_samples=stego_samples,
            n_lsb=n_lsb,
            decryption_key=encryption_key,
            use_random_placement=True,
            stego_key=stego_key
        )
        
        print(f"Extract status: {extract_status}")
        print(f"Extracted filename: {extracted_filename}")
        print(f"Extracted data: {len(extracted_data)} bytes")
        
        # Verifikasi
        success = (
            filename == extracted_filename and
            secret_data == extracted_data
        )
        
        print(f"Test result: {'SUCCESS' if success else 'FAILED'}")
        
        if success:
            print(f"Original: {secret_data[:50]}...")
            print(f"Extracted: {extracted_data[:50]}...")
        
    except Exception as e:
        print(f"Test failed: {str(e)}")


if __name__ == "__main__":
    test_lsb_steganography()