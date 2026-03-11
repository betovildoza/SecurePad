"""
SecurePad - Crypto Engine
========================
AES-256-GCM + PBKDF2-SHA256 (200,000 iterations)
Secure memory wipe after key use.

File Format (.spd):
┌─────────────────────────────────────────┐
│  MAGIC     (8 bytes)  "SPAD\x01\x00\x00\x00"
│  VERSION   (2 bytes)  uint16 LE
│  KEY_ID    (16 bytes) random UUID bytes
│  SALT      (32 bytes) random salt
│  IV/NONCE  (12 bytes) AES-GCM nonce
│  TAG       (16 bytes) AES-GCM auth tag
│  CT_LEN    (8 bytes)  uint64 LE ciphertext length
│  CIPHERTEXT (N bytes) encrypted UTF-8 content
└─────────────────────────────────────────┘

Key File (.key):
┌─────────────────────────────────────────┐
│  MAGIC     (8 bytes)  "SPKY\x01\x00\x00\x00"
│  KEY_ID    (16 bytes) matches .spd KEY_ID
│  MASTER_KEY(32 bytes) raw AES-256 key (encrypted with recovery_key)
│  REC_SALT  (32 bytes) salt for recovery key derivation
│  REC_IV    (12 bytes) nonce for recovery key encryption
│  REC_TAG   (16 bytes) tag for recovery key encryption
│  REC_CT    (32 bytes) encrypted master key bytes
└─────────────────────────────────────────┘
"""

import os
import struct
import secrets
import ctypes
from typing import Optional, Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidTag

# ──────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────
MAGIC_SPD   = b"SPAD\x01\x00\x00\x00"   # .spd file magic
MAGIC_KEY   = b"SPKY\x01\x00\x00\x00"   # .key file magic
VERSION     = 1
KDF_ITERS   = 200_000
SALT_LEN    = 32
IV_LEN      = 12
TAG_LEN     = 16
KEY_LEN     = 32    # AES-256
KEY_ID_LEN  = 16


# ──────────────────────────────────────────────────────────
# Secure memory wipe
# ──────────────────────────────────────────────────────────
def secure_wipe(data: bytearray) -> None:
    """Overwrite a bytearray with zeros in-place, then del it."""
    if isinstance(data, bytearray):
        for i in range(len(data)):
            data[i] = 0
        # Second pass via ctypes to fight optimizer
        try:
            ctypes.memset(ctypes.addressof(
                (ctypes.c_char * len(data)).from_buffer(data)), 0, len(data))
        except Exception:
            pass


def secure_wipe_str(s: str) -> None:
    """Best-effort wipe of a Python str (limited by immutability)."""
    try:
        ba = bytearray(s.encode("utf-8"))
        secure_wipe(ba)
    except Exception:
        pass


# ──────────────────────────────────────────────────────────
# Key Derivation
# ──────────────────────────────────────────────────────────
def derive_key(password: str, salt: bytes) -> bytearray:
    """
    Derive AES-256 key from password using PBKDF2-HMAC-SHA256.
    Returns a bytearray so it can be securely wiped.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LEN,
        salt=salt,
        iterations=KDF_ITERS,
    )
    key_bytes = kdf.derive(password.encode("utf-8"))
    return bytearray(key_bytes)


# ──────────────────────────────────────────────────────────
# Encrypt
# ──────────────────────────────────────────────────────────
def encrypt_content(plaintext: str, password: str) -> Tuple[bytes, bytes]:
    """
    Encrypt plaintext with AES-256-GCM.

    Returns:
        (file_bytes, key_id)
        file_bytes: complete .spd binary ready to write to disk
        key_id:     16-byte identifier (for .key pairing)
    """
    salt    = secrets.token_bytes(SALT_LEN)
    nonce   = secrets.token_bytes(IV_LEN)
    key_id  = secrets.token_bytes(KEY_ID_LEN)

    derived = derive_key(password, salt)
    try:
        aesgcm = AESGCM(bytes(derived))
        ct_with_tag = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        # cryptography lib appends 16-byte tag at end
        ciphertext = ct_with_tag[:-TAG_LEN]
        tag        = ct_with_tag[-TAG_LEN:]
    finally:
        secure_wipe(derived)

    ct_len = len(ciphertext)

    header = (
        MAGIC_SPD
        + struct.pack("<H", VERSION)     # 2 bytes version
        + key_id                          # 16 bytes
        + salt                            # 32 bytes
        + nonce                           # 12 bytes
        + tag                             # 16 bytes
        + struct.pack("<Q", ct_len)       # 8 bytes
    )

    return header + ciphertext, key_id


# ──────────────────────────────────────────────────────────
# Decrypt
# ──────────────────────────────────────────────────────────
def decrypt_content(file_bytes: bytes, password: str) -> str:
    """
    Decrypt .spd file bytes.

    Raises:
        ValueError  – bad magic / unsupported version / truncated file
        SecurityError – authentication tag mismatch (wrong password or tampered file)
    """
    offset = 0

    # Magic
    magic = file_bytes[offset:offset+8]; offset += 8
    if magic != MAGIC_SPD:
        raise ValueError("Archivo no reconocido: magic inválido.")

    # Version
    version = struct.unpack("<H", file_bytes[offset:offset+2])[0]; offset += 2
    if version != VERSION:
        raise ValueError(f"Versión de archivo no soportada: {version}")

    # Key ID
    key_id = file_bytes[offset:offset+KEY_ID_LEN]; offset += KEY_ID_LEN  # noqa: F841

    # Salt
    salt  = file_bytes[offset:offset+SALT_LEN];  offset += SALT_LEN

    # Nonce
    nonce = file_bytes[offset:offset+IV_LEN];    offset += IV_LEN

    # Tag
    tag   = file_bytes[offset:offset+TAG_LEN];   offset += TAG_LEN

    # Ciphertext length
    ct_len = struct.unpack("<Q", file_bytes[offset:offset+8])[0]; offset += 8

    # Ciphertext
    ciphertext = file_bytes[offset:offset+ct_len]
    if len(ciphertext) != ct_len:
        raise ValueError("Archivo truncado o corrupto.")

    derived = derive_key(password, salt)
    try:
        aesgcm = AESGCM(bytes(derived))
        ct_with_tag = ciphertext + tag
        plaintext_bytes = aesgcm.decrypt(nonce, ct_with_tag, None)
    except InvalidTag:
        raise SecurityError(
            "Firma de Seguridad Inválida: contraseña incorrecta o archivo manipulado."
        )
    finally:
        secure_wipe(derived)

    return plaintext_bytes.decode("utf-8")


# ──────────────────────────────────────────────────────────
# Recovery Key (.key file)
# ──────────────────────────────────────────────────────────
def export_recovery_key(
    password: str,
    salt: bytes,
    key_id: bytes,
    recovery_password: str,
) -> bytes:
    """
    Build a .key file that stores the derived master key
    encrypted under recovery_password.
    """
    master_key = derive_key(password, salt)
    rec_salt   = secrets.token_bytes(SALT_LEN)
    rec_nonce  = secrets.token_bytes(IV_LEN)

    rec_derived = derive_key(recovery_password, rec_salt)
    try:
        aesgcm  = AESGCM(bytes(rec_derived))
        rec_ct_with_tag = aesgcm.encrypt(rec_nonce, bytes(master_key), None)
        rec_ct  = rec_ct_with_tag[:-TAG_LEN]
        rec_tag = rec_ct_with_tag[-TAG_LEN:]
    finally:
        secure_wipe(rec_derived)
        secure_wipe(master_key)

    return (
        MAGIC_KEY
        + key_id               # 16 bytes
        + salt                 # 32 bytes — original file salt
        + rec_salt             # 32 bytes
        + rec_nonce            # 12 bytes
        + rec_tag              # 16 bytes
        + rec_ct               # 32 bytes (KEY_LEN)
    )


def decrypt_with_recovery_key(
    file_bytes: bytes,
    key_file_bytes: bytes,
    recovery_password: str,
) -> Tuple[str, str]:
    """
    Decrypt .spd using a .key file + recovery password.
    Returns (plaintext, original_master_password_NOT_AVAILABLE).

    Note: The original text password is NOT stored; only the derived key is.
    Returns (plaintext, '<recuperado via .key>').
    """
    # Parse .key
    offset = 0
    magic = key_file_bytes[offset:offset+8]; offset += 8
    if magic != MAGIC_KEY:
        raise ValueError("Archivo .key inválido.")

    key_id_key = key_file_bytes[offset:offset+KEY_ID_LEN]; offset += KEY_ID_LEN  # noqa
    orig_salt  = key_file_bytes[offset:offset+SALT_LEN];   offset += SALT_LEN
    rec_salt   = key_file_bytes[offset:offset+SALT_LEN];   offset += SALT_LEN
    rec_nonce  = key_file_bytes[offset:offset+IV_LEN];     offset += IV_LEN
    rec_tag    = key_file_bytes[offset:offset+TAG_LEN];    offset += TAG_LEN
    rec_ct     = key_file_bytes[offset:offset+KEY_LEN];    offset += KEY_LEN

    rec_derived = derive_key(recovery_password, rec_salt)
    try:
        aesgcm = AESGCM(bytes(rec_derived))
        master_key_bytes = aesgcm.decrypt(rec_nonce, rec_ct + rec_tag, None)
    except InvalidTag:
        raise SecurityError(
            "Firma de Seguridad Inválida: contraseña de recuperación incorrecta o .key manipulado."
        )
    finally:
        secure_wipe(rec_derived)

    master_key = bytearray(master_key_bytes)

    # Parse .spd header
    spd_offset = 8 + 2 + KEY_ID_LEN  # magic + version + key_id
    salt  = file_bytes[spd_offset:spd_offset+SALT_LEN];  spd_offset += SALT_LEN
    nonce = file_bytes[spd_offset:spd_offset+IV_LEN];    spd_offset += IV_LEN
    tag   = file_bytes[spd_offset:spd_offset+TAG_LEN];   spd_offset += TAG_LEN
    ct_len = struct.unpack("<Q", file_bytes[spd_offset:spd_offset+8])[0]; spd_offset += 8
    ciphertext = file_bytes[spd_offset:spd_offset+ct_len]

    try:
        aesgcm = AESGCM(bytes(master_key))
        plaintext_bytes = aesgcm.decrypt(nonce, ciphertext + tag, None)
    except InvalidTag:
        raise SecurityError(
            "Firma de Seguridad Inválida: .key no corresponde a este archivo."
        )
    finally:
        secure_wipe(master_key)

    return plaintext_bytes.decode("utf-8"), "<recuperado vía .key>"


def get_key_id_from_file(file_bytes: bytes) -> bytes:
    """Extract the KEY_ID from a .spd file (no decryption needed)."""
    offset = 8 + 2  # magic + version
    return file_bytes[offset:offset+KEY_ID_LEN]


def get_salt_from_file(file_bytes: bytes) -> bytes:
    """Extract salt from a .spd file header."""
    offset = 8 + 2 + KEY_ID_LEN  # magic + version + key_id
    return file_bytes[offset:offset+SALT_LEN]


# ──────────────────────────────────────────────────────────
# Custom exception
# ──────────────────────────────────────────────────────────
class SecurityError(Exception):
    """Raised when AES-GCM authentication fails."""
    pass
