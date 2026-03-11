import { motion, AnimatePresence } from "framer-motion";
import { Settings, X } from "lucide-react";

interface SettingsModalProps {
  isOpen: boolean;
  theme: "dark" | "light";
  setTheme: (theme: "dark" | "light") => void;
  fontFamily: string;
  setFontFamily: (font: string) => void;
  fontSize: number;
  setFontSize: (size: number) => void;
  wordWrap: boolean;
  setWordWrap: (wrap: boolean) => void;
  fontOptions: { label: string, value: string }[];
  onClose: () => void;
}

export function SettingsModal({
  isOpen, theme, setTheme, fontFamily, setFontFamily, fontSize, setFontSize,
  wordWrap, setWordWrap, fontOptions, onClose
}: SettingsModalProps) {
  return (
    <AnimatePresence>
      {isOpen && (
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
                <button className="icon-btn" onClick={onClose} style={{ position: "absolute", top: "16px", right: "16px" }}>
                    <X size={20} />
                </button>

                <h3 style={{ margin: "0 0 1rem 0", fontSize: "1.25rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <Settings size={22} /> Ajustes del Documento
                </h3>
                
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
  );
}
