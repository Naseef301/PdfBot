import { useRef, useState } from "react";
import { Check, FileText, LoaderCircle, UploadCloud, X } from "lucide-react";
import { API_CONFIG } from "../config/api";
import { formatBytes } from "../utils/format";

export function UploadPanel({ document, progress, onFile, error, compact = false }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  const selectFile = (file) => {
    if (file) onFile(file);
  };

  if (compact && document) {
    return (
      <div className="compact-document">
        <span className="file-icon"><FileText size={20} /></span>
        <span className="compact-document-copy">
          <strong>{document.name}</strong>
          <small>{document.status === "ready" ? "Indexed and ready" : "Processing document"}</small>
        </span>
        <span className={`status-dot ${document.status}`} aria-label={document.status} />
      </div>
    );
  }

  const isWorking = document?.status === "uploading" || document?.status === "processing";
  const isReady = document?.status === "ready";

  return (
    <section className="upload-card" aria-labelledby="upload-title">
      <div className="eyebrow"><span>01</span> Add knowledge</div>
      <h1 id="upload-title">Chat with any PDF.</h1>
      <p>Upload a document and get grounded answers powered by hybrid semantic and keyword retrieval.</p>

      <div
        className={`dropzone ${dragging ? "dragging" : ""} ${error ? "has-error" : ""}`}
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") inputRef.current?.click();
        }}
        onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          selectFile(event.dataTransfer.files?.[0]);
        }}
      >
        <input
          ref={inputRef}
          className="sr-only"
          type="file"
          accept="application/pdf,.pdf"
          onChange={(event) => selectFile(event.target.files?.[0])}
          aria-label="Choose a PDF to upload"
        />
        <span className="upload-icon"><UploadCloud size={26} /></span>
        <strong>Drop your PDF here</strong>
        <span>or <u>browse files</u> from your device</span>
        <small>PDF only, up to {API_CONFIG.maxFileSizeMb} MB</small>
      </div>

      {document && (
        <div className="upload-file-row">
          <span className="file-icon"><FileText size={20} /></span>
          <span className="upload-file-copy">
            <strong>{document.name}</strong>
            <small>{formatBytes(document.size)}</small>
          </span>
          {isWorking && <LoaderCircle className="spin" size={20} />}
          {isReady && <span className="success-icon"><Check size={15} /></span>}
          {document.status === "error" && <X className="error-text" size={20} />}
        </div>
      )}

      {document?.status === "uploading" && (
        <div className="progress-wrap" aria-live="polite">
          <div><span>Uploading document</span><strong>{progress}%</strong></div>
          <progress max="100" value={progress}>{progress}%</progress>
        </div>
      )}

      {document?.status === "processing" && (
        <div className="processing-row" role="status">
          <LoaderCircle className="spin" size={17} />
          <span><strong>Building your knowledge index</strong> — chunking, embedding and ranking.</span>
        </div>
      )}

      {isReady && (
        <div className="ready-row" role="status">
          <Check size={17} /> Your document is indexed and ready to explore.
        </div>
      )}
      {error && <div className="error-row" role="alert">{error}</div>}
    </section>
  );
}
