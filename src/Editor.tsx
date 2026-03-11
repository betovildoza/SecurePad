import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Save, X, Lock, FilePlus, FolderOpen, Settings, Info } from "lucide-react";
import { invoke } from "@tauri-apps/api/core";
import { save, open } from "@tauri-apps/plugin-dialog";
import CodeMirror, { EditorView } from '@uiw/react-codemirror';
import { javascript } from '@codemirror/lang-javascript';
import { oneDark } from '@codemirror/theme-one-dark';

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
  const [showSettings, setShowSettings] = useState(false);
  const [wordWrap, setWordWrap] = useState(false);
  const [fontSize, setFontSize] = useState(14);
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
        const selectedPath = await save({ filters: [{ name: 'SecurePad Vault', extensions: ['spd'] }] });
        if (!selectedPath) { setIsSaving(false); return; }
        targetPath = selectedPath;
      }

      let currentSeed = generatedSeed;
      if (!targetPath && !currentSeed) {
          currentSeed = await invoke<string>("generate_seed");
      }

      await invoke("encrypt_note", {
        plaintext: content,
        password: password,
        // Tauri TS bindings require camelCase by default matching Rust struct #[serde(rename_all = "camelCase")]
        seedPhrase: currentSeed || "dummy-seed-for-existing-file-not-used-but-needed-by-api",
        filePath: targetPath 
      });

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
          // Si no está guardado, no hay pass validada contra Rust fácil, solo destapamos
          setIsLocked(false);
          setUnlockPassword("");
          return;
      }

      try {
          if (unlockMode === "RESET_SEED" && currentFilePath) {
              // Validar contraseña primero
              await invoke("decrypt_note", { filePath: currentFilePath, password: unlockPassword });
              
              // Si fue exitosa, generar nueva semilla y re-cifrar
              const newSeed = await invoke<string>("generate_seed");
              await invoke("encrypt_note", {
                  plaintext: content,
                  password: unlockPassword,
                  seedPhrase: newSeed,
                  filePath: currentFilePath 
              });
              
              setNewGeneratedSeed(newSeed);
              setUnlockError("¡Semilla actualizada con éxito! Guárdala en un lugar seguro.");
              return; // No destapamos automáticamente para que el usuario pueda copiar las 12 palabras
          }

          if (unlockMode === "PASSWORD") {
             await invoke("decrypt_note", { filePath: currentFilePath, password: unlockPassword });
          } else if (unlockMode === "SEED") {
             await invoke("decrypt_seed", { filePath: currentFilePath, seedPhrase: unlockSeed.trim() });
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
      
      {/* TOOLBAR FLET-STYLE (MODIFICADO) */}
      <div style={{ 
        display: "flex", alignItems: "center", justifyContent: "space-between", 
        padding: "0.5rem 1rem", background: "var(--panel)", borderBottom: "1px solid var(--border)",
        boxShadow: "0 2px 10px rgba(0,0,0,0.05)", zIndex: 10
      }}>
        {/* Lado Izquierdo (Vacío o Logo) */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--muted)", fontSize: "0.85rem", fontWeight: "bold" }}>
          SecurePad Editor
        </div>
            
        {/* Lado Derecho (Botones de Acción y Configuración) */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <button className="icon-btn" title="Nueva Bóveda" onClick={onNewVault}>
                <FilePlus size={20} />
            </button>
            <button className="icon-btn" title="Abrir Bóveda" onClick={handleOpenLocal}>
                <FolderOpen size={20} />
            </button>
            <button className="icon-btn" title="Guardar" onClick={handleSaveFlow}>
                <Save size={20} />
            </button>
            
            <div style={{ width: "1px", height: "24px", background: "var(--border)", margin: "0 4px" }} />

            <button className="icon-btn" title="Ajustes (Alt+Z = Word Wrap)" onClick={() => setShowSettings(!showSettings)}>
                <Settings size={20} />
            </button>

            <div style={{ width: "1px", height: "24px", background: "var(--border)", margin: "0 4px" }} />

            <button className="icon-btn danger" title="Cerrar y Bloquear Bóveda" onClick={onClose} style={{ marginLeft: "0.25rem" }}>
                <Lock size={20} color="var(--bg)" />
            </button>
        </div>
      </div>

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
                 searchKeymap: true // Habilita la búsqueda nativa de codemirror (ctrl+f)
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
          background: "var(--accent)", color: "white", padding: "4px 16px",
          display: "flex", justifyContent: "space-between", alignItems: "center",
          fontSize: "0.75rem", fontFamily: "var(--font-mono)", fontWeight: "500", zIndex: 10
      }}>
          <span>{currentFilePath ? currentFilePath.split('\\').pop()?.split('/').pop() : "Sin título.spd"}</span>
          <div style={{ display: "flex", gap: "1.5rem" }}>
              <span style={{ cursor: "pointer" }} onClick={() => setWordWrap(!wordWrap)} title="Alt+Z">{wordWrap ? "Word Wrap: ON" : "Word Wrap: OFF"}</span>
              <span>AES-256-GCM Protegido</span>
              <span>UTF-8</span>
              <span>{content.length} bytes</span>
          </div>
      </div>

      {/* MODAL DE AJUSTES (DISEÑO BASE) */}
      <AnimatePresence>
      {showSettings && (
          <div style={{
              position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
              background: "var(--overlay)", zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center"
          }}>
              <motion.div 
                initial={{ opacity: 0, scale: 0.95, y: 10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: -10 }}
                style={{
                    background: "var(--surface)", padding: "2rem", borderRadius: "12px",
                    width: "100%", maxWidth: "400px", border: "1px solid var(--border)", position: "relative",
                    display: "flex", flexDirection: "column", gap: "1.5rem"
                }}
              >
                  <button className="icon-btn" onClick={() => setShowSettings(false)} style={{ position: "absolute", top: "16px", right: "16px" }}>
                      <X size={20} />
                  </button>

                  <h3 style={{ margin: "0 0 1rem 0", fontSize: "1.25rem", display: "flex", alignItems: "center", gap: "0.5rem" }}><Settings size={22} /> Ajustes del Documento</h3>
                  
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                      <label style={{ fontSize: "0.85rem", color: "var(--muted)", fontWeight: "bold" }}>Tema Visual</label>
                      <div style={{ display: "flex", gap: "0.5rem", background: "var(--panel)", padding: "4px", borderRadius: "8px", border: "1px solid var(--border)" }}>
                          <button 
                             style={{ flex: 1, padding: "6px", background: theme === "dark" ? "var(--surface)" : "transparent", color: theme === "dark" ? "var(--text)" : "var(--muted)", border: theme === "dark" ? "1px solid var(--border)" : "none", borderRadius: "6px", boxShadow: theme === "dark" ? "0 2px 5px rgba(0,0,0,0.2)" : "none" }}
                             onClick={() => { setTheme("dark"); document.documentElement.setAttribute("data-theme", "dark"); }}
                          >
                              Noche
                          </button>
                          <button 
                             style={{ flex: 1, padding: "6px", background: theme === "light" ? "var(--surface)" : "transparent", color: theme === "light" ? "var(--text)" : "var(--muted)", border: theme === "light" ? "1px solid var(--border)" : "none", borderRadius: "6px", boxShadow: theme === "light" ? "0 2px 5px rgba(0,0,0,0.1)" : "none" }}
                             onClick={() => { setTheme("light"); document.documentElement.setAttribute("data-theme", "light"); }}
                          >
                              Día
                          </button>
                      </div>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                      <label style={{ fontSize: "0.85rem", color: "var(--muted)", fontWeight: "bold" }}>Tipografía</label>
                      <select 
                         style={{ padding: "8px", background: "var(--panel)", color: "var(--text)", border: "1px solid var(--border)", borderRadius: "4px", outline: "none" }}
                         value={fontFamily}
                         onChange={(e) => setFontFamily(e.target.value)}
                      >
                          {fontOptions.map(font => (
                              <option key={font.value} value={font.value}>{font.label}</option>
                          ))}
                      </select>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                      <label style={{ fontSize: "0.85rem", color: "var(--muted)", fontWeight: "bold" }}>Tamaño de fuente: {fontSize}px</label>
                      <input 
                         type="range" min="10" max="32" value={fontSize} 
                         onChange={(e) => setFontSize(Number(e.target.value))}
                         style={{ width: "100%" }}
                      />
                  </div>

                  <div 
                     style={{ display: "flex", alignItems: "center", justifyContent: "space-between", cursor: "pointer", userSelect: "none" }}
                     onClick={() => setWordWrap(!wordWrap)}
                     title="Atajo de teclado: Alt+Z"
                  >
                      <label style={{ fontSize: "0.85rem", color: "var(--muted)", fontWeight: "bold", cursor: "pointer" }}>Word Wrap (Alt+Z)</label>
                      <div style={{ 
                          width: "44px", height: "24px", background: wordWrap ? "var(--accent)" : "var(--panel)", 
                          borderRadius: "12px", padding: "2px", display: "flex", alignItems: "center", 
                          justifyContent: wordWrap ? "flex-end" : "flex-start", border: "1px solid var(--border)", transition: "all 0.3s" 
                      }}>
                          <div style={{ width: "18px", height: "18px", borderRadius: "50%", background: wordWrap ? "#fff" : "var(--muted)", boxShadow: "0 1px 3px rgba(0,0,0,0.3)", transition: "all 0.3s" }} />
                      </div>
                  </div>
              </motion.div>
          </div>
      )}
      </AnimatePresence>

      {/* MODAL GUARDAR */}
      <AnimatePresence>
      {showSaveModal && (
        <div style={{
            position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
            background: "var(--overlay)", zIndex: 100,
            display: "flex", alignItems: "center", justifyContent: "center"
        }}>
            <motion.div 
                initial={{ opacity: 0, scale: 0.95, y: 10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: -10 }}
                style={{
                    background: "var(--surface)", padding: "2rem", borderRadius: "12px",
                    width: "100%", maxWidth: "450px", border: "1px solid var(--border)"
                }}
            >
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1.5rem" }}>
                    <Lock size={24} color="var(--accent)" />
                    <h2 style={{ margin: 0, fontSize: "1.25rem" }}>{currentFilePath ? "Actualizar Bóveda" : "Proteger Nueva Bóveda"}</h2>
                </div>

                <form onSubmit={executeSave} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                    <div>
                        <label style={{ display: "block", fontSize: "0.85rem", color: "var(--muted)", marginBottom: "4px", fontWeight: "600" }}>Contraseña Maestra</label>
                        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} style={{ width: "100%", padding: "10px" }} autoFocus />
                    </div>

                    {!currentFilePath && (
                         <div>
                         <label style={{ display: "block", fontSize: "0.85rem", color: "var(--muted)", marginBottom: "4px", fontWeight: "600" }}>Confirmar Contraseña</label>
                         <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} style={{ width: "100%", padding: "10px" }} />
                     </div>
                    )}

                    {error && <p style={{ color: "var(--danger)", margin: 0, fontSize: "0.85rem", display: "flex", alignItems: "center", gap: "4px" }}><Info size={14} /> {error}</p>}

                    <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem", marginTop: "1rem" }}>
                        <button type="button" onClick={() => setShowSaveModal(false)} disabled={isSaving} style={{ padding: "10px 16px", background: "transparent", color: "var(--text)" }}>Cancelar</button>
                        <button type="submit" className="primary" disabled={isSaving || !password} style={{ padding: "10px 16px" }}>
                            {isSaving ? "Cifrando..." : "Cifrar y Guardar"}
                        </button>
                    </div>
                </form>
            </motion.div>
        </div>
      )}
      </AnimatePresence>

      {/* MODAL AUTO-LOCK / MANUAL LOCK */}
      <AnimatePresence>
      {isLocked && (
          <div style={{
              position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
              background: "var(--bg)", zIndex: 1000, // Highest z-index to block everything
              display: "flex", alignItems: "center", justifyContent: "center",
              backdropFilter: "blur(4px)"
          }}>
              <motion.div 
                  initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                  style={{ textAlign: "center", width: "100%", maxWidth: "340px", padding: "2rem" }}
              >
                  <div style={{ 
                      width: "64px", height: "64px", borderRadius: "50%", 
                      background: "rgba(220, 53, 69, 0.1)", display: "flex", alignItems: "center", justifyContent: "center",
                      margin: "0 auto 1.5rem auto", border: "1px solid var(--danger)"
                  }}>
                      <Lock size={32} color="var(--danger)" />
                  </div>
                  <h2 style={{ margin: "0 0 0.5rem 0" }}>Bóveda Bloqueada</h2>
                  <p style={{ margin: "0 0 2rem 0", color: "var(--muted)", fontSize: "0.9rem" }}>La bóveda ha sido bloqueada por seguridad. Introduce tus credenciales para continuar.</p>
                  
                  <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem", background: "var(--surface)", padding: "4px", borderRadius: "8px", border: "1px solid var(--border)" }}>
                      <button 
                         style={{ flex: 1, padding: "6px", background: unlockMode === "PASSWORD" ? "var(--panel)" : "transparent", color: unlockMode === "PASSWORD" ? "var(--text)" : "var(--muted)", border: unlockMode === "PASSWORD" ? "1px solid var(--border)" : "none", borderRadius: "6px" }}
                         onClick={() => { setUnlockMode("PASSWORD"); setUnlockError(""); setNewGeneratedSeed(null); }}
                      >
                          Contraseña
                      </button>
                      <button 
                         style={{ flex: 1, padding: "6px", background: unlockMode === "SEED" ? "var(--panel)" : "transparent", color: unlockMode === "SEED" ? "var(--text)" : "var(--muted)", border: unlockMode === "SEED" ? "1px solid var(--border)" : "none", borderRadius: "6px" }}
                         onClick={() => { setUnlockMode("SEED"); setUnlockError(""); setNewGeneratedSeed(null); }}
                      >
                          BiP39
                      </button>
                      <button 
                         style={{ flex: 1, padding: "6px", background: unlockMode === "RESET_SEED" ? "var(--panel)" : "transparent", color: unlockMode === "RESET_SEED" ? "var(--text)" : "var(--muted)", border: unlockMode === "RESET_SEED" ? "1px solid var(--border)" : "none", borderRadius: "6px" }}
                         onClick={() => { setUnlockMode("RESET_SEED"); setUnlockError(""); setNewGeneratedSeed(null); }}
                         title="Generar nueva semilla de recuperación"
                      >
                          Reset
                      </button>
                  </div>

                  {newGeneratedSeed && unlockMode === "RESET_SEED" && (
                    <div style={{ background: "rgba(46, 125, 50, 0.1)", border: "1px solid var(--success)", padding: "1rem", borderRadius: "8px", marginBottom: "1.5rem" }}>
                        <p style={{ margin: "0 0 0.5rem 0", color: "var(--success)", fontWeight: "bold", fontSize: "0.85rem" }}>✅ Semilla Regenerada</p>
                        <div style={{ background: "var(--bg)", padding: "0.5rem", borderRadius: "4px", fontFamily: "var(--font-mono)", fontSize: "0.9rem", userSelect: "all" }}>
                            {newGeneratedSeed}
                        </div>
                    </div>
                  )}

                  <form onSubmit={handleUnlock} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                      {unlockMode === "PASSWORD" || unlockMode === "RESET_SEED" ? (
                          <input 
                              type="password" placeholder="Contraseña Maestra..." value={unlockPassword}
                              onChange={(e) => setUnlockPassword(e.target.value)}
                              style={{ width: "100%", padding: "12px", textAlign: "center" }} autoFocus
                          />
                      ) : (
                          <textarea 
                              placeholder="12 Palabras de seguridad separadas por espacio..." value={unlockSeed}
                              onChange={(e) => setUnlockSeed(e.target.value)}
                              style={{ width: "100%", padding: "12px", height: "100px", resize: "none", fontFamily: "var(--font-mono)" }} autoFocus
                          />
                      )}
                      
                      {unlockError && <p style={{ color: unlockMode === "RESET_SEED" && newGeneratedSeed ? "var(--success)" : "var(--danger)", margin: 0, fontSize: "0.85rem" }}>{unlockError}</p>}
                      
                      {(!newGeneratedSeed || unlockMode !== "RESET_SEED") && (
                          <button type="submit" className={unlockMode === "RESET_SEED" ? "danger" : "primary"} style={{ padding: "12px", width: "100%" }} disabled={unlockMode === "SEED" ? !unlockSeed : !unlockPassword}>
                              {unlockMode === "RESET_SEED" ? "Regenerar Semilla y Re-cifrar" : "Desbloquear"}
                          </button>
                      )}

                      {newGeneratedSeed && unlockMode === "RESET_SEED" && (
                          <button type="button" className="primary" onClick={() => { setIsLocked(false); setNewGeneratedSeed(null); setUnlockPassword(""); }} style={{ padding: "12px", width: "100%" }}>
                              He guardado la semilla. Continuar a la Bóveda.
                          </button>
                      )}
                      
                      {currentFilePath && (
                          <button type="button" onClick={() => { setIsLocked(false); handleSaveFlow(); }} style={{ padding: "12px", width: "100%", background: "transparent", color: "var(--accent)", border: "1px solid var(--accent)", marginBottom: "0.5rem" }}>
                              Guardar Cambios
                          </button>
                      )}
                      
                      <button type="button" onClick={onClose} style={{ padding: "12px", width: "100%", background: "transparent", color: "var(--muted)", border: "none" }}>
                          Cerrar Archivo Físicamente
                      </button>
                  </form>
              </motion.div>
          </div>
      )}
      </AnimatePresence>
    </div>
  );
}
