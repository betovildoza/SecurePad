"""
Tests for SecurePad crypto_engine.py
Run: python -m pytest tests/ -v
"""
import pytest
from securepad.crypto_engine import (
    encrypt_content,
    decrypt_content,
    export_recovery_key,
    decrypt_with_recovery_key,
    get_key_id_from_file,
    get_salt_from_file,
    secure_wipe,
    SecurityError,
    MAGIC_SPD,
    MAGIC_KEY,
    SALT_LEN,
    KEY_ID_LEN,
)


# ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
# Encrypt / Decrypt round-trip
# ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
def test_roundtrip_ascii():
    text = "Hello, SecurePad! My password is: Hunter2"
    fb, _ = encrypt_content(text, "strongpassword123")
    assert decrypt_content(fb, "strongpassword123") == text


def test_roundtrip_unicode():
    text = "Contrase├▒a: ­ƒöÉ ├í├®├¡├│├║ ├▒ µ╝óÕ¡ù"
    fb, _ = encrypt_content(text, "pass")
    assert decrypt_content(fb, "pass") == text


def test_roundtrip_empty_string():
    fb, _ = encrypt_content("", "pass")
    assert decrypt_content(fb, "pass") == ""


def test_wrong_password_raises_security_error():
    fb, _ = encrypt_content("secret", "correct_password")
    with pytest.raises(SecurityError) as exc_info:
        decrypt_content(fb, "wrong_password")
    assert "Firma de Seguridad Inv├ílida" in str(exc_info.value)


def test_tampered_ciphertext_raises_security_error():
    text = "Important credentials here"
    fb, _ = encrypt_content(text, "mypassword")
    # Flip last byte of ciphertext
    fb_tampered = bytearray(fb)
    fb_tampered[-1] ^= 0xFF
    with pytest.raises(SecurityError):
        decrypt_content(bytes(fb_tampered), "mypassword")


def test_tampered_tag_raises_security_error():
    fb, _ = encrypt_content("data", "pass")
    fb_tampered = bytearray(fb)
    # Tag starts at offset 8+2+16+32+12 = 70
    fb_tampered[70] ^= 0xAB
    with pytest.raises(SecurityError):
        decrypt_content(bytes(fb_tampered), "pass")


# ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
# File format / header
# ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
def test_magic_header():
    fb, _ = encrypt_content("test", "pass")
    assert fb[:8] == MAGIC_SPD


def test_key_id_extraction():
    fb, key_id = encrypt_content("test", "pass")
    extracted = get_key_id_from_file(fb)
    assert extracted == key_id
    assert len(extracted) == KEY_ID_LEN


def test_salt_extraction():
    fb, _ = encrypt_content("test", "pass")
    salt = get_salt_from_file(fb)
    assert len(salt) == SALT_LEN


def test_two_encryptions_produce_different_bytes():
    text = "same content"
    fb1, _ = encrypt_content(text, "same_password")
    fb2, _ = encrypt_content(text, "same_password")
    assert fb1 != fb2  # different nonce/salt each time


# ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
# Recovery key
# ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
def test_recovery_key_roundtrip():
    text  = "Super secret note"
    pwd   = "masterpassword"
    rec   = "recoverypassword"

    fb, key_id = encrypt_content(text, pwd)
    salt       = get_salt_from_file(fb)

    key_bytes  = export_recovery_key(pwd, salt, key_id, rec)
    assert key_bytes[:8] == MAGIC_KEY

    recovered, _ = decrypt_with_recovery_key(fb, key_bytes, rec)
    assert recovered == text


def test_recovery_wrong_recovery_password():
    fb, key_id = encrypt_content("secret", "master")
    salt       = get_salt_from_file(fb)
    key_bytes  = export_recovery_key("master", salt, key_id, "recpwd")

    with pytest.raises(SecurityError) as exc_info:
        decrypt_with_recovery_key(fb, key_bytes, "wrong_recpwd")
    assert "Firma de Seguridad Inv├ílida" in str(exc_info.value)


def test_recovery_wrong_master_password_for_export():
    fb, key_id = encrypt_content("secret", "correct")
    salt       = get_salt_from_file(fb)
    # Export with wrong master password ÔåÆ key will be wrong derivation
    key_bytes  = export_recovery_key("WRONG", salt, key_id, "recpwd")

    with pytest.raises(SecurityError):
        decrypt_with_recovery_key(fb, key_bytes, "recpwd")


def test_invalid_key_file_magic():
    fb, key_id = encrypt_content("secret", "pass")
    salt       = get_salt_from_file(fb)
    key_bytes  = export_recovery_key("pass", salt, key_id, "rec")

    broken = b"\x00" * 8 + key_bytes[8:]
    with pytest.raises(ValueError, match="inv├ílido"):
        decrypt_with_recovery_key(fb, broken, "rec")


# ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
# Secure wipe
# ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
def test_secure_wipe_zeros_bytearray():
    data = bytearray(b"sensitive data here")
    secure_wipe(data)
    assert all(b == 0 for b in data)


def test_invalid_magic():
    with pytest.raises(ValueError, match="magic"):
        decrypt_content(b"\x00" * 100, "pass")
