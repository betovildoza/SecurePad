import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Lock, Info } from "lucide-react";

interface SaveVaultModalProps {
  isOpen: boolean;
  currentFilePath: string | null;
  password: "";
  setPassword: (val: string) => void;
  confirmPassword: "";
  setConfirmPassword: (val: string) => void;
  error: string;
  isSaving: boolean;
  onClose: () => void;
  onSubmit: (e: React.FormEvent) => void;
}

export function SaveVaultModal({
  isOpen, currentFilePath, password, setPassword, confirmPassword, setConfirmPassword,
  error, isSaving, onClose, onSubmit
}: SaveVaultModalProps) {
  return (
    <AnimatePresence>
      {isOpen && (
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

                <form onSubmit={onSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
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
                        <button type="button" onClick={onClose} disabled={isSaving} style={{ padding: "10px 16px", background: "transparent", color: "var(--text)" }}>Cancelar</button>
                        <button type="submit" className="primary" disabled={isSaving || !password} style={{ padding: "10px 16px" }}>
                            {isSaving ? "Cifrando..." : "Cifrar y Guardar"}
                        </button>
                    </div>
                </form>
            </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
