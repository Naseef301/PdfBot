import { ChevronDown, FileText } from "lucide-react";

export function Sources({ sources }) {
  if (!sources?.length) return null;

  return (
    <details className="sources">
      <summary>
        <span><FileText size={15} /> {sources.length} source{sources.length > 1 ? "s" : ""}</span>
        <ChevronDown size={16} />
      </summary>
      <div className="source-list">
        {sources.map((source, index) => (
          <article className="source-item" key={source.id}>
            <div>
              <span className="source-number">{index + 1}</span>
              <strong>{source.source?.split(/[\\/]/).pop()}</strong>
              {source.page != null && <small>Page {source.page}</small>}
            </div>
            {source.text && <p>{source.text}</p>}
          </article>
        ))}
      </div>
    </details>
  );
}
