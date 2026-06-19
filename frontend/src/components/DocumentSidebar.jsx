import { BookOpen, FileText, Layers3, Plus, ShieldCheck } from "lucide-react";
import { formatBytes } from "../utils/format";

export function DocumentSidebar({ document, onNewPdf }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-heading">
        <span>Document</span>
        {document && <button type="button" onClick={onNewPdf}><Plus size={15} /> New PDF</button>}
      </div>

      {document ? (
        <>
          <div className="document-preview">
            <div className="paper">
              <FileText size={31} />
              <span>PDF</span>
            </div>
            <strong title={document.name}>{document.name}</strong>
            <small>{formatBytes(document.size)}</small>
          </div>
          <dl className="document-stats">
            <div><dt><ShieldCheck size={16} /> Status</dt><dd className={document.status}>{document.status}</dd></div>
            {document.pages != null && <div><dt><BookOpen size={16} /> Pages</dt><dd>{document.pages}</dd></div>}
            {document.chunks != null && <div><dt><Layers3 size={16} /> Chunks</dt><dd>{document.chunks}</dd></div>}
            <div><dt><Layers3 size={16} /> Retrieval</dt><dd>Hybrid</dd></div>
          </dl>
        </>
      ) : (
        <div className="sidebar-empty">
          <FileText size={26} />
          <p>Document details and retrieval metadata will appear here.</p>
        </div>
      )}

      <div className="privacy-note">
        <ShieldCheck size={17} />
        <span><strong>Grounded answers</strong>Your assistant responds from retrieved PDF context.</span>
      </div>
    </aside>
  );
}
