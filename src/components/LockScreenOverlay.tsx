import { FormEvent } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Lock } from "lucide-react";

interface LockScreenOverlayProps {
    isLocked: boolean;
    currentFilePath: string | null;
    unlockMode: "PASSWORD" | "SEED" | "RESET_SEED";
    setUnlockMode: (mode: "PASSWORD" | "SEED" | "RESET_SEED") => void;
    unlockError: string;
    setUnlockError: (err: string) => void;
    unlockPassword: "";
    setUnlockPassword: (val: string) => void;
    unlockSeed: string;
    setUnlockSeed: (val: string) => void;
    newGeneratedSeed: string | null;
    setNewGeneratedSeed: (seed: string | null) => void;
    onUnlockSubmit: (e: FormEvent) => void;
    onClosePhysical: () => void;
    onSaveFlow: () => void;
    onReturnEditor: () => void; // Para archivos sin guardar
}

export function LockScreenOverlay({
    isLocked, currentFilePath, unlockMode, setUnlockMode, unlockError, setUnlockError,
    unlockPassword, setUnlockPassword, unlockSeed, setUnlockSeed,
    newGeneratedSeed, setNewGeneratedSeed, onUnlockSubmit, onClosePhysical, onSaveFlow, onReturnEditor
}: LockScreenOverlayProps) {
  return (
    <AnimatePresence>
      {isLocked && (
          <div style={{
              position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
              background: "rgba(0,0,0,0.85)", zIndex: 1000, 
              display: "flex", alignItems: "center", justifyContent: "center",
              backdropFilter: "blur(4px)"
          }}>
              {!currentFilePath ? (
                  <motion.div 
                     initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}
                     style={{ textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", gap: "1rem" }}
                  >
                      <div style={{ 
                          width: "35vh", height: "35vh", borderRadius: "50%", 
                          background: "var(--panel)", display: "flex", alignItems: "center", justifyContent: "center",
                          border: "1px solid var(--border)", boxShadow: "0 10px 30px rgba(0,0,0,0.3)"
                      }}>
                          <Lock size={"15vh"} color="var(--accent)" />
                      </div>
                      <h2 style={{ color: "white", margin: "1rem 0 0 0", fontSize: "1.5rem" }}>Documento Oculto</h2>
                      <p style={{ color: "var(--muted)", margin: "0", maxWidth: "300px" }}>Este documento aún no ha sido guardado ni cifrado.</p>
                      <button onClick={onReturnEditor} className="primary" style={{ padding: "12px 24px", marginTop: "1rem", fontSize: "1rem" }}>
                          Regresar al Editor
                      </button>
                  </motion.div>
              ) : (
                  <motion.div 
                      initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                      style={{ textAlign: "center", width: "100%", maxWidth: "340px", padding: "2rem", background: "var(--surface)", borderRadius: "12px", boxShadow: "0 10px 40px rgba(0,0,0,0.2)" }}
                  >
                      <div style={{ 
                          width: "64px", height: "64px", borderRadius: "50%", 
                          background: "var(--panel)", display: "flex", alignItems: "center", justifyContent: "center",
                          margin: "0 auto 1.5rem auto", border: "1px solid var(--border)"
                      }}>
                          <Lock size={32} color="var(--accent)" />
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

                  <form onSubmit={onUnlockSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
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
                          <button type="button" className="primary" onClick={() => { onReturnEditor(); setNewGeneratedSeed(null); setUnlockPassword(""); }} style={{ padding: "12px", width: "100%" }}>
                              He guardado la semilla. Continuar a la Bóveda.
                          </button>
                      )}
                      
                      {currentFilePath && (
                          <button type="button" onClick={() => { onReturnEditor(); onSaveFlow(); }} style={{ padding: "12px", width: "100%", background: "transparent", color: "var(--accent)", border: "1px solid var(--accent)", marginBottom: "0.5rem" }}>
                              Guardar Cambios
                          </button>
                      )}
                      
                      <button type="button" onClick={onClosePhysical} style={{ padding: "12px", width: "100%", background: "transparent", color: "var(--danger)", border: "none" }}>
                          Cerrar Archivo Físicamente
                      </button>
                  </form>
                  </motion.div>
              )}
          </div>
      )}
    </AnimatePresence>
  );
}
