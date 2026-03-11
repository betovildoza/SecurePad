"""
SecurePad - Crypto Engine v2
=============================
Cambios v2:
  - Sistema de semilla mnem├│nica (12 palabras BIP-39) reemplaza archivos .key
  - La clave maestra se deriva de: password + salt (flujo normal)
  - Recuperaci├│n: seed_phrase -> master_key_bytes (sin contrase├▒a)
  - Archivo .spd ahora incluye recovery_blob: clave maestra cifrada bajo la seed
  - Sin dependencias de archivos externos para recuperaci├│n

Formato .spd v2:
ÔöîÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÉ
Ôöé  MAGIC       8B   "SPAD\x02\x00\x00\x00"
Ôöé  VERSION     2B   uint16 LE = 2
Ôöé  KEY_ID      16B  UUID aleatorio
Ôöé  SALT        32B  salt para PBKDF2 (password -> key)
Ôöé  NONCE       12B  AES-GCM nonce (ciphertext)
Ôöé  TAG         16B  AES-GCM auth tag (ciphertext)
Ôöé  REC_SALT    32B  salt para PBKDF2 (seed -> recovery_key)
Ôöé  REC_NONCE   12B  nonce para recovery_blob
Ôöé  REC_TAG     16B  tag para recovery_blob
Ôöé  CT_LEN       8B  uint64 LE longitud ciphertext
Ôöé  CIPHERTEXT   NB  texto cifrado
Ôöé  REC_BLOB    32B  master_key cifrada bajo recovery_key (derivada de seed)
ÔööÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÿ
"""

import os
import struct
import secrets
import ctypes
import hashlib
from typing import Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidTag
from mnemonic import Mnemonic

# ÔöÇÔöÇ Constantes ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
MAGIC_V2    = b"SPAD\x02\x00\x00\x00"
VERSION     = 2
KDF_ITERS   = 200_000
SALT_LEN    = 32
IV_LEN      = 12
TAG_LEN     = 16
KEY_LEN     = 32
KEY_ID_LEN  = 16

# Offsets en el header (para parseo directo)
OFF_MAGIC       = 0
OFF_VERSION     = 8
OFF_KEY_ID      = 10
OFF_SALT        = 26
OFF_NONCE       = 58
OFF_TAG         = 70
OFF_REC_SALT    = 86
OFF_REC_NONCE   = 118
OFF_REC_TAG     = 130
OFF_CT_LEN      = 146
OFF_CT          = 154
# REC_BLOB est├í al final: OFF_CT + ct_len

HEADER_FIXED_SIZE = OFF_CT  # 154 bytes de header fijo


# ÔöÇÔöÇ Limpieza de memoria ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
def secure_wipe(data: bytearray) -> None:
    """Sobreescribe un bytearray con ceros usando ctypes para evitar optimizaciones."""
    if not isinstance(data, bytearray) or len(data) == 0:
        return
    for i in range(len(data)):
        data[i] = 0
    try:
        ctypes.memset(
            ctypes.addressof((ctypes.c_char * len(data)).from_buffer(data)),
            0, len(data)
        )
    except Exception:
        pass


def secure_wipe_str(s: str) -> None:
    """Best-effort wipe de un str Python (limitado por inmutabilidad)."""
    try:
        ba = bytearray(s.encode("utf-8"))
        secure_wipe(ba)
    except Exception:
        pass


# ÔöÇÔöÇ Mnem├│nica (BIP-39, 12 palabras) ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
_mnemo = Mnemonic("english")


def generate_seed_phrase() -> str:
    """Genera 12 palabras BIP-39 aleatorias (128 bits de entrop├¡a)."""
    return _mnemo.generate(strength=128)


def validate_seed_phrase(phrase: str) -> bool:
    """Retorna True si la frase es BIP-39 v├ílida."""
    try:
        return _mnemo.check(phrase.strip().lower())
    except Exception:
        return False


def seed_phrase_to_key(phrase: str, salt: bytes) -> bytearray:
    """
    Deriva una clave AES-256 a partir de la semilla mnem├│nica.
    Usa PBKDF2 con la semilla como 'contrase├▒a' para que el salt del archivo
    sea independiente del salt de recuperaci├│n.
    """
    seed_bytes = phrase.strip().lower().encode("utf-8")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LEN,
        salt=salt,
        iterations=KDF_ITERS,
    )
    return bytearray(kdf.derive(seed_bytes))


def hash_seed_phrase(phrase: str) -> str:
    """
    Retorna SHA-256 hex del phrase normalizado.
    Se guarda en SharedPreferences para verificar que la seed ingresada es correcta
    sin exponer la seed en s├¡.
    """
    normalized = phrase.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# ÔöÇÔöÇ Derivaci├│n de clave desde contrase├▒a ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
def derive_key(password: str, salt: bytes) -> bytearray:
    """Deriva AES-256 key desde contrase├▒a usando PBKDF2-HMAC-SHA256."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LEN,
        salt=salt,
        iterations=KDF_ITERS,
    )
    return bytearray(kdf.derive(password.encode("utf-8")))


# ÔöÇÔöÇ Cifrado ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
def encrypt_content(plaintext: str, password: str, seed_phrase: str) -> Tuple[bytes, bytes]:
    """
    Cifra plaintext con AES-256-GCM.

    Args:
        plaintext:    Texto a cifrar (se encode a UTF-8)
        password:     Contrase├▒a maestra del usuario
        seed_phrase:  Semilla mnem├│nica (12 palabras) para recuperaci├│n

    Returns:
        (file_bytes, key_id)
        file_bytes: binario completo .spd listo para escribir a disco
        key_id:     identificador de 16 bytes del archivo
    """
    salt      = secrets.token_bytes(SALT_LEN)
    nonce     = secrets.token_bytes(IV_LEN)
    key_id    = secrets.token_bytes(KEY_ID_LEN)
    rec_salt  = secrets.token_bytes(SALT_LEN)
    rec_nonce = secrets.token_bytes(IV_LEN)

    # 1. Derivar clave desde contrase├▒a
    master_key = derive_key(password, salt)
    try:
        aesgcm = AESGCM(bytes(master_key))
        ct_with_tag = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        ciphertext  = ct_with_tag[:-TAG_LEN]
        tag         = ct_with_tag[-TAG_LEN:]
    finally:
        pass  # master_key se limpia al final

    # 2. Cifrar master_key bajo la clave derivada de la seed (recovery blob)
    rec_key = seed_phrase_to_key(seed_phrase, rec_salt)
    try:
        rec_aesgcm     = AESGCM(bytes(rec_key))
        rec_ct_with_tag = rec_aesgcm.encrypt(rec_nonce, bytes(master_key), None)
        rec_blob       = rec_ct_with_tag[:-TAG_LEN]
        rec_tag        = rec_ct_with_tag[-TAG_LEN:]
    finally:
        secure_wipe(rec_key)
        secure_wipe(master_key)

    ct_len = len(ciphertext)

    header = (
        MAGIC_V2
        + struct.pack("<H", VERSION)          # 2B
        + key_id                               # 16B
        + salt                                 # 32B
        + nonce                                # 12B
        + tag                                  # 16B
        + rec_salt                             # 32B
        + rec_nonce                            # 12B
        + rec_tag                              # 16B
        + struct.pack("<Q", ct_len)            # 8B
    )

    return header + ciphertext + rec_blob, key_id


# ÔöÇÔöÇ Descifrado con contrase├▒a ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
def decrypt_content(file_bytes: bytes, password: str) -> str:
    """
    Descifra un archivo .spd con la contrase├▒a maestra.

    Raises:
        ValueError:     Magic/version inv├ílido o archivo truncado.
        SecurityError:  Tag GCM inv├ílido (contrase├▒a incorrecta o archivo manipulado).
    """
    _check_magic(file_bytes)
    salt, nonce, tag, ciphertext = _parse_content_fields(file_bytes)

    master_key = derive_key(password, salt)
    try:
        aesgcm = AESGCM(bytes(master_key))
        plaintext_bytes = aesgcm.decrypt(nonce, ciphertext + tag, None)
    except InvalidTag:
        raise SecurityError(
            "Firma de Seguridad Inv├ílida: contrase├▒a incorrecta o archivo manipulado."
        )
    finally:
        secure_wipe(master_key)

    return plaintext_bytes.decode("utf-8")


# ÔöÇÔöÇ Recuperaci├│n con semilla ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
def decrypt_with_seed(file_bytes: bytes, seed_phrase: str) -> str:
    """
    Descifra un archivo .spd usando la semilla mnem├│nica de recuperaci├│n.

    Raises:
        ValueError:     Archivo inv├ílido.
        SecurityError:  Seed incorrecta o recovery blob manipulado.
    """
    if not validate_seed_phrase(seed_phrase):
        raise ValueError("La semilla no es v├ílida (verifica las 12 palabras).")

    _check_magic(file_bytes)
    _, _, _, ciphertext = _parse_content_fields(file_bytes)
    salt, nonce, tag    = _parse_content_nonce_tag(file_bytes)
    rec_salt, rec_nonce, rec_tag, rec_blob = _parse_recovery_fields(file_bytes)

    # 1. Recuperar master_key desde seed
    rec_key = seed_phrase_to_key(seed_phrase, rec_salt)
    try:
        rec_aesgcm = AESGCM(bytes(rec_key))
        master_key_bytes = rec_aesgcm.decrypt(rec_nonce, rec_blob + rec_tag, None)
    except InvalidTag:
        raise SecurityError(
            "Firma de Seguridad Inv├ílida: semilla incorrecta o archivo manipulado."
        )
    finally:
        secure_wipe(rec_key)

    master_key = bytearray(master_key_bytes)

    # 2. Descifrar contenido con master_key recuperada
    try:
        aesgcm = AESGCM(bytes(master_key))
        plaintext_bytes = aesgcm.decrypt(nonce, ciphertext + tag, None)
    except InvalidTag:
        raise SecurityError(
            "Firma de Seguridad Inv├ílida: recovery blob no corresponde a este archivo."
        )
    finally:
        secure_wipe(master_key)

    return plaintext_bytes.decode("utf-8")


# ÔöÇÔöÇ Re-cifrado (cambio de contrase├▒a) ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
def reencrypt_content(file_bytes: bytes, old_password: str,
                      new_password: str, seed_phrase: str) -> bytes:
    """
    Re-cifra el contenido con una nueva contrase├▒a manteniendo la misma seed.
    ├Ütil para cambio de contrase├▒a sin perder la recuperaci├│n.
    """
    plaintext = decrypt_content(file_bytes, old_password)
    new_bytes, _ = encrypt_content(plaintext, new_password, seed_phrase)
    secure_wipe_str(plaintext)
    return new_bytes


# ÔöÇÔöÇ Helpers de parseo ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
def _check_magic(file_bytes: bytes):
    if len(file_bytes) < HEADER_FIXED_SIZE:
        raise ValueError("Archivo demasiado peque├▒o o corrupto.")
    magic = file_bytes[OFF_MAGIC:OFF_MAGIC + 8]
    if magic != MAGIC_V2:
        raise ValueError(
            "Formato de archivo no reconocido. "
            "┬┐Fue creado con una versi├│n anterior de SecurePad?"
        )
    version = struct.unpack("<H", file_bytes[OFF_VERSION:OFF_VERSION + 2])[0]
    if version != VERSION:
        raise ValueError(f"Versi├│n de archivo no soportada: {version}")


def _parse_content_fields(file_bytes: bytes):
    salt       = file_bytes[OFF_SALT:OFF_SALT + SALT_LEN]
    nonce      = file_bytes[OFF_NONCE:OFF_NONCE + IV_LEN]
    tag        = file_bytes[OFF_TAG:OFF_TAG + TAG_LEN]
    ct_len     = struct.unpack("<Q", file_bytes[OFF_CT_LEN:OFF_CT_LEN + 8])[0]
    ciphertext = file_bytes[OFF_CT:OFF_CT + ct_len]
    if len(ciphertext) != ct_len:
        raise ValueError("Archivo truncado o corrupto.")
    return salt, nonce, tag, ciphertext


def _parse_content_nonce_tag(file_bytes: bytes):
    salt  = file_bytes[OFF_SALT:OFF_SALT + SALT_LEN]
    nonce = file_bytes[OFF_NONCE:OFF_NONCE + IV_LEN]
    tag   = file_bytes[OFF_TAG:OFF_TAG + TAG_LEN]
    return salt, nonce, tag


def _parse_recovery_fields(file_bytes: bytes):
    rec_salt  = file_bytes[OFF_REC_SALT:OFF_REC_SALT + SALT_LEN]
    rec_nonce = file_bytes[OFF_REC_NONCE:OFF_REC_NONCE + IV_LEN]
    rec_tag   = file_bytes[OFF_REC_TAG:OFF_REC_TAG + TAG_LEN]
    ct_len    = struct.unpack("<Q", file_bytes[OFF_CT_LEN:OFF_CT_LEN + 8])[0]
    rec_blob  = file_bytes[OFF_CT + ct_len: OFF_CT + ct_len + KEY_LEN]
    if len(rec_blob) != KEY_LEN:
        raise ValueError("Recovery blob ausente o truncado.")
    return rec_salt, rec_nonce, rec_tag, rec_blob


def get_key_id_from_file(file_bytes: bytes) -> bytes:
    return file_bytes[OFF_KEY_ID:OFF_KEY_ID + KEY_ID_LEN]


def get_salt_from_file(file_bytes: bytes) -> bytes:
    return file_bytes[OFF_SALT:OFF_SALT + SALT_LEN]


# ÔöÇÔöÇ Excepci├│n de seguridad ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
class SecurityError(Exception):
    """Lanzada cuando falla la autenticaci├│n AES-GCM."""
    pass
