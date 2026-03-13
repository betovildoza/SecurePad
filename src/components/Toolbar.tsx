import { Save, Lock, FilePlus, FolderOpen, Settings } from "lucide-react";

interface ToolbarProps {
  currentFilePath: string | null;
  onNewVault: () => void;
  onOpenLocal: () => void;
  onSaveFlow: () => void;
  onToggleSettings: () => void;
  onClose: () => void;
}

export function Toolbar({ currentFilePath, onNewVault, onOpenLocal, onSaveFlow, onToggleSettings, onClose }: ToolbarProps) {
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 600;
  const fileName = currentFilePath ? (function() {
      const raw = currentFilePath.split('\\').pop()?.split('/').pop() || "Sin título.spd";
      try { return decodeURIComponent(raw); } catch { return raw; }
  })() : "Sin título.spd";

  return (
    <div style={{ 
      display: "flex", flexDirection: "column", 
      background: "var(--panel)", borderBottom: "1px solid var(--border)",
      boxShadow: "0 2px 10px rgba(0,0,0,0.05)", zIndex: 10
    }}>
      {/* Barra superior de título en móvil */}
      {isMobile && (
        <div style={{ 
            background: "black", color: "white", textAlign: "center", 
            paddingTop: "calc(0.25rem + env(safe-area-inset-top, 0px))", paddingBottom: "0.25rem",
            fontSize: "0.8rem", width: "100%"
        }}>
          {fileName}
        </div>
      )}

      {/* Toolbar Principal */}
      <div style={{ 
        display: "flex", alignItems: "center", justifyContent: "space-between", 
        padding: isMobile ? "0.5rem 1rem" : "calc(0.5rem + env(safe-area-inset-top, 0px)) 1rem 0.5rem 1rem"
      }}>
        {/* Lado Izquierdo */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--muted)", fontSize: "0.85rem", fontWeight: "bold" }}>
          SecurePad Editor
        </div>
          
      {/* Lado Derecho (Botones de Acción y Configuración) */}
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <button className="icon-btn" title="Nueva Bóveda" onClick={onNewVault}>
              <FilePlus size={20} />
          </button>
          <button className="icon-btn" title="Abrir Bóveda" onClick={onOpenLocal}>
              <FolderOpen size={20} />
          </button>
          <button className="icon-btn" title="Guardar" onClick={onSaveFlow}>
              <Save size={20} />
          </button>
          
          <div style={{ width: "1px", height: "24px", background: "var(--border)", margin: "0 4px" }} />

          <button className="icon-btn" title="Ajustes (Alt+Z = Word Wrap)" onClick={onToggleSettings}>
              <Settings size={20} />
          </button>

          <div style={{ width: "1px", height: "24px", background: "var(--border)", margin: "0 4px" }} />

          <button className="icon-btn danger" title="Cerrar y Bloquear Bóveda" onClick={onClose} style={{ marginLeft: "0.25rem" }}>
              <Lock size={20} color="var(--bg)" />
          </button>
      </div>
      </div>
    </div>
  );
}
