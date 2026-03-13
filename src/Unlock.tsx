import { useState } from "react";
import { motion } from "framer-motion";
import { Lock, ArrowLeft, KeyRound } from "lucide-react";
import { invoke } from "@tauri-apps/api/core";
import { readFile } from "@tauri-apps/plugin-fs"; // IMPORTANTE: Agregado

interface UnlockProps {
  filePath: string;
  onUnlocked: (content: string) => void;
  onCancel: () => void;
}

export function Unlock({ filePath, onUnlocked, onCancel }: UnlockProps) {
  const [password, setPassword] = useState("");
  const [seedPhrase, setSeedPhrase] = useState("");
  const [unlockMode, setUnlockMode] = useState<"PASSWORD" | "SEED">("PASSWORD");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Extraer solo el nombre del archivo para mostrar
  const fileName = (function() {
      const raw = filePath.split('\\').pop()?.split('/').pop() || filePath;
      try { return decodeURIComponent(raw); } catch { return raw; }
  })();

  const handleUnlock = async (e: React.FormEvent) => {
    e.preventDefault();
    if (unlockMode === "PASSWORD" && !password) return;
    if (unlockMode === "SEED" && !seedPhrase) return;

    setError("");
    setLoading(true);

    try {
      let decryptedContent = "";
      
      // 1. Leer archivo usando API nativa de Tauri en JS (Evita OS error 2 en Android)
      const fileBytes = await readFile(filePath);
      
      // 2. Pasar bytes a Rust
      if (unlockMode === "PASSWORD") {
          decryptedContent = await invoke<string>("decrypt_note", { 
            fileBytes: Array.from(fileBytes), // Convertimos Uint8Array a array simple por seguridad en serialization IPC
            password: password 
          });
      } else {
          decryptedContent = await invoke<string>("decrypt_seed", { 
            fileBytes: Array.from(fileBytes), 
            seedPhrase: seedPhrase.trim() 
          });
      }

      onUnlocked(decryptedContent);
    } catch (err: any) {
      console.error(err);
      setError(typeof err === "string" ? err : "Error al descifrar la bóveda");
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="unlock-container"
      style={{
        width: "100%",
        maxWidth: "400px",
        margin: "0 auto",
        padding: "2rem",
        display: "flex",
        flexDirection: "column",
        gap: "1.5rem"
      }}
    >
      <button 
        style={{ alignSelf: "flex-start", padding: "8px", background: "transparent", border: "none" }} 
        onClick={onCancel}
        disabled={loading}
      >
        <ArrowLeft size={20} />
      </button>

      <div style={{ textAlign: "center", marginBottom: "1rem" }}>
        <div style={{ 
            width: "64px", height: "64px", borderRadius: "50%", 
            background: "var(--panel)", display: "flex", alignItems: "center", justifyContent: "center",
            margin: "0 auto 1rem auto"
        }}>
            <Lock size={32} color="var(--accent)" />
        </div>
        <h2 style={{ margin: "0 0 0.5rem 0" }}>Bóveda Bloqueada</h2>
        <p style={{ margin: 0, color: "var(--muted)", wordBreak: "break-all", fontSize: "0.85rem", marginBottom: "1.5rem" }}>
            {fileName}
        </p>

        <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem", background: "var(--surface)", padding: "4px", borderRadius: "8px", border: "1px solid var(--border)" }}>
            <button 
                type="button"
                style={{ flex: 1, padding: "6px", background: unlockMode === "PASSWORD" ? "var(--panel)" : "transparent", color: unlockMode === "PASSWORD" ? "var(--text)" : "var(--muted)", border: unlockMode === "PASSWORD" ? "1px solid var(--border)" : "none", borderRadius: "6px" }}
                onClick={() => { setUnlockMode("PASSWORD"); setError(""); }}
            >
                Contraseña
            </button>
            <button 
                type="button"
                style={{ flex: 1, padding: "6px", background: unlockMode === "SEED" ? "var(--panel)" : "transparent", color: unlockMode === "SEED" ? "var(--text)" : "var(--muted)", border: unlockMode === "SEED" ? "1px solid var(--border)" : "none", borderRadius: "6px" }}
                onClick={() => { setUnlockMode("SEED"); setError(""); }}
            >
                Semilla BiP39
            </button>
        </div>
      </div>

      <form onSubmit={handleUnlock} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        
        {unlockMode === "PASSWORD" ? (
            <div style={{ position: "relative" }}>
                <KeyRound size={18} style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)", color: "var(--muted)" }} />
                <input 
                    type="password" 
                    placeholder="Contraseña Maestra..." 
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    style={{ width: "100%", paddingLeft: "38px", paddingBottom: "10px", paddingTop: "10px" }}
                    autoFocus
                    disabled={loading}
                />
            </div>
        ) : (
            <textarea 
                placeholder="Ingresa las 12 palabras de recuperación..." 
                value={seedPhrase}
                onChange={(e) => setSeedPhrase(e.target.value)}
                style={{ width: "100%", padding: "12px", height: "100px", resize: "none", fontFamily: "var(--font-mono)" }} 
                autoFocus
                disabled={loading}
            />
        )}

        {error && (
            <motion.p 
                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                style={{ color: "var(--danger)", margin: 0, fontSize: "0.85rem", textAlign: "center" }}
            >
                {error}
            </motion.p>
        )}

        <button 
            type="submit" 
            className="primary" 
            disabled={loading || (unlockMode === "PASSWORD" ? !password : !seedPhrase)}
            style={{ padding: "12px", marginTop: "0.5rem", fontWeight: "bold" }}
        >
            {loading ? "Descifrando..." : "Desbloquear Bóveda"}
        </button>
      </form>
    </motion.div>
  );
}
