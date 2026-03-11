<div align="center">

![SecurePad](img/logo-securepad-azul3-250.png)

# 🔐 SecurePad

> [!WARNING]
> **PROYECTO ARCHIVADO (RAMA FLET)**
> Este branch contiene la implementación original en Python + Flet. 
> Se archiva esta rama debido a las limitaciones del framework Flet para manipular y resaltar texto (RichText) durante las búsquedas y edición avanzada. 
> El desarrollo activo de SecurePad continúa en la rama principal (`main`) usando **Tauri v2 + React**.

**Editor de texto cifrado. Sin servidores. Sin compromisos.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flet](https://img.shields.io/badge/Flet-0.21%2B-00B4D8?style=for-the-badge&logo=flutter&logoColor=white)](https://flet.dev/)
[![Cryptography](https://img.shields.io/badge/cryptography.io-42%2B-FF6B35?style=for-the-badge&logo=letsencrypt&logoColor=white)](https://cryptography.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

[![AES-256-GCM](https://img.shields.io/badge/Cifrado-AES--256--GCM-red?style=flat-square&logo=shieldsdotio&logoColor=white)](https://en.wikipedia.org/wiki/Galois/Counter_Mode)
[![PBKDF2](https://img.shields.io/badge/KDF-PBKDF2--SHA256%20·%20200K%20iter-orange?style=flat-square)](https://en.wikipedia.org/wiki/PBKDF2)
[![Tests](https://img.shields.io/badge/Tests-16%20passed-brightgreen?style=flat-square&logo=pytest&logoColor=white)](tests/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Android-blue?style=flat-square&logo=windows&logoColor=white)](BUILD_GUIDE.md)
[![Zero Network](https://img.shields.io/badge/Red-Cero%20conexiones-black?style=flat-square&logo=tor-browser&logoColor=white)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-blueviolet?style=flat-square)](CONTRIBUTING.md)

<br/>

> SecurePad es un bloc de notas minimalista para guardar credenciales con cifrado de grado militar.  
> Todo vive en archivos locales `.spd` que tú controlas. Ningún byte sale de tu dispositivo.

<br/>

![SecurePad Dark Mode](https://via.placeholder.com/800x480/111111/4A9EFF?text=SecurePad+—+Dark+Mode+Preview)

</div>

---

## ¿Por qué SecurePad?

La mayoría de gestores de contraseñas dependen de servidores en la nube, suscripciones o cuentas de usuario. SecurePad toma el camino opuesto:

| Característica | SecurePad | Gestores cloud |
|---|---|---|
| Servidores externos | ❌ Ninguno | ✅ Siempre |
| Cuenta de usuario | ❌ No requerida | ✅ Obligatoria |
| Cifrado end-to-end real | ✅ AES-256-GCM local | ⚠️ Depende del proveedor |
| Portabilidad del archivo | ✅ Copia el .spd donde quieras | ❌ Atado al servicio |
| Funciona sin internet | ✅ Siempre | ❌ Algunas funciones no |
| Open source auditable | ✅ Código visible | ⚠️ Varía |

---

## Características

### 🔒 Seguridad

- **AES-256-GCM** — Cifrado autenticado: confidencialidad + integridad en una operación
- **PBKDF2-HMAC-SHA256** con 200,000 iteraciones — resistente a ataques de fuerza bruta con GPU
- **Salt único por archivo** (32 bytes, CSPRNG) — dos archivos con la misma clave producen bytes distintos
- **Nonce único por escritura** (12 bytes) — re-cifrar el mismo texto siempre produce un ciphertext diferente
- **Verificación de tag antes de cargar** — si la firma falla, el editor nunca recibe datos; se lanza `SecurityError`
- **Limpieza de memoria** — `secure_wipe()` + `ctypes.memset()` sobreescriben claves derivadas antes de liberar
- **Archivo de recuperación `.key`** — exporta la clave maestra cifrada bajo una segunda contraseña

### 🖥️ Interfaz

- **Bypass de Semilla (Nuevo)** — Permite guardar documentos en la misma sesión original sin requerir re-ingreso de Frase Semilla, preservando la inyección master actual evitando errores de escritura.
- **Dark mode** por defecto con opción Light mode
- **Auto-lock** a los 10 minutos de inactividad
- **En Android**: contenido oculto al minimizar + bloqueo de capturas de pantalla (`FLAG_SECURE`)
- **Buscar y Reemplazar** con barra retráctil (`Ctrl+F` y auto-sync)
- **Fuente configurable**: tamaño y familia (monoespaciada por defecto)
- **Sin usuario, sin registro** — solo una contraseña maestra por archivo

---

## Modelo de Seguridad

```
  Tu contraseña
       │
       ▼
  PBKDF2-HMAC-SHA256          ← 200,000 iteraciones
  + SALT (32 bytes random)    ← almacenado en header del .spd
       │
       ▼
  AES-256 Key (256 bits)
       │
       ▼
  AES-256-GCM encrypt         ← NONCE (12 bytes random)
  ┌──────────────────────┐
  │  Ciphertext          │    ← solo texto cifrado en disco
  │  Auth Tag (16 bytes) │    ← integridad verificada al abrir
  └──────────────────────┘
       │
       ▼
  .spd file
  [MAGIC][VERSION][KEY_ID][SALT][NONCE][TAG][CT_LEN][CIPHERTEXT]
   ◄─────── header no cifrado ──────►◄──── datos cifrados ────►
```

**Si la clave es incorrecta o el archivo fue manipulado:**
la verificación del GCM tag falla → `SecurityError("Firma de Seguridad Inválida")` → clave borrada de RAM → editor vacío.

---

## Instalación rápida

```bash
# Clona el repositorio
git clone https://github.com/betovildoza/securepad.git
cd securepad

# Crea entorno virtual
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Instala dependencias
pip install -r requirements.txt

# Ejecuta
python main.py
```

**Requisitos:** Python 3.10+ · Windows 10+ o Android 8+

---

## Compilar

### Windows `.exe`
```bash
flet build windows --project SecurePad --org com.securepad
# → build/windows/runner/Release/SecurePad.exe
```

### Android `.apk`
```bash
flet build apk --project SecurePad --org com.securepad
# → build/apk/app-release.apk
```

> Consulta [BUILD_GUIDE.md](BUILD_GUIDE.md) para instrucciones detalladas, firma de APK y configuración de Android SDK.

---

## Estructura del Proyecto

```
SecurePad/
├──src
│  ├── main.py                    # Punto de entrada
│  ├── requirements.txt
│  ├── pyproject.toml             # Metadatos + config flet build
│  ├── BUILD_GUIDE.md             # Instrucciones de compilación
│  ├── securepad/
│  │   ├── crypto_engine.py       # AES-256-GCM · PBKDF2 · secure_wipe
│  │   └── app.py                 # UI completa con Flet
│  └── tests/
│      └── test_crypto.py         # 16 tests de seguridad
└── README.md 
```

---

## Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

```
tests/test_crypto.py::test_roundtrip_ascii                          PASSED
tests/test_crypto.py::test_roundtrip_unicode                        PASSED
tests/test_crypto.py::test_roundtrip_empty_string                   PASSED
tests/test_crypto.py::test_wrong_password_raises_security_error     PASSED
tests/test_crypto.py::test_tampered_ciphertext_raises_security_error PASSED
tests/test_crypto.py::test_tampered_tag_raises_security_error       PASSED
tests/test_crypto.py::test_magic_header                             PASSED
tests/test_crypto.py::test_key_id_extraction                        PASSED
tests/test_crypto.py::test_salt_extraction                          PASSED
tests/test_crypto.py::test_two_encryptions_produce_different_bytes  PASSED
tests/test_crypto.py::test_recovery_key_roundtrip                   PASSED
tests/test_crypto.py::test_recovery_wrong_recovery_password         PASSED
tests/test_crypto.py::test_recovery_wrong_master_password_for_export PASSED
tests/test_crypto.py::test_invalid_key_file_magic                   PASSED
tests/test_crypto.py::test_secure_wipe_zeros_bytearray              PASSED
tests/test_crypto.py::test_invalid_magic                            PASSED

========================= 16 passed in 1.29s =========================
```

---

## Formato de archivo `.spd`

| Offset | Tamaño | Campo | Descripción |
|--------|--------|-------|-------------|
| 0 | 8 B | `MAGIC` | `SPAD\x01\x00\x00\x00` |
| 8 | 2 B | `VERSION` | uint16 LE |
| 10 | 16 B | `KEY_ID` | UUID aleatorio (portabilidad) |
| 26 | 32 B | `SALT` | Salt PBKDF2 (único por archivo) |
| 58 | 12 B | `NONCE` | Nonce AES-GCM (único por cifrado) |
| 70 | 16 B | `TAG` | Auth tag AES-GCM |
| 86 | 8 B | `CT_LEN` | uint64 LE |
| 94 | N B | `CIPHERTEXT` | Texto cifrado |

El header (offsets 0–93) no está cifrado para permitir portabilidad sin necesidad de contraseña. El ciphertext y el tag garantizan que cualquier modificación sea detectable.

---

## Atajos de Teclado

| Atajo | Acción |
|-------|--------|
| `Ctrl+N` | Nueva nota |
| `Ctrl+O` | Abrir `.spd` |
| `Ctrl+S` | Guardar |
| `Ctrl+F` | Buscar y reemplazar |
| `Ctrl+L` | Bloquear sesión |

---

## Stack Técnico

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.10+ |
| UI / Multiplataforma | [Flet](https://flet.dev/) (Flutter) |
| Criptografía | [cryptography.io](https://cryptography.io/) |
| Cifrado | AES-256-GCM |
| Derivación de clave | PBKDF2-HMAC-SHA256 |
| Aleatoriedad | `secrets` (CSPRNG del SO) |
| Limpieza de memoria | `ctypes.memset` |

---

## Contribuir

Las contribuciones son bienvenidas. Por favor abre un issue antes de un PR para discutir cambios mayores.

1. Haz fork del repositorio
2. Crea una rama: `git checkout -b feature/mi-mejora`
3. Asegúrate de que los tests pasen: `pytest tests/ -v`
4. Abre un Pull Request

---

## Aviso de Seguridad

Si encuentras una vulnerabilidad de seguridad, **no abras un issue público**. Envía un reporte privado a través de [GitHub Security Advisories](https://github.com/tu-usuario/securepad/security/advisories/new).

---

## Licencia

Distribuido bajo la licencia MIT. Ver [LICENSE](LICENSE) para más detalles.

---

<div align="center">

Hecho con Python · Sin servidores · Sin compromisos

[![GitHub stars](https://img.shields.io/github/stars/tu-usuario/securepad?style=social)](https://github.com/tu-usuario/securepad)
[![GitHub forks](https://img.shields.io/github/forks/tu-usuario/securepad?style=social)](https://github.com/tu-usuario/securepad/fork)

</div>