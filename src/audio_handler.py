"""
Audio Handler untuk load dan save file audio MP3
Implementasi menggunakan FFmpeg untuk kompatibilitas Python 3.13+
Dilengkapi dengan AudioPlayer menggunakan pygame untuk playback audio
"""

import numpy as np
import os
import subprocess
import tempfile
import threading
import time
from typing import Tuple, Optional, Callable
import pygame
from pygame import mixer


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


class AudioPlayer:
    """
    Kelas untuk memainkan file audio MP3 menggunakan pygame
    """
    
    def __init__(self, on_position_change: Optional[Callable[[float], None]] = None):
        """
        Inisialisasi AudioPlayer
        
        Args:
            on_position_change: Callback function untuk update posisi playback (detik)
        """
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
        
        self.current_file = None
        self.duration = 0.0
        self.is_playing = False
        self.is_paused = False
        self.position = 0.0
        self.volume = 0.7
        
        # Callback untuk update posisi
        self.on_position_change = on_position_change
        
        # Thread untuk update posisi
        self.position_thread = None
        self.stop_position_thread = False
        
    def load(self, file_path: str) -> bool:
        """
        Load file audio MP3
        
        Args:
            file_path: Path ke file MP3
            
        Returns:
            bool: True jika berhasil load
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File tidak ditemukan: {file_path}")
            
            # Stop playback yang sedang berjalan
            self.stop()
            
            # Load file ke pygame mixer
            pygame.mixer.music.load(file_path)
            
            self.current_file = file_path
            
            # Dapatkan durasi file menggunakan AudioHandler
            audio_handler = AudioHandler()
            info = audio_handler.get_audio_info(file_path)
            self.duration = info['duration_seconds']
            
            self.position = 0.0
            self.is_playing = False
            self.is_paused = False
            
            return True
            
        except Exception as e:
            print(f"Error loading audio: {e}")
            return False
    
    def play(self) -> bool:
        """
        Mulai playback audio
        
        Returns:
            bool: True jika berhasil play
        """
        try:
            if self.current_file is None:
                return False
            
            if self.is_paused:
                # Resume dari pause
                pygame.mixer.music.unpause()
                self.is_paused = False
            else:
                # Start dari awal atau posisi tertentu
                pygame.mixer.music.play(start=self.position)
            
            self.is_playing = True
            
            # Start thread untuk update posisi
            self._start_position_thread()
            
            return True
            
        except Exception as e:
            print(f"Error playing audio: {e}")
            return False
    
    def pause(self) -> bool:
        """
        Pause playback audio
        
        Returns:
            bool: True jika berhasil pause
        """
        try:
            if self.is_playing and not self.is_paused:
                pygame.mixer.music.pause()
                self.is_paused = True
                self._stop_position_thread()
                return True
            return False
            
        except Exception as e:
            print(f"Error pausing audio: {e}")
            return False
    
    def stop(self) -> bool:
        """
        Stop playback audio
        
        Returns:
            bool: True jika berhasil stop
        """
        try:
            pygame.mixer.music.stop()
            self.is_playing = False
            self.is_paused = False
            self.position = 0.0
            self._stop_position_thread()
            return True
            
        except Exception as e:
            print(f"Error stopping audio: {e}")
            return False
    
    def set_volume(self, volume: float) -> bool:
        """
        Set volume playback (0.0 - 1.0)
        
        Args:
            volume: Volume level (0.0 = mute, 1.0 = max)
            
        Returns:
            bool: True jika berhasil set volume
        """
        try:
            volume = max(0.0, min(1.0, volume))  # Clamp ke range 0-1
            pygame.mixer.music.set_volume(volume)
            self.volume = volume
            return True
            
        except Exception as e:
            print(f"Error setting volume: {e}")
            return False
    
    def get_volume(self) -> float:
        """
        Get current volume level
        
        Returns:
            float: Volume level (0.0 - 1.0)
        """
        return self.volume
    
    def set_position(self, position: float) -> bool:
        """
        Set posisi playback (dalam detik)
        
        CATATAN: pygame.mixer.music tidak mendukung seeking untuk MP3.
        Fungsi ini hanya akan mengupdate posisi internal untuk UI,
        tetapi tidak dapat mengubah posisi playback sebenarnya.
        
        Args:
            position: Posisi dalam detik
            
        Returns:
            bool: True jika berhasil set posisi (hanya untuk UI)
        """
        try:
            if self.current_file is None or position < 0 or position > self.duration:
                return False
            
            # PERINGATAN: pygame.mixer.music tidak mendukung seeking untuk MP3
            # Kita hanya bisa restart dari awal
            was_playing = self.is_playing and not self.is_paused
            
            if abs(position - 0.0) < 0.1:  # Jika posisi mendekati 0, restart
                # Stop current playback
                pygame.mixer.music.stop()
                self.position = 0.0
                
                # Restart jika sedang playing
                if was_playing:
                    pygame.mixer.music.play()
                    self._start_position_thread()
                return True
            else:
                # Untuk posisi selain 0, kita tidak bisa melakukan seeking
                # Hanya update posisi UI tanpa mengubah playback
                print(f"Warning: Cannot seek to position {position:.1f}s. MP3 seeking not supported by pygame.mixer.music")
                return False
            
        except Exception as e:
            print(f"Error setting position: {e}")
            return False
    
    def get_position(self) -> float:
        """
        Get posisi playback saat ini (dalam detik)
        
        Returns:
            float: Posisi dalam detik
        """
        return self.position
    
    def get_duration(self) -> float:
        """
        Get durasi total audio (dalam detik)
        
        Returns:
            float: Durasi dalam detik
        """
        return self.duration
    
    def is_busy(self) -> bool:
        """
        Cek apakah audio sedang playing
        
        Returns:
            bool: True jika sedang playing
        """
        return pygame.mixer.music.get_busy() or self.is_playing
    
    def _start_position_thread(self):
        """Start thread untuk update posisi playback"""
        self._stop_position_thread()
        self.stop_position_thread = False
        self.position_thread = threading.Thread(target=self._position_updater)
        self.position_thread.daemon = True
        self.position_thread.start()
    
    def _stop_position_thread(self):
        """Stop thread update posisi"""
        self.stop_position_thread = True
        if self.position_thread and self.position_thread.is_alive():
            self.position_thread.join(timeout=0.1)
    
    def _position_updater(self):
        """Thread function untuk update posisi secara real-time"""
        start_time = time.time()
        start_position = self.position
        
        while not self.stop_position_thread and self.is_playing:
            if not self.is_paused and pygame.mixer.music.get_busy():
                elapsed = time.time() - start_time
                self.position = start_position + elapsed
                
                # Pastikan tidak melebihi durasi
                if self.position >= self.duration:
                    self.position = self.duration
                    self.is_playing = False
                    break
                
                # Callback untuk update UI
                if self.on_position_change:
                    self.on_position_change(self.position)
            
            elif not pygame.mixer.music.get_busy() and self.is_playing:
                # Playback selesai
                self.is_playing = False
                self.position = self.duration
                if self.on_position_change:
                    self.on_position_change(self.position)
                break
            
            time.sleep(0.1)  # Update setiap 100ms
    
    def cleanup(self):
        """Cleanup resources"""
        self.stop()
        self._stop_position_thread()
        pygame.mixer.quit()


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
    
    # Test AudioPlayer
    print("\n3. Testing AudioPlayer...")
    try:
        def position_callback(pos):
            print(f"Position: {pos:.1f}s", end='\r')
        
        player = AudioPlayer(on_position_change=position_callback)
        print("AudioPlayer initialized successfully")
        
        # Test dengan file yang ada di assets
        test_files = [
            "assets/fake.mp3",
            "assets/Terima Kasih Pak JOKOWI - Kang Lidan (Official Music Video).mp3"
        ]
        
        for test_file in test_files:
            if os.path.exists(test_file):
                print(f"\nTesting with: {test_file}")
                if player.load(test_file):
                    print(f"Loaded successfully. Duration: {player.get_duration():.1f}s")
                    print("Volume test...")
                    player.set_volume(0.5)
                    print(f"Volume set to: {player.get_volume()}")
                    
                    # Test play sebentar
                    print("Playing for 2 seconds...")
                    if player.play():
                        time.sleep(2)
                        player.stop()
                        print("Play test completed")
                    break
                else:
                    print(f"Failed to load: {test_file}")
        
        player.cleanup()
        
    except Exception as e:
        print(f"AudioPlayer test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_audio_handler()