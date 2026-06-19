import { useEffect, useRef, useState } from "react";
import { ArrowUp, LoaderCircle, MessageSquareText, Sparkles, Trash2 } from "lucide-react";
import { ChatMessage } from "./ChatMessage";

const SUGGESTIONS = [
  "Summarize the key ideas in this document",
  "What are the most important takeaways?",
  "List the main topics covered",
];

export function ChatPanel({ messages, ready, loading, onSend, onClear, documentName }) {
  const [question, setQuestion] = useState("");
  const endRef = useRef(null);

  useEffect(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), [messages, loading]);

  const submit = (value = question) => {
    const clean = value.trim();
    if (!clean || !ready || loading) return;
    onSend(clean);
    setQuestion("");
  };

  return (
    <section className="chat-card" aria-label="Document chat">
      <div className="chat-header">
        <div>
          <span className="chat-status"><i className={ready ? "ready" : ""} /> {ready ? "Ready to answer" : "Waiting for document"}</span>
          <h2>{documentName ? "Ask your document" : "Document conversation"}</h2>
        </div>
        {messages.length > 0 && (
          <button className="text-button" type="button" onClick={onClear}>
            <Trash2 size={15} /> Clear chat
          </button>
        )}
      </div>

      <div className="messages" aria-live="polite">
        {!messages.length && (
          <div className="empty-chat">
            <span><MessageSquareText size={27} /></span>
            <h3>{ready ? "Your document is ready" : "Start with a PDF"}</h3>
            <p>{ready ? "Ask a question or try one of these prompts." : "Upload and index a PDF to begin a grounded conversation."}</p>
            {ready && (
              <div className="suggestions">
                {SUGGESTIONS.map((suggestion) => (
                  <button key={suggestion} type="button" onClick={() => submit(suggestion)}>
                    <Sparkles size={14} /> {suggestion}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
        {messages.map((message) => <ChatMessage key={message.id} message={message} />)}
        {loading && (
          <div className="thinking" role="status">
            <span className="avatar"><LoaderCircle className="spin" size={18} /></span>
            <div><strong>Searching your document</strong><span className="typing"><i /><i /><i /></span></div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="composer-wrap">
        <div className={`composer ${!ready ? "disabled" : ""}`}>
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                submit();
              }
            }}
            rows="1"
            disabled={!ready || loading}
            aria-label="Ask a question about your PDF"
            placeholder={ready ? "Ask anything about your PDF..." : "Upload a PDF to start asking questions"}
          />
          <button type="button" onClick={() => submit()} disabled={!ready || loading || !question.trim()} aria-label="Send question">
            <ArrowUp size={19} />
          </button>
        </div>
        <small>Press Enter to send · Shift + Enter for a new line</small>
      </div>
    </section>
  );
}
