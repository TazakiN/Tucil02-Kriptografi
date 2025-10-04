import random
import struct
from typing import List, Tuple, Iterator


def bytes_to_bits(data: bytes) -> List[int]:
    bits = []
    for byte in data:
        # Konversi setiap byte ke 8 bits (MSB first)
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits


def bits_to_bytes(bits: List[int]) -> bytes:
    # Pastikan panjang bits kelipatan 8
    while len(bits) % 8 != 0:
        bits.append(0)

    result = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for j in range(8):
            if i + j < len(bits):
                byte |= bits[i + j] << (7 - j)
        result.append(byte)

    return bytes(result)


def get_lsb(sample: int, n: int = 1) -> int:
    mask = (1 << n) - 1  # Buat mask untuk n bits
    return sample & mask


def set_lsb(sample: int, bits: int, n: int = 1) -> int:
    mask = (1 << n) - 1  # Buat mask untuk n bits
    # Clear n LSB kemudian set dengan nilai baru
    return (sample & ~mask) | (bits & mask)


def create_payload(secret_data: bytes, filename: str = "") -> bytes:
    filename_bytes = filename.encode("utf-8")

    payload = bytearray()

    # Tambahkan panjang filename (4 bytes, little endian)
    payload.extend(struct.pack("<I", len(filename_bytes)))

    # Tambahkan filename
    payload.extend(filename_bytes)

    # Tambahkan panjang data (4 bytes, little endian)
    payload.extend(struct.pack("<I", len(secret_data)))

    # Tambahkan data
    payload.extend(secret_data)

    return bytes(payload)


def extract_payload(payload: bytes) -> Tuple[str, bytes]:
    if (
        len(payload) < 8
    ):  # Minimal 4 bytes untuk filename_length + 4 bytes untuk data_length
        raise ValueError(f"Payload terlalu pendek: {len(payload)} bytes")

    try:
        offset = 0

        # Baca panjang filename
        filename_length = struct.unpack("<I", payload[offset : offset + 4])[0]
        offset += 4

        # Validasi filename length
        if filename_length > 1000:  # Maksimal 1000 karakter untuk filename
            raise ValueError(f"Filename length tidak valid: {filename_length}")

        if offset + filename_length > len(payload):
            raise ValueError(
                f"Payload corrupt: filename length ({filename_length}) melebihi payload ({len(payload)})"
            )

        # Baca filename dengan error handling yang lebih baik
        try:
            filename_bytes = payload[offset : offset + filename_length]
            filename = filename_bytes.decode("utf-8", errors="replace")
            # Jika ada karakter yang tidak valid, beri nama default
            if "�" in filename:
                filename = "extracted_file"
        except Exception:
            filename = "extracted_file"

        offset += filename_length

        if offset + 4 > len(payload):
            raise ValueError("Payload corrupt: tidak ada data length")

        # Baca panjang data
        data_length = struct.unpack("<I", payload[offset : offset + 4])[0]
        offset += 4

        # Validasi data length
        if data_length > 100 * 1024 * 1024:  # Maksimal 100MB
            raise ValueError(f"Data length terlalu besar: {data_length}")

        if offset + data_length > len(payload):
            raise ValueError(
                f"Payload corrupt: data length ({data_length}) melebihi payload ({len(payload)})"
            )

        # Baca data
        data = payload[offset : offset + data_length]

        return filename, data

    except struct.error as e:
        raise ValueError(f"Error parsing payload structure: {e}")
    except Exception as e:
        raise ValueError(f"Error extracting payload: {e}")


def generate_random_positions(
    total_samples: int, required_positions: int, seed: str = None
) -> List[int]:
    if required_positions > total_samples:
        raise ValueError(
            f"Required positions ({required_positions}) melebihi total samples ({total_samples})"
        )

    # Set seed jika diberikan
    if seed is not None:
        random.seed(seed)

    # Generate posisi unik
    positions = random.sample(range(total_samples), required_positions)

    # Sort untuk memudahkan processing
    positions.sort()

    return positions


def calculate_capacity(total_samples: int, n_lsb: int) -> int:
    total_bits = total_samples * n_lsb
    return total_bits // 8


def int16_to_samples(data: bytes) -> List[int]:
    samples = []
    for i in range(0, len(data), 2):
        if i + 1 < len(data):
            # Little endian 16-bit signed integer
            sample = struct.unpack("<h", data[i : i + 2])[0]
            samples.append(sample)
    return samples


def samples_to_int16(samples: List[int]) -> bytes:
    data = bytearray()
    for sample in samples:
        # Clamp sample ke range 16-bit
        sample = max(-32768, min(32767, sample))
        data.extend(struct.pack("<h", sample))
    return bytes(data)


def test_utils():
    # Test bitstream conversion
    test_data = b"Hello!"
    bits = bytes_to_bits(test_data)
    recovered_data = bits_to_bytes(bits)
    print(
        f"Bitstream test: {test_data} -> {recovered_data} (Success: {test_data == recovered_data})"
    )

    # Test LSB operations
    sample = 0b11010110  # 214
    lsb_2 = get_lsb(sample, 2)
    print(f"LSB test: sample={bin(sample)}, 2-LSB={bin(lsb_2)} ({lsb_2})")

    new_sample = set_lsb(sample, 0b01, 2)
    print(f"Set LSB: {bin(sample)} -> {bin(new_sample)}")

    # Test payload
    secret = b"Secret message"
    filename = "secret.txt"
    payload = create_payload(secret, filename)
    recovered_filename, recovered_data = extract_payload(payload)
    print(
        f"Payload test: '{filename}', {secret} -> '{recovered_filename}', {recovered_data}"
    )
    print(f"Success: {filename == recovered_filename and secret == recovered_data}")

    # Test random positions
    positions = generate_random_positions(1000, 50, "test_seed")
    print(f"Random positions (first 10): {positions[:10]}")

    # Test capacity
    capacity = calculate_capacity(44100 * 10, 2)  # 10 detik audio, 2-LSB
    print(f"Capacity: {capacity} bytes ({capacity/1024:.2f} KB)")


if __name__ == "__main__":
    test_utils()
