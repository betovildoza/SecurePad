pub mod crypto_engine;

// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
#[tauri::command]
fn generate_seed() -> String {
    crypto_engine::generate_seed_phrase()
}

#[tauri::command]
fn validate_seed(phrase: &str) -> bool {
    crypto_engine::validate_seed_phrase(phrase)
}

#[tauri::command]
fn hash_seed(phrase: &str) -> String {
    crypto_engine::hash_seed_phrase(phrase)
}

#[tauri::command]
fn encrypt_note(plaintext: &str, password: &str, seed_phrase: &str) -> Result<Vec<u8>, String> {
    let (encrypted_bytes, _) = crypto_engine::encrypt_content(plaintext, password, seed_phrase)
        .map_err(|e| e.to_string())?;
    Ok(encrypted_bytes)
}

#[tauri::command]
fn decrypt_note(file_bytes: Vec<u8>, password: &str) -> Result<String, String> {
    crypto_engine::decrypt_content(&file_bytes, password).map_err(|e| e.to_string())
}

#[tauri::command]
fn decrypt_seed(file_bytes: Vec<u8>, seed_phrase: &str) -> Result<String, String> {
    crypto_engine::decrypt_with_seed(&file_bytes, seed_phrase).map_err(|e| e.to_string())
}
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_store::Builder::new().build())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            generate_seed,
            validate_seed,
            hash_seed,
            encrypt_note,
            decrypt_note,
            decrypt_seed
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
