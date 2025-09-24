"""
PSNR (Peak Signal-to-Noise Ratio) Calculator
Untuk mengukur kualitas audio setelah steganografi
"""

import numpy as np
from typing import Union


def calculate_psnr(original: np.ndarray, modified: np.ndarray) -> float:
    """
    Menghitung PSNR antara audio original dan modified
    
    Args:
        original: Array numpy dari audio original
        modified: Array numpy dari audio yang sudah dimodifikasi
        
    Returns:
        float: Nilai PSNR dalam dB
        
    Raises:
        ValueError: Jika array memiliki shape yang berbeda
    """
    if original.shape != modified.shape:
        raise ValueError("Original dan modified audio harus memiliki shape yang sama")
    
    # Pastikan kedua array adalah float untuk perhitungan yang akurat
    original = original.astype(np.float64)
    modified = modified.astype(np.float64)
    
    # Hitung MSE (Mean Squared Error)
    mse = np.mean((original - modified) ** 2)
    
    # Jika MSE = 0, berarti tidak ada perbedaan (PSNR tak terhingga)
    if mse == 0:
        return float('inf')
    
    # Tentukan nilai maksimum signal
    # Untuk audio 16-bit: maksimum = 2^15 - 1 = 32767
    # Untuk audio float: maksimum = 1.0
    if original.dtype == np.int16 or np.max(np.abs(original)) > 1.0:
        max_signal = 32767.0  # 16-bit audio
    else:
        max_signal = 1.0  # Normalized audio
    
    # Hitung PSNR: PSNR = 20 * log10(MAX / sqrt(MSE))
    psnr = 20 * np.log10(max_signal / np.sqrt(mse))
    
    return psnr


def calculate_mse(original: np.ndarray, modified: np.ndarray) -> float:
    """
    Menghitung MSE (Mean Squared Error) antara dua sinyal
    
    Args:
        original: Array numpy dari sinyal original
        modified: Array numpy dari sinyal modified
        
    Returns:
        float: Nilai MSE
    """
    if original.shape != modified.shape:
        raise ValueError("Array harus memiliki shape yang sama")
    
    return np.mean((original.astype(np.float64) - modified.astype(np.float64)) ** 2)


def calculate_snr(signal: np.ndarray, noise: np.ndarray) -> float:
    """
    Menghitung SNR (Signal-to-Noise Ratio)
    
    Args:
        signal: Array numpy dari sinyal
        noise: Array numpy dari noise
        
    Returns:
        float: Nilai SNR dalam dB
    """
    signal_power = np.mean(signal.astype(np.float64) ** 2)
    noise_power = np.mean(noise.astype(np.float64) ** 2)
    
    if noise_power == 0:
        return float('inf')
    
    snr = 10 * np.log10(signal_power / noise_power)
    return snr


def evaluate_audio_quality(psnr: float) -> str:
    """
    Memberikan evaluasi kualitas audio berdasarkan nilai PSNR
    
    Args:
        psnr: Nilai PSNR dalam dB
        
    Returns:
        str: Evaluasi kualitas
    """
    if psnr >= 40:
        return "Excellent (>= 40 dB)"
    elif psnr >= 30:
        return "Good (30-40 dB)"
    elif psnr >= 20:
        return "Fair (20-30 dB)"
    elif psnr >= 10:
        return "Poor (10-20 dB)"
    else:
        return "Very Poor (< 10 dB)"


def test_psnr():
    """
    Test function untuk PSNR calculator
    """
    # Buat sinyal test
    t = np.linspace(0, 1, 44100)  # 1 detik audio 44.1kHz
    original = np.sin(2 * np.pi * 440 * t)  # Nada A4
    
    # Tambahkan noise kecil
    noise = np.random.normal(0, 0.01, len(original))
    modified = original + noise
    
    # Hitung PSNR
    psnr = calculate_psnr(original, modified)
    mse = calculate_mse(original, modified)
    
    print(f"Original signal shape: {original.shape}")
    print(f"Modified signal shape: {modified.shape}")
    print(f"MSE: {mse:.6f}")
    print(f"PSNR: {psnr:.2f} dB")
    print(f"Quality: {evaluate_audio_quality(psnr)}")
    
    # Test dengan sinyal identik
    psnr_identical = calculate_psnr(original, original)
    print(f"\nPSNR identical signals: {psnr_identical} dB")


if __name__ == "__main__":
    test_psnr()