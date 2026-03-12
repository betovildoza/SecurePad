import { useState, useRef, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { save, open } from "@tauri-apps/plugin-dialog";
import { readFile, writeFile } from "@tauri-apps/plugin-fs"; // IMPORTANTE: file-saver en JS
import CodeMirror, { EditorView } from '@uiw/react-codemirror';
import { javascript } from '@codemirror/lang-javascript';
import { oneDark } from '@codemirror/theme-one-dark';

// Import Componentes Extraídos
import { Toolbar } from "./components/Toolbar";
import { SettingsModal } from "./components/SettingsModal";
import { SaveVaultModal } from "./components/SaveVaultModal";
import { LockScreenOverlay } from "./components/LockScreenOverlay";

interface EditorProps {
  initialContent: string;
  filePath: string | null;
  onClose: () => void;
  onNewVault: () => void;
  onOpenVault: (file: string) => void;
}

export function Editor({ initialContent, filePath, onClose, onNewVault, onOpenVault }: EditorProps) {
  const [content, setContent] = useState(initialContent);
  const [currentFilePath, setCurrentFilePath] = useState<string | null>(filePath);
  
  // Save/Encrypt state
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");
  const [generatedSeed, setGeneratedSeed] = useState<string | null>(null);

  // Auto-Lock state
  const [isLocked, setIsLocked] = useState(false);
  const [unlockPassword, setUnlockPassword] = useState("");
  const [unlockSeed, setUnlockSeed] = useState("");
  const [unlockMode, setUnlockMode] = useState<"PASSWORD" | "SEED" | "RESET_SEED">("PASSWORD");
  const [unlockError, setUnlockError] = useState("");
  const [newGeneratedSeed, setNewGeneratedSeed] = useState<string | null>(null);
  let inactivityTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Settings State
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 600;
  const [showSettings, setShowSettings] = useState(false);
  const [wordWrap, setWordWrap] = useState(true);
  const [fontSize, setFontSize] = useState(isMobile ? 20 : 14);
  const [fontFamily, setFontFamily] = useState("var(--font-mono)");
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  const fontOptions = [
      { label: "Courier (Default)", value: "var(--font-mono)" },
      { label: "Consolas", value: "'Consolas', monospace" },
      { label: "Fira Code", value: "'Fira Code', monospace" },
      { label: "JetBrains Mono", value: "'JetBrains Mono', monospace" },
      { label: "Roboto Mono", value: "'Roboto Mono', monospace" },
      { label: "Source Code Pro", value: "'Source Code Pro', monospace" },
      { label: "Ubuntu Mono", value: "'Ubuntu Mono', monospace" },
      { label: "Inconsolata", value: "'Inconsolata', monospace" },
      { label: "Arial", value: "Arial, sans-serif" },
      { label: "Verdana", value: "Verdana, sans-serif" }
  ];

  // Set initial theme based on body data-theme
  useEffect(() => {
     const currentTheme = document.documentElement.getAttribute("data-theme");
     if (currentTheme === "light" || currentTheme === "dark") {
         setTheme(currentTheme);
     }
  }, []);

  // Set initial theme based on body data-theme
  useEffect(() => {
     const currentTheme = document.documentElement.getAttribute("data-theme");
     if (currentTheme === "light" || currentTheme === "dark") {
         setTheme(currentTheme);
     }
  }, []);

  const handleSaveFlow = async () => {
    if (!currentFilePath && !generatedSeed) {
      try {
        const seed = await invoke<string>("generate_seed");
        setGeneratedSeed(seed);
      } catch (err) {
        console.error("Error generating seed:", err);
      }
    }
    setShowSaveModal(true);
  };

  const executeSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password) {
      setError("La contraseña no puede estar vacía");
      return;
    }
    if (!currentFilePath && password !== confirmPassword) {
      setError("Las contraseñas no coinciden");
      return;
    }

    setError("");
    setIsSaving(true);

    try {
      let targetPath = currentFilePath;
      if (!targetPath) {
        let selectedPath = await save({ filters: [{ name: 'SecurePad Vault', extensions: ['spd'] }] });
        if (!selectedPath) { setIsSaving(false); return; }
        
        // Android fix: Ensure .spd extension is present, save dialog might not append it automatically
        if (typeof selectedPath === 'string' && !selectedPath.toLowerCase().endsWith('.spd')) {
            selectedPath += '.spd';
        }
        targetPath = selectedPath as string;
      }

      let currentSeed = generatedSeed;
      if (!targetPath && !currentSeed) {
          currentSeed = await invoke<string>("generate_seed");
      }

      // 1. Invocar a Rust para cifrar y devolver un array de bytes
      const encryptedBytesArray: number[] = await invoke("encrypt_note", {
        plaintext: content,
        password: password,
        // Tauri TS bindings require camelCase by default matching Rust struct #[serde(rename_all = "camelCase")]
        seedPhrase: currentSeed || "dummy-seed-for-existing-file-not-used-but-needed-by-api"
      });

      // 2. Usar API de FS de Javascript para guardar en disco real o URI en Android
      const fileBytes = new Uint8Array(encryptedBytesArray);
      await writeFile(targetPath, fileBytes);

      setCurrentFilePath(targetPath);
      setShowSaveModal(false);
      setPassword("");
      setConfirmPassword("");
    } catch (err: any) {
      console.error(err);
      setError(typeof err === "string" ? err : "Error al cifrar y guardar el archivo");
    } finally {
      setIsSaving(false);
    }
  };

  const handleOpenLocal = async () => {
      const file = await open({ multiple: false, directory: false, filters: [{ name: 'SecurePad Vault', extensions: ['spd'] }] });
      if (file && typeof file === "string") {
        onOpenVault(file);
      }
  };

  // Lock Mechanism
  const resetInactivityTimer = () => {
      if (inactivityTimer.current) clearTimeout(inactivityTimer.current);
      inactivityTimer.current = setTimeout(() => {
          // Solo bloquear automáticamente si el archivo ha sido guardado previamente (existe path)
          if (currentFilePath) {
              setIsLocked(true);
          }
      }, 120000); // 2 minutes
  };

  useEffect(() => {
      // Setup events
      const events = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart'];
      const handleActivity = () => { if(!isLocked) resetInactivityTimer(); };
      
      events.forEach(evt => document.addEventListener(evt, handleActivity));
      
      const handleFocus = () => { /* Logic to unlock automatically? Wait, no, we lock on blur */ };
      const handleBlur = () => { 
          // Solo si tiene path
          if (currentFilePath) {
              setIsLocked(true); 
          }
      };
      
      window.addEventListener('blur', handleBlur);
      window.addEventListener('focus', handleFocus);
      
      resetInactivityTimer(); // Initial start

      // Alt+Z Shortcut for Word Wrap
      const handleShortcut = (e: KeyboardEvent) => {
          if (e.altKey && e.key.toLowerCase() === 'z') {
              e.preventDefault();
              setWordWrap(prev => !prev);
          }
      };
      window.addEventListener('keydown', handleShortcut);

      return () => {
          events.forEach(evt => document.removeEventListener(evt, handleActivity));
          window.removeEventListener('blur', handleBlur);
          window.removeEventListener('focus', handleFocus);
          window.removeEventListener('keydown', handleShortcut);
          if (inactivityTimer.current) clearTimeout(inactivityTimer.current);
      };
  }, [isLocked, currentFilePath]);

  const handleUnlock = async (e: React.FormEvent) => {
      e.preventDefault();
      // En una app real de escritorio, deberiamos reenviar la password
      // De hecho, en el EDITOR de Flet, el Auto-Lock sólo tapaba la pantalla (si el memo ya estaba descifrado). 
      // Si requerimos descifrar de nuevo, perdemos cambios no guardados. 
      // Aquí simulamos el bloqueo visual, requerirá la misma contraseña que usamos para guardar o abrir?
      // O solo destapamos? Flet usaba una validación contra el hash en memoria. 
      // Por simplicidad en React, vamos a hacer que un blur bloquee visualmente.
      
      setUnlockError("");
      
      if (!currentFilePath) {
          // Si es un archivo sin guardar, el bloqueo es puramente visual sobre el DOM.
          // Flet simplemente retiraba el overlay.
          setIsLocked(false);
          setUnlockPassword("");
          return;
      }

      try {
          // 1. Array de bytes leído a través de js (fundamental para content:// android URI)
          const fileBytes = await readFile(currentFilePath);
          
          if (unlockMode === "RESET_SEED" && currentFilePath) {
              // Validar contraseña primero usando JSON serialization
              await invoke("decrypt_note", { fileBytes: Array.from(fileBytes), password: unlockPassword });
              
              // Si fue exitosa, generar nueva semilla y re-cifrar
              const newSeed = await invoke<string>("generate_seed");
              const encryptedBytesArr: number[] = await invoke("encrypt_note", {
                  plaintext: content,
                  password: unlockPassword,
                  seedPhrase: newSeed
              });
              
              const newBytes = new Uint8Array(encryptedBytesArr);
              await writeFile(currentFilePath, newBytes);
              
              setNewGeneratedSeed(newSeed);
              setUnlockError("¡Semilla actualizada con éxito! Guárdala en un lugar seguro.");
              return; // No destapamos automáticamente para que el usuario pueda copiar las 12 palabras
          }

          if (unlockMode === "PASSWORD") {
             await invoke("decrypt_note", { fileBytes: Array.from(fileBytes), password: unlockPassword });
          } else if (unlockMode === "SEED") {
             await invoke("decrypt_seed", { fileBytes: Array.from(fileBytes), seedPhrase: unlockSeed.trim() });
          }
          
          setIsLocked(false);
          setUnlockPassword("");
          setUnlockSeed("");
          setNewGeneratedSeed(null);
      } catch (err: any) {
          setUnlockError("Credenciales o Semilla incorrectas");
      }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", width: "100%", position: "relative" }}>
      
      <Toolbar 
        currentFilePath={currentFilePath}
        onNewVault={onNewVault}
        onOpenLocal={handleOpenLocal}
        onSaveFlow={handleSaveFlow}
        onToggleSettings={() => setShowSettings(!showSettings)}
        onClose={onClose}
      />

      {/* EDITOR AREA (CodeMirror) */}
      <div style={{ flex: 1, display: "flex", position: "relative", overflow: "hidden", background: "var(--surface)", fontSize: `${fontSize}px`, fontFamily: fontFamily }}>
            <CodeMirror
              value={content}
              height="100%"
              extensions={[
                  javascript({ jsx: true }),
                  wordWrap ? EditorView.lineWrapping : []
              ]}
              theme={theme === "dark" ? oneDark : "light"}
              onChange={(value) => setContent(value)}
              basicSetup={{
                 lineNumbers: true,
                 foldGutter: false,
                 highlightActiveLine: false,
                 searchKeymap: true
              }}
              style={{
                 width: "100%", height: "100%", position: "absolute", top: 0, left: 0, bottom: 0, right: 0,
                 fontSize: `${fontSize}px`, fontFamily: fontFamily
              }}
              className={wordWrap ? "cm-word-wrap-enabled cm-theme-override" : "cm-theme-override"}
            />
            <style>{`
              .cm-theme-override .cm-content, 
              .cm-theme-override .cm-line {
                font-family: ${fontFamily} !important;
              }
            `}</style>
            {wordWrap && (
                <style>{`
                  .cm-word-wrap-enabled .cm-content {
                    white-space: pre-wrap !important;
                    word-break: break-word !important;
                  }
                  .cm-word-wrap-enabled .cm-line {
                    white-space: pre-wrap !important;
                  }
                `}</style>
            )}
      </div>

      {/* STATUS BAR */}
      <div style={{
          background: "var(--accent)", color: "white", padding: "8px 16px calc(8px + env(safe-area-inset-bottom, 0px)) 16px",
          display: "flex", justifyContent: "space-between", alignItems: "center",
          fontSize: "0.75rem", fontFamily: "var(--font-mono)", fontWeight: "500", zIndex: 10
      }}>
          {!isMobile && <span>{currentFilePath ? currentFilePath.split('\\').pop()?.split('/').pop() : "Sin título.spd"}</span>}
          <div style={{ display: "flex", gap: "1.5rem", width: isMobile ? "100%" : "auto", justifyContent: isMobile ? "center" : "flex-end" }}>
              {!isMobile && <span style={{ cursor: "pointer" }} onClick={() => setWordWrap(!wordWrap)} title="Alt+Z">{wordWrap ? "Word Wrap: ON" : "Word Wrap: OFF"}</span>}
              <span>AES-256-GCM Protegido</span>
              <span>UTF-8</span>
              {!isMobile && <span>{content.length} bytes</span>}
          </div>
      </div>

      <SettingsModal 
          isOpen={showSettings}
          theme={theme} setTheme={setTheme}
          fontFamily={fontFamily} setFontFamily={setFontFamily}
          fontSize={fontSize} setFontSize={setFontSize}
          wordWrap={wordWrap} setWordWrap={setWordWrap}
          fontOptions={fontOptions}
          onClose={() => setShowSettings(false)}
      />

      <SaveVaultModal 
          isOpen={showSaveModal}
          currentFilePath={currentFilePath}
          password={password as any} setPassword={setPassword}
          confirmPassword={confirmPassword as any} setConfirmPassword={setConfirmPassword}
          error={error} isSaving={isSaving} onSubmit={executeSave}
          onClose={() => setShowSaveModal(false)}
      />

      <LockScreenOverlay 
          isLocked={isLocked}
          currentFilePath={currentFilePath}
          unlockMode={unlockMode} setUnlockMode={setUnlockMode}
          unlockError={unlockError} setUnlockError={setUnlockError}
          unlockPassword={unlockPassword as any} setUnlockPassword={setUnlockPassword}
          unlockSeed={unlockSeed} setUnlockSeed={setUnlockSeed}
          newGeneratedSeed={newGeneratedSeed} setNewGeneratedSeed={setNewGeneratedSeed}
          onUnlockSubmit={handleUnlock}
          onClosePhysical={onClose}
          onSaveFlow={handleSaveFlow}
          onReturnEditor={() => setIsLocked(false)}
      />

    </div>
  );
}
