import argparse
import json
import math
import mimetypes
import os
import random
import stat
from hashlib import sha256
from typing import List, Tuple, Optional
from zlib import crc32


# --------------------------- Extended Vigenère 256 ---------------------------
def _vigenere256_encrypt(data: bytes, key: str) -> bytes:
    if not key:
        return data
    kb = key.encode("utf-8")
    out = bytearray(len(data))
    for i, b in enumerate(data):
        out[i] = (b + kb[i % len(kb)]) & 0xFF
    return bytes(out)


# --------------------------- Seed from key -----------------------------------
def _key_to_seed(key: str) -> int:
    h = sha256(key.encode("utf-8")).digest()
    return int.from_bytes(h[:4], "big")


# --------------------------- Bit helpers ------------------------------------
def _bytes_to_bits(b: bytes) -> List[int]:
    return [(b[i // 8] >> (7 - (i % 8))) & 1 for i in range(len(b) * 8)]


# --------------------------- MP3 helpers (robust) ----------------------------
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


def _collect_frames_and_regions(mp3: bytes, max_main_bytes_per_frame: int = 512):
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


# --------------------------- Header & constants ------------------------------
_MAGIC = b"MLSBv3"
_FLAG_ENCRYPTED = 1 << 0
_FLAG_RANDOM_START = 1 << 1
_HEADER_LEN_FIXED = 22


# --------------------------- PSNR --------------------------------------------
def _compute_psnr(a: bytes, b: bytes) -> float:
    assert len(a) == len(b)
    if len(a) == 0:
        return float("inf")
    mse = 0.0
    for x, y in zip(a, b):
        d = x - y
        mse += d * d
    mse /= len(a)
    if mse == 0:
        return float("inf")
    MAX = 255.0
    return 10.0 * math.log10((MAX * MAX) / mse)


# --------------------------- Metadata helpers --------------------------------
def _file_metadata(path: str, payload: bytes) -> dict:
    st = os.stat(path)
    base = os.path.basename(path)
    _, ext = os.path.splitext(base)
    mime, _ = mimetypes.guess_type(base)
    return {
        "filename": base,
        "ext": ext,
        "mime": mime or "application/octet-stream",
        "size": len(payload),
        "mtime": int(st.st_mtime),
        "mode": stat.S_IMODE(st.st_mode),
        "sha256": sha256(payload).hexdigest(),
    }


def _apply_metadata(path: str, meta: dict):
    try:
        if "mode" in meta:
            try:
                os.chmod(path, meta["mode"])
            except Exception:
                pass
        if "mtime" in meta:
            try:
                os.utime(path, (meta["mtime"], meta["mtime"]))
            except Exception:
                pass
    except Exception:
        pass


def _resolve_output_path(out_path: Optional[str], meta: dict) -> str:
    fn = (
        meta.get("filename", "recovered.bin")
        if isinstance(meta, dict)
        else "recovered.bin"
    )
    if not out_path or out_path.strip() == "":
        return fn
    if os.path.isdir(out_path) or out_path.endswith(os.sep):
        os.makedirs(out_path, exist_ok=True)
        return os.path.join(out_path, fn)
    parent = os.path.dirname(out_path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)
    return out_path


class MultipleLSBSteganography:
    """
    MP3 Multiple-LSB steganography utilities used by the GUI.

    Public file-based methods:
      - embed_file(in_mp3, payload_path, out_path, key, nlsb, encrypt=True, random_start=True)
      - extract_file(in_mp3, out_path_or_dir, key, restore_meta=True)
    """

    def embed_file(
        self,
        mp3_path: str,
        payload_path: str,
        out_path: str,
        key: str,
        nlsb: int,
        encrypt: bool = True,
        random_start: bool = True,
    ) -> str:
        if nlsb < 1 or nlsb > 4:
            raise ValueError("n_lsb harus antara 1-4")
        mp3 = open(mp3_path, "rb").read()
        payload_plain = open(payload_path, "rb").read()

        meta_json = json.dumps(
            _file_metadata(payload_path, payload_plain), separators=(",", ":")
        ).encode("utf-8")

        flags = 0
        data = payload_plain
        if encrypt:
            flags |= _FLAG_ENCRYPTED
            data = _vigenere256_encrypt(data, key)
        if random_start:
            flags |= _FLAG_RANDOM_START

        crc = crc32(data) & 0xFFFFFFFF
        header = (
            _MAGIC
            + bytes([flags & 0xFF])
            + bytes([nlsb & 0xFF])
            + len(data).to_bytes(4, "big")
            + crc.to_bytes(4, "big")
            + len(meta_json).to_bytes(4, "big")
            + b"\x00\x00"
            + meta_json
        )

        message = header + data
        msg_bits = _bytes_to_bits(message)

        regs = _collect_frames_and_regions(mp3)
        if not regs:
            raise RuntimeError("No usable MP3 frames found.")
        total_bytes_md = sum(e - s for s, e in regs)
        start_offset = 0
        if random_start:
            start_offset = random.Random(_key_to_seed(key)).randrange(0, total_bytes_md)
        cap_bits = (total_bytes_md - start_offset) * nlsb
        if cap_bits < len(msg_bits):
            raise RuntimeError(
                f"Insufficient capacity: need {len(msg_bits)} bits, have {cap_bits} bits."
            )

        mp3_out = bytearray(mp3)
        bits_idx = 0
        passed = 0
        mask = 0xFF ^ ((1 << nlsb) - 1)
        for s, e in regs:
            for pos in range(s, e):
                if passed < start_offset:
                    passed += 1
                    continue
                if bits_idx >= len(msg_bits):
                    break
                group = msg_bits[bits_idx : bits_idx + nlsb]
                v = 0
                for bit in group:
                    v = (v << 1) | (bit & 1)
                mp3_out[pos] = (mp3_out[pos] & mask) | v
                bits_idx += len(group)
            if bits_idx >= len(msg_bits):
                break
        if bits_idx < len(msg_bits):
            raise RuntimeError("Unexpected: capacity ran out after pre-check.")

        psnr = _compute_psnr(mp3, bytes(mp3_out))
        open(out_path, "wb").write(mp3_out)
        print(f"PSNR (cover vs stego): {psnr:.2f} dB")
        print(
            f"Embedded {len(message)} bytes (header+meta+payload) using {nlsb}-LSB "
            f"(encrypt={'on' if encrypt else 'off'}, random_start={'on' if random_start else 'off'}) into '{out_path}'."
        )
        return out_path

    def extract_file(
        self,
        mp3_path: str,
        out_path: Optional[str],
        key: str,
        restore_meta: bool = True,
    ) -> Tuple[str, int, str]:
        mp3 = open(mp3_path, "rb").read()
        regs = _collect_frames_and_regions(mp3)
        if not regs:
            raise RuntimeError("No MP3 frames/regions found.")
        stream = bytearray()
        for s, e in regs:
            stream.extend(mp3[s:e])
        total_bytes = len(stream)
        if total_bytes == 0:
            raise RuntimeError("Main-data stream empty.")

        cand_offsets = [0, random.Random(_key_to_seed(key)).randrange(0, total_bytes)]

        for n in (1, 2, 3, 4):
            for off in cand_offsets:
                br = _BitStreamReader(stream, off, n)
                fixed = br.read(_HEADER_LEN_FIXED)
                if (
                    len(fixed) != _HEADER_LEN_FIXED
                    or fixed[:6] != _MAGIC
                    or fixed[7] != n
                ):
                    continue
                flags = fixed[6]
                payload_len = int.from_bytes(fixed[8:12], "big")
                crc_hdr = int.from_bytes(fixed[12:16], "big")
                meta_len = int.from_bytes(fixed[16:20], "big")
                meta_bytes = br.read(meta_len)
                if len(meta_bytes) != meta_len:
                    continue
                try:
                    meta = json.loads(meta_bytes.decode("utf-8"))
                except Exception:
                    continue

                out_file = _resolve_output_path(out_path, meta)
                kb = key.encode("utf-8") if (flags & _FLAG_ENCRYPTED) else None
                km = len(kb) if kb else 0

                crc_calc = 0
                written = 0
                try:
                    with open(out_file, "wb") as f:
                        CHUNK = 1 << 16
                        while written < payload_len:
                            need = min(CHUNK, payload_len - written)
                            raw = br.read(need)
                            if len(raw) != need:
                                raise IOError("Truncated payload in stream")
                            crc_calc = crc32(raw, crc_calc)
                            if kb:
                                dec = bytearray(need)
                                for i, b in enumerate(raw):
                                    dec[i] = (b - kb[(written + i) % km]) & 0xFF
                                f.write(dec)
                            else:
                                f.write(raw)
                            written += need
                except Exception:
                    try:
                        if os.path.exists(out_file):
                            os.remove(out_file)
                    except Exception:
                        pass
                    continue

                if (crc_calc & 0xFFFFFFFF) != crc_hdr:
                    try:
                        os.remove(out_file)
                    except Exception:
                        pass
                    continue

                if restore_meta and isinstance(meta, dict):
                    _apply_metadata(out_file, meta)

                status = (
                    f"Extracted {written} bytes to '{out_file}' "
                    f"(nlsb={n}, random_start={'on' if (flags & _FLAG_RANDOM_START) else 'off'}, "
                    f"encrypted={'yes' if (flags & _FLAG_ENCRYPTED) else 'no'})."
                )
                print(status)
                return out_file, written, status

        raise RuntimeError(
            "Failed to extract at deterministic offsets. Re-embed and verify the key/options."
        )


class _BitStreamReader:
    def __init__(self, stream: bytes, start_off: int, nlsb: int):
        self.stream = stream
        self.pos = start_off
        self.n = nlsb
        self.mask = (1 << nlsb) - 1
        self.bitbuf = 0
        self.bits_in_buf = 0
        self.total = len(stream)

    def read(self, k: int) -> bytes:
        out = bytearray()
        while len(out) < k:
            if self.bits_in_buf < 8:
                if self.pos >= self.total:
                    break
                v = self.stream[self.pos] & self.mask
                self.bitbuf = (self.bitbuf << self.n) | v
                self.bits_in_buf += self.n
                self.pos += 1
                continue
            out.append((self.bitbuf >> (self.bits_in_buf - 8)) & 0xFF)
            self.bits_in_buf -= 8
        return bytes(out)
