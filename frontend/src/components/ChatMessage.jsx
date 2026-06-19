import { useState } from "react";
import { Bot, Check, Copy, User } from "lucide-react";
import { Sources } from "./Sources";
import { formatAnswer } from "../utils/format";

export function ChatMessage({ message }) {
  const [copied, setCopied] = useState(false);
  const isAssistant = message.role === "assistant";

  const copy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  return (
    <article className={`message ${message.role}`}>
      <span className="avatar">{isAssistant ? <Bot size={18} /> : <User size={17} />}</span>
      <div className="message-main">
        <div className="message-heading">
          <strong>{isAssistant ? "Pdf Assistant" : "You"}</strong>
          {isAssistant && (
            <button type="button" onClick={copy} aria-label="Copy answer">
              {copied ? <Check size={15} /> : <Copy size={15} />}
              <span>{copied ? "Copied" : "Copy"}</span>
            </button>
          )}
        </div>
        <div className="message-content">
          {formatAnswer(message.content).map((line, index) => <p key={index}>{line}</p>)}
        </div>
        {isAssistant && <Sources sources={message.sources} />}
      </div>
    </article>
  );
}
