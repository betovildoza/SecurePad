<div align="center">
  <img src="img/logo-securepad-azul3-693.png" width="128" />
  <h1>SecurePad v2.0</h1>
  <p><strong>Cifrado local seguro con AES-256-GCM y una interfaz rápida impulsada por React + Rust (Tauri).</strong></p>
</div>

---

## 🔒 Sobre el Proyecto

**SecurePad** es un editor de texto diseñado para almacenar notas de forma 100% segura y privada en archivos locales `.spd` (SecurePad vault format). Esta herramienta fue reescrita en **Tauri v2 + React + Rust** para superar los problemas originales de renderizado de `Flet/Python` y ofrecer una experiencia nativa, segura y multiplataforma, logrando un resaltado de sintaxis eficiente y soporte para Android/Windows nativo real.

### Arquitectura de Seguridad
- **Algoritmo de cifrado:** AES-256-GCM
- **KDF (Derivación de llaves):** PBKDF2 (HMAC-SHA256) con 200,000 iteraciones y salt dinámico (32 bytes).
- **Semilla de Recuperación:** 12 palabras (estándar BIP39) generadas localmente. Útil si olvidas la *Master Password*.
- **Cero Logs:** Todo el cifrado / descifrado se ejecuta en la máquina local usando el binario de Rust y la memoria volátil se limpia de manera segura al instante (uso del crate `zeroize`).

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
