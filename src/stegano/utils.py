from typing import List
from hashlib import sha256


def bytes_to_bits(b: bytes) -> List[int]:
    return [(b[i // 8] >> (7 - (i % 8))) & 1 for i in range(len(b) * 8)]


def vigenere256_encrypt(data: bytes, key: str) -> bytes:
    if not key:
        return data
    kb = key.encode("utf-8")
    out = bytearray(len(data))
    for i, b in enumerate(data):
        out[i] = (b + kb[i % len(kb)]) & 0xFF
    return bytes(out)


def key_to_seed(key: str) -> int:
    h = sha256(key.encode("utf-8")).digest()
    return int.from_bytes(h[:4], "big")


_BITRATE_TABLE = {
    "1": [None, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, None],
    "2": [None, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, None],
    "2.5": [None, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, None],
}

_SR_TABLE = {
    "1": [44100, 48000, 32000, None],
    "2": [22050, 24000, 16000, None],
    "2.5": [11025, 12000, 8000, None],
}


def _read_synchsafe32(b):
    return (
        ((b[0] & 0x7F) << 21)
        | ((b[1] & 0x7F) << 14)
        | ((b[2] & 0x7F) << 7)
        | (b[3] & 0x7F)
    )


def _skip_id3v2(mp3: bytes) -> int:
    if len(mp3) >= 10 and mp3[:3] == b"ID3":
        size = _read_synchsafe32(mp3[6:10])
        total = 10 + size
        return min(total, len(mp3))
    return 0


def _parse_header_at(mp3: bytes, off: int):
    if off + 4 > len(mp3):
        return None
    b1, b2, b3, b4 = mp3[off : off + 4]
    if b1 != 0xFF or (b2 & 0xE0) != 0xE0:
        return None
    ver_bits = (b2 >> 3) & 0x03
    layer_bits = (b2 >> 1) & 0x03
    if layer_bits != 0x01:
        return None
    if ver_bits == 0x01:
        return None
    version = {0x03: "1", 0x02: "2", 0x00: "2.5"}.get(ver_bits, None)
    if version is None:
        return None
    bitrate_idx = (b3 >> 4) & 0x0F
    sr_idx = (b3 >> 2) & 0x03
    padding = (b3 >> 1) & 0x01
    channel_mode = (b4 >> 6) & 0x03

    if bitrate_idx == 0 or bitrate_idx == 0x0F:
        return None
    if sr_idx == 0x03:
        return None
    br_kbps = _BITRATE_TABLE[version][bitrate_idx]
    sr = _SR_TABLE[version][sr_idx]
    if br_kbps is None or sr is None:
        return None

    coef = 144 if version == "1" else 72
    frame_len = int((coef * (br_kbps * 1000)) // sr + padding)
    if frame_len < 24:
        return None

    if version == "1":
        side_len = 17 if channel_mode == 3 else 32
    else:
        side_len = 9 if channel_mode == 3 else 17

    return {
        "frame_len": frame_len,
        "side_len": side_len,
    }


def collect_frames_and_regions(mp3: bytes, max_main_bytes_per_frame: int = 512):
    regions = []
    off = _skip_id3v2(mp3)
    L = len(mp3)
    while off + 4 <= L:
        hdr = _parse_header_at(mp3, off)
        if not hdr:
            off += 1
            continue
        fsize = hdr["frame_len"]
        if off + fsize > L:
            break
        s = off + 4 + hdr["side_len"]
        e = min(off + fsize, s + max_main_bytes_per_frame)
        if s < e:
            regions.append((s, e))
        off += fsize
    return regions


def evaluate_audio_quality(psnr: float) -> str:
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
