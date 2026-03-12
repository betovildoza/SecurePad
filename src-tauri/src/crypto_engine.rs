use aes_gcm::{
    aead::{Aead, KeyInit},
    Aes256Gcm, Nonce,
};
use bip39::Mnemonic;
use hmac::Hmac;
use pbkdf2::pbkdf2;
use rand::RngCore;
use sha2::Sha256;
use uuid::Uuid;
use zeroize::{Zeroize, ZeroizeOnDrop};

const MAGIC_V2: &[u8; 8] = b"SPAD\x02\x00\x00\x00";
const VERSION: u16 = 2;
const KDF_ITERS: u32 = 200_000;
const SALT_LEN: usize = 32;
const IV_LEN: usize = 12;
const TAG_LEN: usize = 16;
const KEY_LEN: usize = 32;
const KEY_ID_LEN: usize = 16;

const OFF_MAGIC: usize = 0;
const OFF_VERSION: usize = 8;
const OFF_KEY_ID: usize = 10;
const OFF_SALT: usize = 26;
const OFF_NONCE: usize = 58;
const OFF_TAG: usize = 70;
const OFF_REC_SALT: usize = 86;
const OFF_REC_NONCE: usize = 118;
const OFF_REC_TAG: usize = 130;
const OFF_CT_LEN: usize = 146;
const OFF_CT: usize = 154;

const HEADER_FIXED_SIZE: usize = OFF_CT;

#[derive(thiserror::Error, Debug)]
pub enum SecurityError {
    #[error("Formato de archivo inválido o corrupto")]
    InvalidFormat,
    #[error("Versión no soportada: {0}")]
    UnsupportedVersion(u16),
    #[error("Firma de Seguridad Inválida: contraseña incorrecta o archivo manipulado")]
    InvalidTag,
    #[error("Semilla inválida")]
    InvalidSeed,
    #[error("Error interno de encriptación")]
    EncryptionError,
}

#[derive(Zeroize, ZeroizeOnDrop)]
struct MasterKey([u8; KEY_LEN]);

fn derive_key(password: &str, salt: &[u8]) -> MasterKey {
    let mut key = MasterKey([0u8; KEY_LEN]);
    let _ = pbkdf2::<Hmac<Sha256>>(password.as_bytes(), salt, KDF_ITERS, &mut key.0);
    key
}

fn seed_phrase_to_key(phrase: &str, salt: &[u8]) -> MasterKey {
    let phrase = phrase.trim().to_lowercase();
    let mut key = MasterKey([0u8; KEY_LEN]);
    let _ = pbkdf2::<Hmac<Sha256>>(phrase.as_bytes(), salt, KDF_ITERS, &mut key.0);
    key
}

pub fn generate_seed_phrase() -> String {
    let mut rng = rand::thread_rng();
    let mut entropy = [0u8; 16];
    rng.fill_bytes(&mut entropy);
    let mnemonic = Mnemonic::from_entropy(&entropy).unwrap();
    mnemonic.to_string()
}

pub fn validate_seed_phrase(phrase: &str) -> bool {
    Mnemonic::parse_in_normalized(
        bip39::Language::English,
        phrase.trim().to_lowercase().as_str(),
    )
    .is_ok()
}

pub fn encrypt_content(
    plaintext: &str,
    password: &str,
    seed_phrase: &str,
) -> Result<(Vec<u8>, Vec<u8>), SecurityError> {
    let mut rng = rand::thread_rng();

    let mut salt = [0u8; SALT_LEN];
    let mut nonce_bytes = [0u8; IV_LEN];
    let mut rec_salt = [0u8; SALT_LEN];
    let mut rec_nonce_bytes = [0u8; IV_LEN];

    rng.fill_bytes(&mut salt);
    rng.fill_bytes(&mut nonce_bytes);
    rng.fill_bytes(&mut rec_salt);
    rng.fill_bytes(&mut rec_nonce_bytes);

    let key_id = Uuid::new_v4();
    let key_id_bytes = key_id.into_bytes();

    let master_key = derive_key(password, &salt);

    let cipher = Aes256Gcm::new_from_slice(&master_key.0).unwrap();
    let ct_with_tag = cipher
        .encrypt(Nonce::from_slice(&nonce_bytes), plaintext.as_bytes())
        .map_err(|_| SecurityError::EncryptionError)?;

    let ciphertext = &ct_with_tag[..ct_with_tag.len() - TAG_LEN];
    let tag = &ct_with_tag[ct_with_tag.len() - TAG_LEN..];

    let rec_key = seed_phrase_to_key(seed_phrase, &rec_salt);
    let rec_cipher = Aes256Gcm::new_from_slice(&rec_key.0).unwrap();
    let rec_ct_with_tag = rec_cipher
        .encrypt(Nonce::from_slice(&rec_nonce_bytes), master_key.0.as_ref())
        .map_err(|_| SecurityError::EncryptionError)?;

    let rec_blob = &rec_ct_with_tag[..rec_ct_with_tag.len() - TAG_LEN];
    let rec_tag = &rec_ct_with_tag[rec_ct_with_tag.len() - TAG_LEN..];

    let ct_len = ciphertext.len() as u64;

    let mut out = Vec::with_capacity(HEADER_FIXED_SIZE + ciphertext.len() + KEY_LEN);
    out.extend_from_slice(MAGIC_V2);
    out.extend_from_slice(&VERSION.to_le_bytes());
    out.extend_from_slice(&key_id_bytes);
    out.extend_from_slice(&salt);
    out.extend_from_slice(&nonce_bytes);
    out.extend_from_slice(tag);
    out.extend_from_slice(&rec_salt);
    out.extend_from_slice(&rec_nonce_bytes);
    out.extend_from_slice(rec_tag);
    out.extend_from_slice(&ct_len.to_le_bytes());
    out.extend_from_slice(ciphertext);
    out.extend_from_slice(rec_blob);

    Ok((out, key_id_bytes.to_vec()))
}

fn check_magic(file_bytes: &[u8]) -> Result<(), SecurityError> {
    if file_bytes.len() < HEADER_FIXED_SIZE {
        return Err(SecurityError::InvalidFormat);
    }
    if &file_bytes[OFF_MAGIC..OFF_MAGIC + 8] != MAGIC_V2 {
        return Err(SecurityError::InvalidFormat);
    }
    let version = u16::from_le_bytes(file_bytes[OFF_VERSION..OFF_VERSION + 2].try_into().unwrap());
    if version != VERSION {
        return Err(SecurityError::UnsupportedVersion(version));
    }
    Ok(())
}

pub fn decrypt_content(file_bytes: &[u8], password: &str) -> Result<String, SecurityError> {
    check_magic(file_bytes)?;

    let ct_len =
        u64::from_le_bytes(file_bytes[OFF_CT_LEN..OFF_CT_LEN + 8].try_into().unwrap()) as usize;
    if file_bytes.len() < OFF_CT + ct_len {
        return Err(SecurityError::InvalidFormat);
    }

    let salt = &file_bytes[OFF_SALT..OFF_SALT + SALT_LEN];
    let nonce_bytes = &file_bytes[OFF_NONCE..OFF_NONCE + IV_LEN];
    let tag = &file_bytes[OFF_TAG..OFF_TAG + TAG_LEN];
    let ciphertext = &file_bytes[OFF_CT..OFF_CT + ct_len];

    let master_key = derive_key(password, salt);
    let cipher = Aes256Gcm::new_from_slice(&master_key.0).unwrap();

    let mut payload = Vec::with_capacity(ciphertext.len() + tag.len());
    payload.extend_from_slice(ciphertext);
    payload.extend_from_slice(tag);

    let plaintext_bytes = cipher
        .decrypt(Nonce::from_slice(nonce_bytes), payload.as_ref())
        .map_err(|_| SecurityError::InvalidTag)?;

    String::from_utf8(plaintext_bytes).map_err(|_| SecurityError::InvalidFormat)
}

pub fn decrypt_with_seed(file_bytes: &[u8], seed_phrase: &str) -> Result<String, SecurityError> {
    if !validate_seed_phrase(seed_phrase) {
        return Err(SecurityError::InvalidSeed);
    }
    check_magic(file_bytes)?;

    let ct_len =
        u64::from_le_bytes(file_bytes[OFF_CT_LEN..OFF_CT_LEN + 8].try_into().unwrap()) as usize;
    if file_bytes.len() < OFF_CT + ct_len + KEY_LEN {
        return Err(SecurityError::InvalidFormat);
    }

    let nonce_bytes = &file_bytes[OFF_NONCE..OFF_NONCE + IV_LEN];
    let tag = &file_bytes[OFF_TAG..OFF_TAG + TAG_LEN];
    let ciphertext = &file_bytes[OFF_CT..OFF_CT + ct_len];

    let rec_salt = &file_bytes[OFF_REC_SALT..OFF_REC_SALT + SALT_LEN];
    let rec_nonce_bytes = &file_bytes[OFF_REC_NONCE..OFF_REC_NONCE + IV_LEN];
    let rec_tag = &file_bytes[OFF_REC_TAG..OFF_REC_TAG + TAG_LEN];
    let rec_blob = &file_bytes[OFF_CT + ct_len..OFF_CT + ct_len + KEY_LEN];

    let rec_key = seed_phrase_to_key(seed_phrase, rec_salt);
    let rec_cipher = Aes256Gcm::new_from_slice(&rec_key.0).unwrap();

    let mut payload = Vec::with_capacity(rec_blob.len() + rec_tag.len());
    payload.extend_from_slice(rec_blob);
    payload.extend_from_slice(rec_tag);

    let master_key_bytes = rec_cipher
        .decrypt(Nonce::from_slice(rec_nonce_bytes), payload.as_ref())
        .map_err(|_| SecurityError::InvalidTag)?;

    let master_key = MasterKey(master_key_bytes.try_into().unwrap());
    let cipher = Aes256Gcm::new_from_slice(&master_key.0).unwrap();

    let mut ct_payload = Vec::with_capacity(ciphertext.len() + tag.len());
    ct_payload.extend_from_slice(ciphertext);
    ct_payload.extend_from_slice(tag);

    let plaintext_bytes = cipher
        .decrypt(Nonce::from_slice(nonce_bytes), ct_payload.as_ref())
        .map_err(|_| SecurityError::InvalidTag)?;

    String::from_utf8(plaintext_bytes).map_err(|_| SecurityError::InvalidFormat)
}

pub fn get_key_id_from_file(file_bytes: &[u8]) -> Result<Vec<u8>, SecurityError> {
    if file_bytes.len() < HEADER_FIXED_SIZE {
        return Err(SecurityError::InvalidFormat);
    }
    Ok(file_bytes[OFF_KEY_ID..OFF_KEY_ID + KEY_ID_LEN].to_vec())
}

pub fn get_salt_from_file(file_bytes: &[u8]) -> Result<Vec<u8>, SecurityError> {
    if file_bytes.len() < HEADER_FIXED_SIZE {
        return Err(SecurityError::InvalidFormat);
    }
    Ok(file_bytes[OFF_SALT..OFF_SALT + SALT_LEN].to_vec())
}

pub fn hash_seed_phrase(phrase: &str) -> String {
    use sha2::Digest;
    let mut hasher = Sha256::new();
    hasher.update(phrase.trim().to_lowercase().as_bytes());
    let result = hasher.finalize();
    format!("{:x}", result)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_roundtrip_ascii() {
        let text = "Hello, SecurePad! My password is: Hunter2";
        let seed = generate_seed_phrase();
        let (fb, _key_id) = encrypt_content(text, "strongpassword123", &seed).unwrap();
        let decrypted = decrypt_content(&fb, "strongpassword123").unwrap();
        assert_eq!(decrypted, text);
    }

    #[test]
    fn test_roundtrip_unicode() {
        let text = "Contraseña: 🔑 áéíóú ñ 漢字";
        let seed = generate_seed_phrase();
        let (fb, _) = encrypt_content(text, "pass", &seed).unwrap();
        let decrypted = decrypt_content(&fb, "pass").unwrap();
        assert_eq!(decrypted, text);
    }

    #[test]
    fn test_roundtrip_empty_string() {
        let seed = generate_seed_phrase();
        let (fb, _) = encrypt_content("", "pass", &seed).unwrap();
        let decrypted = decrypt_content(&fb, "pass").unwrap();
        assert_eq!(decrypted, "");
    }

    #[test]
    fn test_wrong_password_raises_security_error() {
        let seed = generate_seed_phrase();
        let (fb, _) = encrypt_content("secret", "correct_password", &seed).unwrap();
        let err = decrypt_content(&fb, "wrong_password").unwrap_err();
        match err {
            SecurityError::InvalidTag => (),
            _ => panic!("Expected InvalidTag"),
        }
    }

    #[test]
    fn test_tampered_ciphertext_raises_security_error() {
        let text = "Important credentials here";
        let seed = generate_seed_phrase();
        let (mut fb, _) = encrypt_content(text, "mypassword", &seed).unwrap();

        let last_idx = fb.len() - KEY_LEN - 1;
        fb[last_idx] ^= 0xFF; // Tamper ciphertext

        let err = decrypt_content(&fb, "mypassword").unwrap_err();
        match err {
            SecurityError::InvalidTag => (),
            _ => panic!("Expected InvalidTag"),
        }
    }

    #[test]
    fn test_tampered_tag_raises_security_error() {
        let seed = generate_seed_phrase();
        let (mut fb, _) = encrypt_content("data", "pass", &seed).unwrap();
        fb[OFF_TAG] ^= 0xAB;

        let err = decrypt_content(&fb, "pass").unwrap_err();
        match err {
            SecurityError::InvalidTag => (),
            _ => panic!("Expected InvalidTag"),
        }
    }

    #[test]
    fn test_magic_header() {
        let seed = generate_seed_phrase();
        let (fb, _) = encrypt_content("test", "pass", &seed).unwrap();
        assert_eq!(&fb[..8], MAGIC_V2);
    }

    #[test]
    fn test_key_id_extraction() {
        let seed = generate_seed_phrase();
        let (fb, key_id) = encrypt_content("test", "pass", &seed).unwrap();
        let extracted = get_key_id_from_file(&fb).unwrap();
        assert_eq!(extracted, key_id);
    }

    #[test]
    fn test_salt_extraction() {
        let seed = generate_seed_phrase();
        let (fb, _) = encrypt_content("test", "pass", &seed).unwrap();
        let salt = get_salt_from_file(&fb).unwrap();
        assert_eq!(salt.len(), SALT_LEN);
    }

    #[test]
    fn test_two_encryptions_produce_different_bytes() {
        let text = "same content";
        let seed = generate_seed_phrase();
        let (fb1, _) = encrypt_content(text, "same_password", &seed).unwrap();
        let (fb2, _) = encrypt_content(text, "same_password", &seed).unwrap();
        assert_ne!(fb1, fb2);
    }

    #[test]
    fn test_recovery_seed_roundtrip() {
        let text = "Super secret note";
        let pwd = "masterpassword";
        let seed = generate_seed_phrase();

        let (fb, _) = encrypt_content(text, pwd, &seed).unwrap();

        let recovered = decrypt_with_seed(&fb, &seed).unwrap();
        assert_eq!(recovered, text);
    }

    #[test]
    fn test_recovery_wrong_seed() {
        let text = "secret";
        let pwd = "master";
        let seed1 = generate_seed_phrase();
        let seed2 = generate_seed_phrase();

        let (fb, _) = encrypt_content(text, pwd, &seed1).unwrap();

        let err = decrypt_with_seed(&fb, &seed2).unwrap_err();
        match err {
            SecurityError::InvalidTag => (),
            _ => panic!("Expected InvalidTag"),
        }
    }

    #[test]
    fn test_invalid_seed_format() {
        let fb = vec![0u8; 200];
        let err = decrypt_with_seed(&fb, "not a twelve word phrase random incorrect").unwrap_err();
        match err {
            SecurityError::InvalidSeed => (),
            _ => panic!("Expected InvalidSeed"),
        }
    }

    #[test]
    fn test_invalid_magic() {
        let fb = vec![0u8; 100];
        let err = decrypt_content(&fb, "pass").unwrap_err();
        match err {
            SecurityError::InvalidFormat => (),
            _ => panic!("Expected InvalidFormat"),
        }
    }
}
