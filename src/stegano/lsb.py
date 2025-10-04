import json
import math
import mimetypes
import os
import random
import stat
from hashlib import sha256
from typing import Tuple, Optional
from zlib import crc32

from stegano.utils import (
    bytes_to_bits,
    collect_frames_and_regions,
    key_to_seed,
    vigenere256_encrypt,
)


_MAGIC = b"MLSBv3"
_FLAG_ENCRYPTED = 1 << 0
_FLAG_RANDOM_START = 1 << 1
_HEADER_LEN_FIXED = 22


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
            data = vigenere256_encrypt(data, key)
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
        msg_bits = bytes_to_bits(message)

        regs = collect_frames_and_regions(mp3)
        if not regs:
            raise RuntimeError("No usable MP3 frames found.")
        total_bytes_md = sum(e - s for s, e in regs)
        start_offset = 0
        if random_start:
            start_offset = random.Random(key_to_seed(key)).randrange(0, total_bytes_md)
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
        regs = collect_frames_and_regions(mp3)
        if not regs:
            raise RuntimeError("No MP3 frames/regions found.")
        stream = bytearray()
        for s, e in regs:
            stream.extend(mp3[s:e])
        total_bytes = len(stream)
        if total_bytes == 0:
            raise RuntimeError("Main-data stream empty.")

        cand_offsets = [0, random.Random(key_to_seed(key)).randrange(0, total_bytes)]

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
