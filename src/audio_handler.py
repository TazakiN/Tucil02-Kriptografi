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
    def __init__(self):
        # Cek apakah ffmpeg tersedia (wajib untuk MP3)
        self.ffmpeg_available = self._check_ffmpeg()
        if not self.ffmpeg_available:
            raise RuntimeError(
                "FFmpeg diperlukan untuk menangani file MP3. Silakan install FFmpeg terlebih dahulu."
            )

    def _check_ffmpeg(self) -> bool:
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def load_mp3(self, file_path: str) -> Tuple[np.ndarray, int]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File tidak ditemukan: {file_path}")

        try:
            # Konversi MP3 ke raw PCM menggunakan ffmpeg
            cmd = [
                "ffmpeg",
                "-i",
                file_path,
                "-ac",
                "1",  # mono
                "-ar",
                "44100",  # sample rate 44.1kHz
                "-f",
                "s16le",  # format: signed 16-bit little endian
                "-",  # output ke stdout
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

    def save_mp3(
        self,
        samples: np.ndarray,
        sample_rate: int,
        output_path: str,
        bitrate: str = "128k",
    ) -> None:
        try:
            # Pastikan samples dalam range 16-bit
            samples = np.clip(samples, -32768, 32767).astype(np.int16)

            # Konversi numpy array ke MP3 menggunakan ffmpeg
            cmd = [
                "ffmpeg",
                "-f",
                "s16le",  # input format: signed 16-bit little endian
                "-ar",
                str(sample_rate),  # sample rate
                "-ac",
                "1",  # mono
                "-i",
                "-",  # input dari stdin
                "-b:a",
                bitrate,  # bitrate
                "-y",  # overwrite
                output_path,
            ]

            # Kirim raw audio data ke ffmpeg via stdin
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = process.communicate(input=samples.tobytes())

            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, cmd, stderr)

        except subprocess.CalledProcessError as e:
            raise ValueError(f"Gagal save MP3: {e}")
        except Exception as e:
            raise ValueError(f"Gagal save audio: {str(e)}")

    def get_audio_info(self, file_path: str) -> dict:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File tidak ditemukan: {file_path}")

        try:
            # Load untuk mendapatkan info
            samples, sample_rate = self.load_mp3(file_path)
            duration_seconds = len(samples) / sample_rate

            info = {
                "duration_seconds": duration_seconds,
                "duration_ms": duration_seconds * 1000,
                "sample_rate": sample_rate,
                "channels": 1,  # Selalu dikonversi ke mono
                "sample_width": 2,  # Selalu 16-bit
                "frame_count": len(samples),
                "sample_count": len(samples),
                "bitrate": None,
                "format": "mp3",
            }

            return info

        except Exception as e:
            raise ValueError(f"Gagal get audio info: {str(e)}")


class AudioPlayer:
    def __init__(self, on_position_change: Optional[Callable[[float], None]] = None):
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
            self.duration = info["duration_seconds"]

            self.position = 0.0
            self.is_playing = False
            self.is_paused = False

            return True

        except Exception as e:
            print(f"Error loading audio: {e}")
            return False

    def play(self) -> bool:
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
        try:
            volume = max(0.0, min(1.0, volume))  # Clamp ke range 0-1
            pygame.mixer.music.set_volume(volume)
            self.volume = volume
            return True

        except Exception as e:
            print(f"Error setting volume: {e}")
            return False

    def get_volume(self) -> float:
        return self.volume

    def set_position(self, position: float) -> bool:
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
                print(
                    f"Warning: Cannot seek to position {position:.1f}s. MP3 seeking not supported by pygame.mixer.music"
                )
                return False

        except Exception as e:
            print(f"Error setting position: {e}")
            return False

    def get_position(self) -> float:
        return self.position

    def get_duration(self) -> float:
        return self.duration

    def is_busy(self) -> bool:
        return pygame.mixer.music.get_busy() or self.is_playing

    def _start_position_thread(self):
        self._stop_position_thread()
        self.stop_position_thread = False
        self.position_thread = threading.Thread(target=self._position_updater)
        self.position_thread.daemon = True
        self.position_thread.start()

    def _stop_position_thread(self):
        self.stop_position_thread = True
        if self.position_thread and self.position_thread.is_alive():
            self.position_thread.join(timeout=0.1)

    def _position_updater(self):
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
        self.stop()
        self._stop_position_thread()
        pygame.mixer.quit()
