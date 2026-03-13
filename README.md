
<div align="center">
  <img src="https://raw.githubusercontent.com/betovildoza/SecurePad/main/src-tauri/icons/icon.png" alt="SecurePad Logo" width="128" />
  <h1>SecurePad v2</h1>

  [![SecurePad Release](https://github.com/betovildoza/SecurePad/actions/workflows/release.yml/badge.svg)](https://github.com/betovildoza/SecurePad/actions/workflows/release.yml)
  [![GitHub license](https://img.shields.io/github/license/betovildoza/SecurePad?style=flat-square)](https://github.com/betovildoza/SecurePad/blob/main/LICENSE)
  [![GitHub release](https://img.shields.io/github/v/release/betovildoza/SecurePad?style=flat-square&color=green&logo=github)](https://github.com/betovildoza/SecurePad/releases/latest)
  [![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/betovildoza/SecurePad/release.yml?branch=main&style=flat-square&logo=github&label=Release%20CI)](https://github.com/betovildoza/SecurePad/actions/workflows/release.yml)
  [![GitHub stars](https://img.shields.io/github/stars/betovildoza/SecurePad?style=flat-square&color=yellow&logo=github)](https://github.com/betovildoza/SecurePad/stargazers)
  [![GitHub forks](https://img.shields.io/github/forks/betovildoza/SecurePad?style=flat-square&logo=github)](https://github.com/betovildoza/SecurePad/network/members)

  [![Rust](https://img.shields.io/badge/Rust-000000?style=flat-square&logo=rust&logoColor=white)](https://www.rust-lang.org/)
  [![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
  [![React](https://img.shields.io/badge/React-20232A?style=flat-square&logo=react&logoColor=61DAFB)](https://react.dev/)
  [![Tauri](https://img.shields.io/badge/Tauri-24C8D9?style=flat-square&logo=tauri&logoColor=white)](https://tauri.app/)
  [![Vite](https://img.shields.io/badge/Vite-646CFF?style=flat-square&logo=vite&logoColor=white)](https://vitejs.dev/)

  ![AES-256-GCM](https://img.shields.io/badge/AES--256--GCM-encrypted-blue?style=flat-square&logo=lock&logoColor=white)
  ![Offline-first](https://img.shields.io/badge/Offline--first-2ecc71?style=flat-square&logo=lock&logoColor=white)
  ![No Cloud](https://img.shields.io/badge/No%20Cloud-000000?style=flat-square&logo=ghost&logoColor=white)

  ![Windows](https://img.shields.io/badge/Windows-0078D6?style=flat-square&logo=windows&logoColor=white)
  ![Android](https://img.shields.io/badge/Android-3DDC84?style=flat-square&logo=android&logoColor=white)

</div>

**Minimal encrypted notes.**  
Protege tus textos y códigos con cifrado AES-256-GCM sin depender de la nube. Sin cuentas. Solo tus llaves.


# SecurePad v2
  <p>
    <strong>Minimal encrypted notes.</strong><br>
    Protege tus textos y códigos con cifrado AES-256-GCM.<br>
    Sin nube. Sin cuentas. Solo tus llaves.
  </p>
</div>

## Why SecurePad?

La mayoría de las herramientas para guardar información sensible dependen de la nube, cuentas online o servicios de terceros.
SecurePad nace con una idea mucho más simple: **tus datos deberían pertenecer solo a vos.**

SecurePad funciona completamente offline. No requiere cuentas, servidores ni sincronización obligatoria.
Cada nota se guarda como un archivo `.spd` cifrado con **AES-256-GCM**, que solo puede abrirse con tu contraseña o tu semilla de recuperación.

Esto significa que:

* tus datos **no pasan por servidores externos**
* **no hay cuentas que puedan ser hackeadas**
* puedes mover tus archivos libremente entre dispositivos
* tus notas siguen siendo **archivos portables y controlados por vos**

SecurePad no intenta ser un gestor de contraseñas complejo ni una plataforma de productividad.
Es simplemente **un bloc de notas cifrado, rápido y portátil**.

A veces, lo más seguro es también lo más simple.

---

## 📥 Descargar

Puedes descargar la última versión desde:

➡️ **[Releases](../../releases/latest)**

Archivos disponibles:

**Windows**

* SecurePad_windows_x64.msi
* SecurePad_windows_portable.exe

**Android**

* SecurePad_android.apk

---

## 🛡️ ¿Qué es SecurePad?

SecurePad es un editor de texto seguro y ultraligero que cifra todo su contenido en archivos locales `.spd` utilizando **AES-256-GCM**.

No depende de servidores, cuentas ni servicios en la nube.

Diseñado originalmente en **Flet (Python)**, la **Versión 2 fue completamente reescrita** usando:

* **Rust** para el motor criptográfico
* **Tauri v2** para empaquetado nativo
* **React + TypeScript** para la interfaz

Esto reduce significativamente el consumo de memoria y mejora la velocidad del editor.

---

## ✨ Características

| Feature               | Descripción                             |
| --------------------- | --------------------------------------- |
| 🔐 AES-256-GCM        | Cifrado autenticado seguro              |
| 🦀 Motor en Rust      | Criptografía nativa usando RustCrypto   |
| 📝 Editor CodeMirror  | Editor rápido con resaltado y Word Wrap |
| 🔑 Recuperación BIP39 | Recupera tu bóveda con 12 palabras      |
| 🔒 Auto-Lock          | Bloqueo automático tras inactividad     |
| 🔁 Compatibilidad     | Lee bóvedas creadas con la versión Flet |

---

## 🖼️ Screenshots

### Pantalla de Inicio, Bloqueo y Configuracion

<div display:"flex"> 
<img src="img/screenshot-inicio.png" width="30%">
<img src="img/screenshot-bloqueo.png" width="30%">
<img src="img/screenshot-settings.png" width="30%">
</div>
---

## 🛠️ Stack Tecnológico

**Core / Backend**

* Rust 🦀
* RustCrypto

**Frontend**

* TypeScript
* React
* CodeMirror

**App Framework**

* Tauri v2

---

## 🧑‍💻 Desarrollo

Requisitos:

* Node.js v18 o superior
* Rust (stable vía `rustup`)
* Visual Studio Build Tools con C++ (Windows)
* Android Studio + SDK / NDK

---

### Ejecutar en modo desarrollo

```
npm install
npm run tauri dev
```

⚠️ No abras el proyecto en `localhost` dentro de tu navegador.

Tauri expone APIs del sistema **solo dentro de la ventana nativa**.

---

## 📦 Compilar

### Windows

```
npm run tauri build
```

Output:

```
src-tauri/target/release/bundle/
```

---

### Android

Inicializar entorno Android:

```
npm run tauri android init
```

Compilar APK:

```
npm run tauri android build
```

Output:

```
src-tauri/gen/android/app/build/outputs/apk/universal/release/
```

---

## 📜 Licencia

Este software se distribuye **tal cual** bajo licencia libre.

Consulta el archivo `LICENSE` para más detalles.

---

> **Tus pensamientos. Tus llaves. Tu bóveda.**
