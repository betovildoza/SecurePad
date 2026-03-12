<div align="center">
  <img src="src-tauri/icons/icon.png" alt="SecurePad Logo" width="128" />
  <h1>SecurePad v2</h1>
  <p><strong>Bóveda Criptográfica Ultraligera.</strong> <br> Protege tus textos y códigos con cifrado AES-256-GCM sin depender de la nube.</p>
</div>

---

## 🛡️ ¿Qué es SecurePad?

SecurePad es un editor de texto seguro y ultraligero que cifra todo su contenido en archivos locales inmodificables `.spd` utilizando el estándar criptográfico AES-256-GCM impulsado nativamente por **Rust**.
Diseñado originalmente en Flet (Python), la **Versión 2 ha sido completamente reescrita** con **Tauri v2 + React**, reduciendo drásticamente su latencia y peso residual, y permitiendo una ejecución nativa tanto en Windows como en Android usando el mismo Engine criptográfico.

### 🌟 Características Principales (v2)
* **Cifrado Neutro en Rust**: Utiliza primitivas puras en Rust (familia `RustCrypto` y AES GCM) sin dependencias nativas del sistema, lo cual previene vulnerabilidades a nivel S.O.
* **Recuperación Global Bip39**: Olvida el antiguo sistema arcaico de semillas por-archivo; SecurePad v2 guarda de forma segura tu semilla global y cifra dinámicamente cada bóveda bajo una derivación única y un Recovery Blob. Si olvidas tu Contraseña Maestra, tus 12 palabras lo recuperarán.
* **Editor Profesional (CodeMirror)**: Editor impulsado por CodeMirror, incluyendo números de línea, *Word Wrap* real asíncrono, y alto contraste, eliminando la latencia de teclas.
* **Modo Aislamiento y Bloqueo**: Se bloquea de forma autónoma tras uso continuo y mantiene la bóveda protegida bloqueando las lecturas directas del Disco.
* **100% Interop Flet (Retrocompatible)**: SecurePad v2 en Rust lee nativamente las bóvedas creadas con la versión vieja de Flet.

## 📦 Instalación

SecurePad no requiere dependencias web, cuentas ni conexión a internet para funcionar. 

### En Windows
Descarga el último instalador MSI o Setup desde la pestaña [Releases](#) de este repositorio o compílalo tú mismo:
1. Asegúrate de tener Rust y Node.js instalados.
2. Clona este repositorio y pule las dependencias: `npm install`.
3. Ejecuta `npm run tauri build` para obtener el ejecutable (.exe).

### En Android
Descarga la versión `.apk` desde Releases para tu celular:
1. Instala el APK.
2. Genera una Semilla la primera vez que abras la app. 
3. Pásate tus bóvedas `.spd` del portatil al celular y ábrelas en el vuelo.

## 🛠️ Stack Tecnológico
- **Core / Backend**: Rust 🦀 (Motor RustCrypto, Bindings JSON).
- **Frontend / GUI**: TypeScript + React ⚛️ (Framer Motion).
- **App Packager**: Tauri v2 🔌.

## 📜 Licencia
Este software es libre y se distribuye "Tal cual". Revisa la licencia para más detalles.

---
> *Tus pensamientos, tus llaves, tu bóveda.*

---

## 🛠 Entorno de Desarrollo

Necesitarás:
- **Node.js**: v18 o superior
- **Rust**: Versión más reciente de establo (`rustup`)
- **[Windows]** Visual Studio Build Tools con componentes C++
- **[Android]** Android Studio + SDK, NDK y variables de entorno configuradas (`ANDROID_HOME`, `NDK_HOME`).

### 1. Iniciar en Modo Desarrollo (Pruebas)

```bash
npm install
npm run tauri dev
```

> **NOTA IMPORTANTE:** NO uses el servidor de desarrollo en tu navegador (e.g., `http://localhost:1420` en Google Chrome). Tauri expone todas sus funciones del sistema de archivos mediante una inyección nativa (IPC) que *solo* existe en la ventana nativa que se abre automáticamente tras compilar el código en Rust.

---

## 📦 Cómo Compilar

Para generar los instaladores / ejecutables finales:

### 🖥 Para Windows
```bash
npm run tauri build
```
*(Encontrarás el `.exe` o el instalador `.msi` en `src-tauri/target/release/bundle/`)*

### 📱 Para Android
Asegúrate de tener las herramientas de Android configuradas según la guía oficial de Tauri v2.

1. Inicializa el proyecto Android si todavía no lo está:
   ```bash
   npm run tauri android init
   ```
2. Compila el APK:
   ```bash
   npm run tauri android build
   ```
*(Encontrarás tu `.apk` universal en `src-tauri/gen/android/app/build/outputs/apk/universal/release/`)*

---

*La rama de Flet se mantiene únicamente como archivo histórico. Todos los pull requests y desarrollos deben hacerse para esta pila de Tauri v2.*
