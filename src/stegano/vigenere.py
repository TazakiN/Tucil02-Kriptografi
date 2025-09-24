"""
Extended Vigenère Cipher dengan 256 karakter
Implementasi untuk enkripsi dan dekripsi data binary
"""


class ExtendedVigenereCipher:
    """
    Extended Vigenère Cipher yang mendukung semua 256 karakter ASCII
    """
    
    def __init__(self):
        # Menggunakan semua 256 karakter ASCII (0-255)
        pass
    
    def encrypt(self, data: bytes, key: str) -> bytes:
        """
        Enkripsi data menggunakan Extended Vigenère Cipher
        
        Args:
            data: Data binary yang akan dienkripsi
            key: Kunci enkripsi (string)
            
        Returns:
            bytes: Data terenkripsi
        """
        if not key:
            raise ValueError("Key tidak boleh kosong")
            
        key_bytes = key.encode('utf-8')
        encrypted = bytearray()
        
        for i, byte in enumerate(data):
            # Ambil karakter kunci dengan modulo untuk looping
            key_char = key_bytes[i % len(key_bytes)]
            
            # Enkripsi: (plaintext + key) mod 256
            encrypted_byte = (byte + key_char) % 256
            encrypted.append(encrypted_byte)
            
        return bytes(encrypted)
    
    def decrypt(self, encrypted_data: bytes, key: str) -> bytes:
        """
        Dekripsi data menggunakan Extended Vigenère Cipher
        
        Args:
            encrypted_data: Data terenkripsi
            key: Kunci dekripsi (string)
            
        Returns:
            bytes: Data terdekripsi
        """
        if not key:
            raise ValueError("Key tidak boleh kosong")
            
        key_bytes = key.encode('utf-8')
        decrypted = bytearray()
        
        for i, byte in enumerate(encrypted_data):
            # Ambil karakter kunci dengan modulo untuk looping
            key_char = key_bytes[i % len(key_bytes)]
            
            # Dekripsi: (ciphertext - key) mod 256
            decrypted_byte = (byte - key_char) % 256
            decrypted.append(decrypted_byte)
            
        return bytes(decrypted)


def test_vigenere():
    """
    Test function untuk Extended Vigenère Cipher
    """
    cipher = ExtendedVigenereCipher()
    
    # Test dengan string sederhana
    original = b"Hello, World! 123"
    key = "SECRET"
    
    encrypted = cipher.encrypt(original, key)
    decrypted = cipher.decrypt(encrypted, key)
    
    print(f"Original: {original}")
    print(f"Key: {key}")
    print(f"Encrypted: {encrypted}")
    print(f"Decrypted: {decrypted}")
    print(f"Success: {original == decrypted}")
    
    # Test dengan data binary
    binary_data = bytes(range(256))  # Semua byte 0-255
    encrypted_binary = cipher.encrypt(binary_data, key)
    decrypted_binary = cipher.decrypt(encrypted_binary, key)
    
    print(f"\nBinary test success: {binary_data == decrypted_binary}")


if __name__ == "__main__":
    test_vigenere()