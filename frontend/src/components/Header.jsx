import { FileSearch2, Moon, Sun } from "lucide-react";

export function Header({ theme, onToggleTheme }) {
  return (
    <header className="topbar">
      <a className="brand" href="/" aria-label="PDF RAG Assistant home">
        <span className="brand-mark"><FileSearch2 size={20} /></span>
        <span>
          <strong>PDF</strong>
          <small>Assistant</small>
        </span>
      </a>
      <div className="topbar-actions">
        <span className="engine-badge"><i /> Hybrid retrieval</span>
        <button className="icon-button" type="button" onClick={onToggleTheme} aria-label={`Use ${theme === "dark" ? "light" : "dark"} mode`}>
          {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
        </button>
      </div>
    </header>
  );
}
