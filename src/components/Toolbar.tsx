import { Save, Lock, FilePlus, FolderOpen, Settings } from "lucide-react";

interface ToolbarProps {
  onNewVault: () => void;
  onOpenLocal: () => void;
  onSaveFlow: () => void;
  onToggleSettings: () => void;
  onClose: () => void;
}

export function Toolbar({ onNewVault, onOpenLocal, onSaveFlow, onToggleSettings, onClose }: ToolbarProps) {
  return (
    <div style={{ 
      display: "flex", alignItems: "center", justifyContent: "space-between", 
      padding: "calc(0.5rem + env(safe-area-inset-top, 0px)) 1rem 0.5rem 1rem", background: "var(--panel)", borderBottom: "1px solid var(--border)",
      boxShadow: "0 2px 10px rgba(0,0,0,0.05)", zIndex: 10
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
  );
}
