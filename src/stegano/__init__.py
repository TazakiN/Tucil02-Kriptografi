from .lsb import MultipleLSBSteganography
from .utils import (
    bytes_to_bits,
    vigenere256_encrypt,
    key_to_seed,
    collect_frames_and_regions,
    evaluate_audio_quality,
)

__version__ = "1.0.0"
__author__ = "Tucil 2 Kripto"

__all__ = [
    "MultipleLSBSteganography",
    "bytes_to_bits",
    "vigenere256_encrypt",
    "key_to_seed",
    "collect_frames_and_regions",
    "evaluate_audio_quality",
]
