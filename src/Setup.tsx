import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Lock, FilePlus, ArrowRight, ShieldCheck, Fingerprint, Settings } from "lucide-react";
import { open } from '@tauri-apps/plugin-dialog';
import { invoke } from "@tauri-apps/api/core";
import { load } from '@tauri-apps/plugin-store';

interface SetupProps {
  onUnlock: (filePath: string) => void;
  onNewVault: () => void;
}

export function Setup({ onUnlock, onNewVault }: SetupProps) {
  const [loading, setLoading] = useState(true);
  const [hasGlobalSeed, setHasGlobalSeed] = useState(false);
  const [showSeedSetup, setShowSeedSetup] = useState(false);
  const [showImportSeed, setShowImportSeed] = useState(false);
  const [newSeed, setNewSeed] = useState<string | null>(null);
  const [importingSeed, setImportingSeed] = useState("");
  const [importError, setImportError] = useState("");
  const [isConfirmingReset, setIsConfirmingReset] = useState(false);

  // Inicialización de la Tienda de Seguridad
  useEffect(() => {
      const initStore = async () => {
          try {
              const store = await load('settings.json');
              const seedVal = await store.get<{ encrypted: string }>('global_seed');
              if (seedVal) {
                  setHasGlobalSeed(true);
              }
          } catch (e) {
              console.error("Error al cargar la tienda Tauri:", e);
          } finally {
              setLoading(false);
          }
      };
      initStore();
  }, []);

  const handleGenerateGlobalSeed = async () => {
      setLoading(true);
      try {
          // Generar una semilla aleatoria nueva desde Rust
          const seed = await invoke<string>("generate_seed");
          setNewSeed(seed);
          
          // Guardar esta semilla temporalmente en la base de datos (Nota: en Producción esto debería cifrarse contra una password maestra de la instancia, 
          // pero como V2 hereda el descifrado desde archivo a archivo, dejamos el flag "true" guardado como constancia de Onboarding completo).
          const store = await load('settings.json');
          await store.set('global_seed', { established: true, phrase: seed }); 
          await store.save();
          
          setHasGlobalSeed(true);
          setShowSeedSetup(true);
      } catch (e) {
          console.error(e);
      } finally {
          setLoading(false);
      }
  };

  const handleImportGlobalSeed = async () => {
      setImportError("");
      if (!importingSeed || importingSeed.split(" ").length !== 12) {
          setImportError("La semilla debe contener exactamente 12 palabras.");
          return;
      }
      setLoading(true);
      try {
          const isValid = await invoke<boolean>("validate_seed", { phrase: importingSeed.trim() });
          if (isValid) {
              const store = await load('settings.json');
              await store.set('global_seed', { established: true, phrase: importingSeed.trim() }); 
              await store.save();
              setHasGlobalSeed(true);
              setShowImportSeed(false);
          } else {
              setImportError("La semilla Bip39 ingresada no es válida.");
          }
      } catch (e) {
          setImportError("Error verificando la semilla.");
      } finally {
          setLoading(false);
      }
  };

  const handleResetGlobalSeed = async () => {
      if(!isConfirmingReset) {
          setIsConfirmingReset(true);
          return;
      }
      if(confirm("Advertencia Crítica: Si regeneras la semilla, perderás el acceso biP39 a todos los archivos anteriores. ¿Estás seguro de sobrescribir tu identidad?")) {
         setIsConfirmingReset(false);
         await handleGenerateGlobalSeed();
      } else {
         setIsConfirmingReset(false);
      }
  };

  const handleOpenExisting = async () => {
    try {
      setLoading(true);
      const file = await open({
        multiple: false,
        directory: false,
        filters: [{
          name: 'SecurePad Vault',
          extensions: ['spd']
        }]
      });
      
      if (file && typeof file === "string") {
        onUnlock(file);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="setup-container"
      style={{
        width: "100%",
        maxWidth: "480px",
        margin: "0 auto",
        padding: "2rem",
        display: "flex",
        flexDirection: "column",
        gap: "1.5rem"
      }}
    >
      <div style={{ textAlign: "center", marginBottom: "1rem" }}>
        <img src="/logo.png" alt="SecurePad Logo" style={{ width: "96px", height: "96px", marginBottom: "1rem" }} />
        <h1 style={{ margin: "0 0 0.5rem 0", fontSize: "1.75rem", fontWeight: "600" }}>SecurePad</h1>
        <p style={{ margin: 0, color: "var(--muted)", display: "flex", alignItems: "center", justifyContent: "center", gap: "0.5rem" }}>
            <ShieldCheck size={16} /> Cifrado AES-256-GCM
        </p>
      </div>

      {loading ? (
          <div style={{ textAlign: "center", color: "var(--muted)" }}>Verificando Seguridad del Equipo...</div>
      ) : showSeedSetup && newSeed ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem", background: "var(--surface)", padding: "1.5rem", borderRadius: "12px", border: "1px solid var(--danger)", boxShadow: "0 4px 24px rgba(0,0,0,0.1)" }}>
              <h3 style={{ margin: "0 0 0.5rem 0", color: "var(--danger)", display: "flex", alignItems: "center", gap: "0.5rem" }}><Fingerprint size={20} /> Identidad Generada</h3>
              <p style={{ margin: 0, fontSize: "0.85rem", lineHeight: "1.4" }}>Esta es tu nueva semilla matriz. A partir de ahora, todas las bóvedas nuevas que crees en este equipo usarán esta semilla como clave de recuperación en caso de que olvides tu Contraseña Maestra.</p>
              
              <div style={{ background: "var(--bg)", padding: "1rem", borderRadius: "8px", fontFamily: "var(--font-mono)", fontSize: "0.95rem", textAlign: "center", border: "1px solid var(--border)", userSelect: "all" }}>
                  {newSeed}
              </div>

              <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--danger)", fontWeight: "bold", textAlign: "center" }}>
                  Escríbela en un papel y guárdalo en un lugar seguro.
              </p>

              <button className="primary" onClick={() => setShowSeedSetup(false)} style={{ padding: "12px", marginTop: "1rem" }}>
                  He guardado las 12 palabras
              </button>
          </div>
      ) : showImportSeed ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem", background: "var(--surface)", padding: "1.5rem", borderRadius: "12px", border: "1px solid var(--border)", boxShadow: "0 4px 24px rgba(0,0,0,0.1)" }}>
              <h3 style={{ margin: "0 0 0.5rem 0", display: "flex", alignItems: "center", gap: "0.5rem" }}><Fingerprint size={20} /> Importar Identidad</h3>
              <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--muted)", lineHeight: "1.4" }}>Pega tus 12 palabras de seguridad para vincular este dispositivo a tus bóvedas existentes.</p>
              
              <textarea 
                  placeholder="palabra1 palabra2 palabra3..." 
                  value={importingSeed}
                  onChange={(e) => setImportingSeed(e.target.value)}
                  style={{ width: "100%", padding: "12px", height: "100px", resize: "none", fontFamily: "var(--font-mono)", fontSize: "0.9rem" }}
                  autoFocus
              />
              
              {importError && <p style={{ color: "var(--danger)", margin: 0, fontSize: "0.85rem" }}>{importError}</p>}

              <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
                  <button onClick={() => setShowImportSeed(false)} style={{ flex: 1, padding: "10px", background: "transparent", border: "1px solid var(--border)", color: "var(--text)" }}>Cancelar</button>
                  <button className="primary" onClick={handleImportGlobalSeed} style={{ flex: 2, padding: "10px" }} disabled={!importingSeed}>
                      Verificar e Importar
                  </button>
              </div>
          </div>
      ) : !hasGlobalSeed ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem", background: "var(--surface)", padding: "1.5rem", borderRadius: "12px", border: "1px solid var(--border)", boxShadow: "0 4px 24px rgba(0,0,0,0.1)" }}>
              <h3 style={{ margin: "0 0 0.5rem 0", display: "flex", alignItems: "center", gap: "0.5rem" }}><ShieldCheck size={20} color="var(--accent)"/> Inicialización Requerida</h3>
              <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--muted)", lineHeight: "1.4" }}>Para usar SecurePad en este dispositivo, primero debemos generar una identidad criptográfica (Semilla BiP39) que protegerá todas tus futuras bóvedas globalmente.</p>
              
              <button 
                  className="primary" 
                  style={{ padding: "12px", fontSize: "1rem", marginTop: "0.5rem" }}
                  onClick={handleGenerateGlobalSeed}
              >
                  <Fingerprint size={20} /> Generar Semilla del Equipo
              </button>

              <button 
                  style={{ padding: "10px", fontSize: "0.9rem", background: "transparent", color: "var(--text)", border: "1px solid var(--border)" }}
                  onClick={() => { setShowImportSeed(true); setImportError(""); setImportingSeed(""); }}
              >
                  Tengo una Semilla (Importar)
              </button>
          </div>
      ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem", background: "var(--surface)", padding: "1.5rem", borderRadius: "12px", border: "1px solid var(--border)", boxShadow: "0 4px 24px rgba(0,0,0,0.1)" }}>
            
            <button 
                className="primary" 
                style={{ padding: "12px", fontSize: "1rem", display: "flex", alignItems: "center", justifyContent: "center", position: "relative" }}
                onClick={onNewVault}
            >
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <FilePlus size={20} /> <span>Crear Nueva Bóveda</span>
                </div>
                <ArrowRight size={20} style={{ position: "absolute", right: "16px" }} />
            </button>

            <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                <hr style={{ flex: 1, border: "none", borderTop: "1px solid var(--border)" }} />
                <span style={{ color: "var(--muted)", fontSize: "0.85rem", textTransform: "uppercase" }}>o</span>
                <hr style={{ flex: 1, border: "none", borderTop: "1px solid var(--border)" }} />
            </div>

            <button 
                style={{ padding: "12px", fontSize: "1rem", display: "flex", alignItems: "center", justifyContent: "flex-start", gap: "0.5rem" }}
                onClick={handleOpenExisting}
            >
                <Lock size={20} /> <span style={{ textAlign: "left" }}>Abrir Bóveda Existente (.spd)</span>
            </button>

            <button 
                style={{ padding: "8px", fontSize: "0.85rem", background: isConfirmingReset ? "var(--danger)" : "transparent", color: isConfirmingReset ? "#fff" : "var(--danger)", border: "1px solid var(--danger)", marginTop: "0.5rem", transition: "all 0.2s" }}
                onClick={handleResetGlobalSeed}
                onMouseLeave={() => setIsConfirmingReset(false)}
            >
                <Settings size={16} style={{ verticalAlign: "middle", marginRight: "4px" }} /> 
                {isConfirmingReset ? "Click de nuevo para confirmar el reset crítico" : "Regenerar Semilla Global de la App"}
            </button>

          </div>
      )}
      
      <p style={{ textAlign: "center", color: "var(--muted)", fontSize: "0.8rem", marginTop: "1rem" }}>
        v2.0.0 • Rust Core
      </p>

    </motion.div>
  );
}
