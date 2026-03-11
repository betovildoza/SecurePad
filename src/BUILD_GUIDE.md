# SecurePad — Guía de Compilación y Despliegue

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

## 1. Instalación del Entorno de Desarrollo

```bash
# Crea entorno virtual
python -m venv .venv

# Activa (Windows)
.venv\Scripts\activate

# Activa (macOS/Linux)
source .venv/bin/activate

# Instala dependencias
pip install -r requirements.txt

# Ejecutar en modo desarrollo
python main.py
```

---

## 2. Compilar para Windows (.exe)

### Requisitos previos
- Python 3.10–3.12
- Windows 10/11 (64-bit) recomendado
- Flutter SDK instalado: https://docs.flutter.dev/get-started/install/windows

### Paso a paso

```bash
# 1. Instala flet CLI si no está instalado
pip install flet

# 2. Verifica que Flutter esté disponible
flutter doctor

# 3. Compila el ejecutable
flet build windows --project SecurePad --org com.securepad

# El .exe generado estará en:
# build/windows/runner/Release/SecurePad.exe
```

### Alternativa con PyInstaller (sin Flutter)

```bash
pip install pyinstaller

pyinstaller --onefile \
  --windowed \
  --name SecurePad \
  --icon assets/icon.ico \
  --add-data "securepad;securepad" \
  main.py

# Salida: dist/SecurePad.exe
```

**Nota:** con PyInstaller la UI será nativa de escritorio vía Flet web view.
Para la versión más integrada, usar `flet build windows`.

---

## 3. Compilar para Android (.apk / .aab)

### Requisitos previos

1. **Flutter SDK** >= 3.22  
   https://docs.flutter.dev/get-started/install

2. **Android SDK** + NDK  
   Instalar via Android Studio → SDK Manager  
   - Android SDK Platform 33+
   - Android NDK 26+

3. **Java JDK 17** (OpenJDK recomendado)  
   ```bash
   java -version  # debe mostrar 17.x
   ```

4. Variables de entorno:
   ```bash
   # En ~/.bashrc o ~/.zshrc
   export ANDROID_HOME=$HOME/Android/Sdk
   export PATH=$PATH:$ANDROID_HOME/tools:$ANDROID_HOME/platform-tools
   ```

5. Verificar todo:
   ```bash
   flutter doctor -v
   # Todos los checks deben ser ✓ o ⚠ (warnings menores)
   ```

### Compilar APK (distribución directa)

```bash
# Debug APK para pruebas
flet build apk --project SecurePad --org com.securepad

# Release APK firmado (producción)
flet build apk \
  --project SecurePad \
  --org com.securepad \
  --build-number 1 \
  --build-version 1.0.0

# Salida: build/apk/app-release.apk
```

### Compilar AAB (Google Play Store)

```bash
flet build aab \
  --project SecurePad \
  --org com.securepad \
  --build-number 1 \
  --build-version 1.0.0

# Salida: build/aab/app-release.aab
```

### Firma del APK para producción

```bash
# 1. Genera keystore (solo una vez, guárdalo seguro)
keytool -genkey -v \
  -keystore securepad-release.keystore \
  -alias securepad \
  -keyalg RSA \
  -keysize 4096 \
  -validity 10000

# 2. Firma el APK
apksigner sign \
  --ks securepad-release.keystore \
  --ks-key-alias securepad \
  --out SecurePad-signed.apk \
  build/apk/app-release.apk

# 3. Verifica la firma
apksigner verify --verbose SecurePad-signed.apk
```

---

## 4. Permisos Android (AndroidManifest.xml)

Flet genera automáticamente el manifest, pero para SecurePad agrega estas
líneas en `buildfiles/android/app/src/main/AndroidManifest.xml` antes de
la etiqueta `</manifest>`:

```xml
<!-- Bloquear capturas de pantalla -->
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />

<!-- En el activity principal agrega el flag FLAG_SECURE: -->
```

Crea `buildfiles/android/app/src/main/java/.../MainActivity.java` o
modifica el existente para agregar al método `onCreate`:

```java
import android.view.WindowManager;

@Override
protected void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);
    // Bloquear capturas de pantalla y previews de app switcher
    getWindow().setFlags(
        WindowManager.LayoutParams.FLAG_SECURE,
        WindowManager.LayoutParams.FLAG_SECURE
    );
}
```

---

## 5. Formato del Archivo .spd (Referencia Técnica)

```
Offset  Size   Campo        Descripción
------  ----   -----        -----------
0       8      MAGIC        "SPAD\x01\x00\x00\x00"
8       2      VERSION      uint16 LE = 1
10      16     KEY_ID       UUID aleatorio (portabilidad)
26      32     SALT         Salt para PBKDF2 (único por archivo)
58      12     NONCE        Nonce AES-GCM (único por cifrado)
70      16     TAG          Tag de autenticación AES-GCM
86      8      CT_LEN       uint64 LE — longitud del ciphertext
94      N      CIPHERTEXT   Texto cifrado
```

**Todo desde offset 0 hasta 93 es el header NO cifrado.**  
El ciphertext y el tag garantizan autenticidad e integridad.

---

## 6. Formato del Archivo .key (Referencia Técnica)

```
Offset  Size   Campo        Descripción
------  ----   -----        -----------
0       8      MAGIC        "SPKY\x00\x00\x00\x00"
8       16     KEY_ID       Mismo KEY_ID del .spd asociado
24      32     ORIG_SALT    Salt del archivo .spd (para re-derivar)
56      32     REC_SALT     Salt para derivar clave de recuperación
88      12     REC_NONCE    Nonce del cifrado de recuperación
100     16     REC_TAG      Tag de autenticación del .key
116     32     REC_CT       Master key cifrada con recovery password
```

---

## 7. Modelo de Seguridad

| Propiedad         | Implementación                              |
|-------------------|---------------------------------------------|
| Confidencialidad  | AES-256-GCM                                 |
| Autenticidad      | GCM Authentication Tag (16 bytes)           |
| Derivación        | PBKDF2-HMAC-SHA256, 200,000 iteraciones     |
| Unicidad          | Salt 32 bytes + Nonce 12 bytes (aleatorios) |
| Memoria segura    | `secure_wipe()` con ctypes.memset           |
| Sin servidores    | 100% local, archivos portables              |

**Ante cualquier fallo de autenticación:**  
1. Se lanza `SecurityError("Firma de Seguridad Inválida…")`  
2. Se llama `secure_wipe()` sobre la clave derivada antes de propagar  
3. La contraseña del campo UI se borra con `secure_wipe_str()`  
4. El editor queda en blanco — ningún dato plaintext en memoria  

---

## 8. Ejecutar Tests

```bash
# Instala pytest
pip install pytest

# Corre los 16 tests de seguridad
python -m pytest tests/ -v

# Con reporte de cobertura
pip install pytest-cov
python -m pytest tests/ --cov=securepad --cov-report=term-missing
```

---

## 9. Atajos de Teclado

| Atajo     | Acción              |
|-----------|---------------------|
| Ctrl+N    | Nueva nota          |
| Ctrl+O    | Abrir archivo .spd  |
| Ctrl+S    | Guardar             |
| Ctrl+F    | Buscar y reemplazar |
| Ctrl+L    | Bloquear sesión     |
