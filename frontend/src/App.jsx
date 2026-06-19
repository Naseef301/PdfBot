import { useEffect, useRef, useState } from "react";
import { Header } from "./components/Header";
import { UploadPanel } from "./components/UploadPanel";
import { ChatPanel } from "./components/ChatPanel";
import { DocumentSidebar } from "./components/DocumentSidebar";
import { Toast } from "./components/Toast";
import { useTheme } from "./hooks/useTheme";
import { API_CONFIG } from "./config/api";
import { askQuestion, getDocumentStatus, uploadPdf } from "./services/ragApi";

const uid = () => `${Date.now()}-${Math.random().toString(16).slice(2)}`;

export default function App() {
  const { theme, toggleTheme } = useTheme();
  const [document, setDocument] = useState(null);
  const [messages, setMessages] = useState([]);
  const [progress, setProgress] = useState(0);
  const [uploadError, setUploadError] = useState("");
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);
  const pollTimer = useRef(null);

  useEffect(() => () => window.clearTimeout(pollTimer.current), []);

  const notify = (message, type = "success") => {
    setToast({ message, type });
    window.setTimeout(() => setToast(null), 4000);
  };

  const pollStatus = async (current) => {
    try {
      const updated = await getDocumentStatus(current);
      setDocument(updated);
      if (updated.status === "ready") {
        notify("Your PDF is indexed and ready.");
        return;
      }
      if (updated.status === "error") throw new Error(updated.message || "Document processing failed.");
      pollTimer.current = window.setTimeout(() => pollStatus(updated), API_CONFIG.pollIntervalMs);
    } catch (error) {
      setDocument((value) => value ? { ...value, status: "error" } : value);
      setUploadError(error.message);
      notify(error.message, "error");
    }
  };

  const handleFile = async (file) => {
    window.clearTimeout(pollTimer.current);
    setMessages([]);
    setUploadError("");
    setProgress(0);

    const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
    if (!isPdf) {
      setUploadError("Please choose a valid PDF file.");
      return;
    }
    if (file.size > API_CONFIG.maxFileSizeMb * 1024 * 1024) {
      setUploadError(`The PDF must be smaller than ${API_CONFIG.maxFileSizeMb} MB.`);
      return;
    }

    setDocument({ name: file.name, size: file.size, status: "uploading" });
    try {
      const uploaded = await uploadPdf(file, setProgress);
      setDocument(uploaded);
      if (uploaded.status === "ready") notify("Your PDF is indexed and ready.");
      else pollStatus(uploaded);
    } catch (error) {
      setDocument({ name: file.name, size: file.size, status: "error" });
      setUploadError(error.message);
      notify(error.message, "error");
    }
  };

  const handleQuestion = async (question) => {
    const userMessage = { id: uid(), role: "user", content: question };
    const history = [...messages, userMessage];
    setMessages(history);
    setLoading(true);
    try {
      const result = await askQuestion({
        question,
        documentId: document.id,
        messages: history,
      });
      setMessages((value) => [
        ...value,
        { id: uid(), role: "assistant", content: result.answer, sources: result.sources, metadata: result.metadata },
      ]);
    } catch (error) {
      notify(error.message, "error");
      setMessages((value) => [
        ...value,
        { id: uid(), role: "assistant", content: `I couldn't complete that request. ${error.message}`, sources: [] },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const resetDocument = () => {
    window.clearTimeout(pollTimer.current);
    setDocument(null);
    setMessages([]);
    setUploadError("");
    setProgress(0);
  };

  const ready = document?.status === "ready";

  return (
    <div className="app-shell">
      <Header theme={theme} onToggleTheme={toggleTheme} />
      <main className="workspace">
        <div className="primary-column">
          {!document || document.status !== "ready" ? (
            <UploadPanel document={document} progress={progress} onFile={handleFile} error={uploadError} />
          ) : (
            <UploadPanel document={document} progress={progress} onFile={handleFile} error={uploadError} compact />
          )}
          <ChatPanel
            messages={messages}
            ready={ready}
            loading={loading}
            onSend={handleQuestion}
            onClear={() => setMessages([])}
            documentName={document?.name}
          />
        </div>
        <DocumentSidebar document={document} onNewPdf={resetDocument} />
      </main>
      <Toast toast={toast} onClose={() => setToast(null)} />
    </div>
  );
}
