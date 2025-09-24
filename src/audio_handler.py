"""
Audio Handler untuk load dan save file audio MP3
Implementasi menggunakan FFmpeg untuk kompatibilitas Python 3.13+
"""

import numpy as np
import os
import subprocess
import tempfile
from typing import Tuple, Optional


class AudioHandler:
    """
    Kelas untuk menangani operasi audio MP3
    """
    
    def __init__(self):
        # Cek apakah ffmpeg tersedia (wajib untuk MP3)
        self.ffmpeg_available = self._check_ffmpeg()
        if not self.ffmpeg_available:
            raise RuntimeError("FFmpeg diperlukan untuk menangani file MP3. Silakan install FFmpeg terlebih dahulu.")
    
    def _check_ffmpeg(self) -> bool:
        """Cek apakah ffmpeg tersedia"""
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def load_mp3(self, file_path: str) -> Tuple[np.ndarray, int]:
        """
        Load file MP3 dan konversi ke numpy array
        
        Args:
            file_path: Path ke file MP3
            
        Returns:
            Tuple[np.ndarray, int]: (audio_samples, sample_rate)
            
        Raises:
            FileNotFoundError: Jika file tidak ditemukan
            ValueError: Jika file tidak bisa diload
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File tidak ditemukan: {file_path}")
        
        try:
            # Konversi MP3 ke raw PCM menggunakan ffmpeg
            cmd = [
                "ffmpeg", "-i", file_path,
                "-ac", "1",  # mono
                "-ar", "44100",  # sample rate 44.1kHz
                "-f", "s16le",  # format: signed 16-bit little endian
                "-"  # output ke stdout
            ]
            
            result = subprocess.run(cmd, capture_output=True, check=True)
            
            # Konversi raw PCM data ke numpy array
            samples = np.frombuffer(result.stdout, dtype=np.int16)
            sample_rate = 44100  # Fixed sample rate
            
            return samples, sample_rate
            
        except subprocess.CalledProcessError as e:
            raise ValueError(f"Gagal load MP3: {e}")
        except Exception as e:
            raise ValueError(f"Gagal load audio: {str(e)}")
    
    def save_mp3(self, samples: np.ndarray, sample_rate: int, output_path: str,
                 bitrate: str = "128k") -> None:
        """
        Save numpy array ke file MP3
        
        Args:
            samples: Audio samples (numpy array)
            sample_rate: Sample rate audio
            output_path: Path output file
            bitrate: Bitrate MP3 (default: 128k)
            
        Raises:
            ValueError: Jika gagal save audio
        """
        try:
            # Pastikan samples dalam range 16-bit
            samples = np.clip(samples, -32768, 32767).astype(np.int16)
            
            # Konversi numpy array ke MP3 menggunakan ffmpeg
            cmd = [
                "ffmpeg", 
                "-f", "s16le",  # input format: signed 16-bit little endian
                "-ar", str(sample_rate),  # sample rate
                "-ac", "1",  # mono
                "-i", "-",  # input dari stdin
                "-b:a", bitrate,  # bitrate
                "-y",  # overwrite
                output_path
            ]
            
            # Kirim raw audio data ke ffmpeg via stdin
            process = subprocess.Popen(cmd, stdin=subprocess.PIPE, 
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate(input=samples.tobytes())
            
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, cmd, stderr)
            
        except subprocess.CalledProcessError as e:
            raise ValueError(f"Gagal save MP3: {e}")
        except Exception as e:
            raise ValueError(f"Gagal save audio: {str(e)}")
    

    
    def get_audio_info(self, file_path: str) -> dict:
        """
        Get informasi audio file MP3
        
        Args:
            file_path: Path ke file MP3
            
        Returns:
            dict: Informasi audio (duration, sample_rate, channels, dll.)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File tidak ditemukan: {file_path}")
        
        try:
            # Load untuk mendapatkan info
            samples, sample_rate = self.load_mp3(file_path)
            duration_seconds = len(samples) / sample_rate
            
            info = {
                'duration_seconds': duration_seconds,
                'duration_ms': duration_seconds * 1000,
                'sample_rate': sample_rate,
                'channels': 1,  # Selalu dikonversi ke mono
                'sample_width': 2,  # Selalu 16-bit
                'frame_count': len(samples),
                'sample_count': len(samples),
                'bitrate': None,
                'format': 'mp3'
            }
            
            return info
            
        except Exception as e:
            raise ValueError(f"Gagal get audio info: {str(e)}")
    

    
    def create_dummy_audio(self, duration_seconds: float = 10.0, 
                          frequency: float = 440.0, 
                          sample_rate: int = 44100) -> Tuple[np.ndarray, int]:
        """
        Buat dummy audio untuk testing
        
        Args:
            duration_seconds: Durasi dalam detik
            frequency: Frekuensi tone (Hz)
            sample_rate: Sample rate
            
        Returns:
            Tuple[np.ndarray, int]: (audio_samples, sample_rate)
        """
        t = np.linspace(0, duration_seconds, int(sample_rate * duration_seconds))
        
        # Buat sinyal sinus
        samples = (np.sin(2 * np.pi * frequency * t) * 16000).astype(np.int16)
        
        return samples, sample_rate


def test_audio_handler():
    """
    Test function untuk AudioHandler
    """
    try:
        handler = AudioHandler()
        
        print("Testing AudioHandler")
        print(f"FFmpeg available: {handler.ffmpeg_available}")
        
        # Buat dummy audio
        print("\n1. Creating dummy audio...")
        samples, sample_rate = handler.create_dummy_audio(duration_seconds=2.0)
        print(f"Created audio: {len(samples)} samples at {sample_rate} Hz")
        print(f"Duration: {len(samples) / sample_rate:.2f} seconds")
        
        # Test save/load MP3
        print("\n2. Testing MP3 save/load...")
        try:
            temp_mp3 = "test_audio.mp3"
            handler.save_mp3(samples, sample_rate, temp_mp3)
            print(f"Saved MP3: {temp_mp3}")
            
            # Load kembali
            loaded_samples, loaded_sr = handler.load_mp3(temp_mp3)
            print(f"Loaded MP3: {len(loaded_samples)} samples at {loaded_sr} Hz")
            
            # MP3 adalah lossy, jadi tidak akan sama persis
            print(f"Sample count difference: {abs(len(samples) - len(loaded_samples))}")
            
            # Get info
            info = handler.get_audio_info(temp_mp3)
            print(f"Audio info: {info['duration_seconds']:.2f}s, {info['channels']} ch")
            
            # Cleanup
            if os.path.exists(temp_mp3):
                os.remove(temp_mp3)
                
        except Exception as e:
            print(f"MP3 test failed: {e}")
            
    except RuntimeError as e:
        print(f"AudioHandler initialization failed: {e}")
        print("Please install FFmpeg to use this application.")


if __name__ == "__main__":
    test_audio_handler()