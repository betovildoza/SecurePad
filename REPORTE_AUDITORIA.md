# Reporte de Auditoría y Estado de la Aplicación - SecurePad v2

## 1. Introducción
Este documento presenta un análisis detallado de la aplicación **SecurePad v2**, evaluando su arquitectura, implementación criptográfica, usabilidad y áreas potenciales de mejora. SecurePad es un editor de texto enfocado en la privacidad que utiliza cifrado local sin dependencia de la nube.

---

## 2. Resumen Ejecutivo
SecurePad v2 representa una evolución significativa respecto a su versión original en Flet. La transición a **Rust** para el núcleo criptográfico y **Tauri + React** para la interfaz proporciona una base sólida en términos de rendimiento y seguridad nativa. La aplicación cumple con su promesa de "offline-first" y control total por parte del usuario.

---

## 3. Auditoría de Funcionamiento

### 3.1 Motor Criptográfico (Rust)
- **Algoritmo:** Utiliza **AES-256-GCM**, el estándar de la industria para cifrado autenticado, lo que garantiza tanto confidencialidad como integridad de los datos.
- **Derivación de Claves:** Emplea **PBKDF2-HMAC-SHA256** con 200,000 iteraciones. Es una implementación robusta, aunque existen alternativas más modernas y resistentes a ataques de GPU.
- **Recuperación:** Implementa un sistema dual donde el archivo se puede descifrar con la contraseña maestra o con una semilla de recuperación **BIP39** de 12 palabras.
- **Higiene de Memoria:** Se observa el uso de los traits `Zeroize` y `ZeroizeOnDrop` en estructuras sensibles como `MasterKey`, lo cual es una excelente práctica para prevenir fugas de claves en la memoria RAM.

### 3.2 Interfaz de Usuario (Frontend)
- **Tecnología:** React 19 con TypeScript, proporcionando una interfaz reactiva y tipado fuerte.
- **Editor:** Integración de **CodeMirror 6**, que permite manejar archivos grandes con resaltado de sintaxis y word-wrap de manera eficiente.
- **Persistencia:** Uso de `tauri-plugin-store` para configuraciones y `tauri-plugin-fs` para el manejo de archivos directamente desde el sistema de archivos (esencial para compatibilidad con Android).

### 3.3 Flujo de Usuario
- El proceso de **Setup** inicial obliga a establecer una identidad criptográfica, lo cual es crítico para el sistema de recuperación.
- El **Auto-Lock** (bloqueo por inactividad o pérdida de foco) añade una capa extra de protección física.

---

## 4. Fortalezas
1. **Privacidad Absoluta:** No hay telemetría, no hay cuentas, no hay servidores.
2. **Rendimiento:** El uso de Rust permite que las operaciones de cifrado sean casi instantáneas incluso en archivos grandes.
3. **Portabilidad:** Los archivos `.spd` contienen todo lo necesario para ser descifrados en cualquier instancia de SecurePad (siempre que se tenga la contraseña o la semilla).
4. **Seguridad por Diseño:** El uso de cifrado autenticado (GCM) evita ataques de manipulación de bits (bit-flipping).

---

## 5. Espacios de Mejora (Auditoría Técnica)

### 5.1 Seguridad
- **KDF Moderno:** Se recomienda migrar de PBKDF2 a **Argon2id**. Argon2 es el ganador del Password Hashing Competition y ofrece mejor resistencia contra ataques de fuerza bruta basados en hardware especializado (ASIC/GPU).
- **Almacenamiento de la Semilla Global:** Actualmente, en `Setup.tsx`, la frase semilla se guarda en texto plano (dentro de un JSON gestionado por el store) si el sistema no está configurado para cifrar el store. Se debería considerar el uso de `keyring` (a través de plugins de Tauri) para almacenar la semilla en el gestor de credenciales nativo del sistema operativo (Windows Credential Manager / Android KeyStore).
- **Entropía de la Sal (Salt):** El salt de 32 bytes es excelente, pero se debe asegurar que se guarde de forma que no se degrade la seguridad en futuras versiones.

### 5.2 Experiencia de Usuario (UX)
- **Manejo de "Dummy Seed":** En `Editor.tsx`, se observa el uso de `"dummy-seed-for-existing-file..."` al re-guardar archivos. Esto indica que si se guarda un archivo que ya existe, no se está actualizando o manteniendo correctamente el vínculo con la semilla original en esa llamada específica. Esto podría romper la recuperación por BIP39 si no se maneja con cuidado.
- **Indicadores de Guardado:** Falta un indicador visual de "Cambios sin guardar" (ej. un asterisco en el título).
- **Feedback de Errores:** Algunos errores de Rust se pasan directamente a la UI. Sería ideal mapearlos a mensajes más amigables para el usuario final.

### 5.3 Calidad de Código
- **Consistencia en IPC:** La conversión manual `Array.from(fileBytes)` para pasar datos a Rust es funcional pero ineficiente para archivos muy grandes. Se recomienda investigar el uso de canales de datos binarios de Tauri v2.
- **Duplicación de Código:** Hay algo de lógica duplicada entre `Unlock.tsx` y el componente de bloqueo en `Editor.tsx`. Se podría unificar en un hook de autenticación.

---

## 6. Conclusión
SecurePad v2 es una herramienta robusta y bien construida. Sus fundamentos de seguridad son sólidos. La mayoría de los "espacios de mejora" son refinamientos técnicos que elevarían la aplicación de un estado de "herramienta personal confiable" a "estándar de seguridad profesional".

**Prioridad recomendada:**
1. Implementar almacenamiento seguro de la Semilla Global (OS Keyring).
2. Evaluar la migración a Argon2id.
3. Refinar el flujo de "Guardado" para asegurar la integridad de la recuperación por semilla.
