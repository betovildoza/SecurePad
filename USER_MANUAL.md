# 📚 Manual de Uso - SecurePad v2

Bienvenido al manual oficial de **SecurePad v2**. Este software ha sido diseñado con una filosofía de uso minimalista: máxima seguridad sin pasos complejos, funcionando totalmente *offline* en tu computadora o teléfono Android.

---

## 🔑 Conceptos Básicos de Seguridad

SecurePad cifra tus archivos de extensión `.spd` (`SecurePad Document`) con encriptación real asimétrica usando AES-256-GCM y una derivación intensiva (HMAC + PBKDF2).

Para que la experiencia sea fluida, la Aplicación utiliza un ecosistema híbrido basado en dos factores locales:

1. **Tu Semilla de Recuperación Global (Bip39):** Son 12 palabras aleatorias que identifican criptográficamente a tu instalación o dispositivo. Esta semilla queda guardada de forma encriptada en los ajustes secretos del SO (Android Store o Windows Credential Manager).
2. **Tu Contraseña Maestra (Personal):** Es una contraseña (alfanumérica) que tú eliges cuando **guardas o creas** cada documento nuevo. 

### ¿Qué pasa cuando abro un `.spd`?
El archivo está anclado a las 12 palabras del equipo que lo creó **y** a tu contraseña maestra. Para abrir el candado, basta con insertar tu Contraseña Maestra de corto uso.

Si pierdes o extravías esa Contraseña Maestra, ¡aún hay salvación! Puedes elegir la opción **Desbloquear con Bip39** e ingresar las 12 palabras globales del generador.

---

## 🛠️ Usabilidad del Día a Día

### 1. La Pantalla de Configuración Inicial (Setup)
Al abrir SecurePad v2 por primera vez, verás una pantalla de Setup amigable preguntándote cómo deseas inicializar tu equipo actual. Tienes dos opciones:
* **Generar Semillas Mágicas:** La app generará 12 palabras nuevas solo para ti. Deberás anotarlas en un papel físico y guardarlas en un lugar 100% seguro (fuera de la web).
* **Ingresar mis semillas de otro equipo:** Útil si acabas de comprar una nueva PC, formateaste, o quieres abrir en el celular un `.spd` que creaste en tu laptop. Introduces tus mismas 12 palabras de siempre (separadas por espacio) para unificar la identidad criptográfica. 

> *Nota: Una vez generada la semilla, ya no volverás a ver esta pantalla inicial de Setup. Irás directo al editor cada vez que abras la app, ahorrándote tiempo.*

### 2. Bloqueo Inteligente de Documento
¿Te levantas por un café y dejas tu PC con el documento de claves abierto?
Para tu tranquilidad, SecurePad incluye un **candado rojo** en la barra superior del editor para bloquear físicamente el acceso al archivo en un clic.

* **Si el archivo YA estaba previamente guardado en tu disco:** Aparecerá la ventana negra de "Bóveda Bloqueada". La memoria de la PC ha sido sanitizada al instante en que pulsaste el candado y ya nadie puede leer el contenido. Para regresar, ingresa tu código Maestro o pulsa la cruz para "Cerrar archivo físicamente".
* **Si tu documento NUNCA se ha guardado (.spd en blanco):** Si bloqueas accidentalmente, la pantalla se volverá negra con un escudo central con el cartel "Documento Oculto". **Tranquilo, tu texto no se ha borrado.** Como SecurePad no quiere arriesgar que pierdas tu trabajo no guardado, permite hacer clic en "Regresar al editor" sin contraseña, forzándote únicamente a esconderlo visualmente.  

### 3. Editor Profesional y Ajustes Visuales
Hemos cambiado el editor arcaico por una ventana *CodeMirror* asíncrona:
- Puedes cambiar la **fuente** del texto o el **tema visual** (`Día`/`Noche`) desde el engranaje de configuración.
- Con el atajo de redactor `[Alt + Z]` (o desde los ajustes) podrás activar el **Word Wrap** (Ajuste de línea), permitiendo que renglones kilométricos se adapten visualmente a tu pantalla sin corromper el número real de fila. Ideal para edición de código en laptop o celulares estrechos.
- Se ha incluido `Búsqueda Nativa` de texto presionando `Ctrl + F`.

---

## 🆘 Resolución de Problemas

1. **Olvidé las 12 palabras en mi PC actual, ¿puedo verlas?**
   Por seguridad criptográfica, las 12 palabras **jamás** pueden volver a visualizarse libres de cifrado una vez aceptadas en el setup. Si puedes abrir tus bóvedas con Contraseña y deseas regenerar tus 12 palabras "desde cero" porque se perdió el papel:
   Aprovecha mientras el documento está bloqueado y pulsa el nuevo botón **"Reset/Regenerar"**. Se pedirá tu Contraseña Maestra actual para avalar tu identidad, te brindará 12 palabras nuevas y *Re-cifrará* la bóveda ligándola eternamente al nuevo Bip39 verde mostrado.

2. **Error al cifrar o descifrar el Header (Android/Windows)**
   Esto suele ocurrir porque el equipo tiene una "Semilla Global A" y tratas de abrir un archivo `.spd` creado en una instalación con "Semilla Global B". Para solucionarlo, tendrás que desbloquearlo localmente con la semilla original mediante la opción "BiP39" del candado, resetear los credenciales, y volver a generarlas para tu nuevo equipo.
