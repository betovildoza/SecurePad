import { useEffect, useState } from "react";
import "./App.css";
import { Setup } from "./Setup";
import { Unlock } from "./Unlock";
import { Editor } from "./Editor";

export type AppState = "LOADING" | "SETUP" | "LOCKED" | "EDITOR";

function App() {
  const [appState, setAppState] = useState<AppState>("LOADING");
  const [filePath, setFilePath] = useState<string | null>(null);
  const [editorContent, setEditorContent] = useState<string>("");

  useEffect(() => {
    // Detect system theme preference
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const applyTheme = (e: MediaQueryListEvent | MediaQueryList) => {
      document.documentElement.setAttribute("data-theme", e.matches ? "dark" : "light");
    };
    applyTheme(mediaQuery);
    mediaQuery.addEventListener("change", applyTheme);
    
    // Simulate loading/checking config
    setTimeout(() => {
        setAppState("SETUP"); // Starting at setup for now as default
    }, 500);

    return () => mediaQuery.removeEventListener("change", applyTheme);
  }, []);

  const handleUnlockFile = (file: string) => {
    setFilePath(file);
    setAppState("LOCKED");
  };

  const handleUnlockedContent = (content: string) => {
    setEditorContent(content);
    setAppState("EDITOR");
  };

  const handleNewVault = () => {
    setFilePath(null);
    setEditorContent("");
    setAppState("EDITOR");
  };

  return (
    <main className="app-container" style={{ width: "100%", height: "100vh", display: "flex", flexDirection: "column" }}>
      {appState === "LOADING" && (
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <h2>Cargando SecurePad...</h2>
        </div>
      )}
      
      {appState === "SETUP" && (
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Setup 
                onUnlock={handleUnlockFile} 
                onNewVault={handleNewVault} 
            />
        </div>
      )}

      {appState === "LOCKED" && filePath && (
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
             <Unlock 
                filePath={filePath} 
                onUnlocked={handleUnlockedContent} 
                onCancel={() => setAppState("SETUP")} 
             />
        </div>
      )}

      {appState === "EDITOR" && (
        <Editor 
            initialContent={editorContent}
            filePath={filePath}
            onClose={() => { setAppState("SETUP"); setFilePath(null); setEditorContent(""); }}
            onNewVault={handleNewVault}
            onOpenVault={handleUnlockFile}
        />
      )}
    </main>
  );
}

export default App;
