import { API_CONFIG, apiUrl } from "../config/api";

function getFirst(object, keys, fallback = undefined) {
  for (const key of keys) {
    if (object?.[key] !== undefined && object[key] !== null) return object[key];
  }
  return fallback;
}

async function parseResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json")
    ? await response.json()
    : { message: await response.text() };

  if (!response.ok) {
    throw new Error(
      getFirst(body, ["detail", "error", "message"], `Request failed (${response.status})`),
    );
  }
  return body;
}

export function normalizeStatus(value) {
  const status = String(value || "").toLowerCase();
  if (["ready", "complete", "completed", "indexed", "success"].includes(status)) {
    return "ready";
  }
  if (["failed", "error"].includes(status)) return "error";
  return "processing";
}

function normalizeDocument(data, file) {
  const nested = data.document || data.data || {};
  const id = getFirst(data, ["document_id", "documentId", "session_id", "sessionId", "id"])
    ?? getFirst(nested, ["document_id", "documentId", "session_id", "sessionId", "id"]);

  if (!id) {
    throw new Error("Upload succeeded, but the backend did not return a document or session ID.");
  }

  const rawStatus = getFirst(data, ["status", "state"], getFirst(nested, ["status", "state"]));
  return {
    id: String(id),
    name: getFirst(nested, ["name", "filename", "file_name"], file?.name || "Uploaded PDF"),
    size: getFirst(nested, ["size", "file_size"], file?.size || 0),
    pages: getFirst(nested, ["pages", "page_count", "pageCount"]),
    chunks: getFirst(nested, ["chunks", "chunk_count", "chunkCount"]),
    status: normalizeStatus(rawStatus || (data.ready === true ? "ready" : "processing")),
    message: getFirst(data, ["message", "detail"]),
    metadata: getFirst(data, ["metadata"], getFirst(nested, ["metadata"], {})),
  };
}

export function uploadPdf(file, onProgress) {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append("file", file);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", apiUrl(API_CONFIG.uploadEndpoint));
    xhr.responseType = "json";

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress?.(Math.round((event.loaded / event.total) * 100));
    };

    xhr.onerror = () => reject(new Error("Could not reach the backend. Check the API URL and CORS settings."));
    xhr.onload = () => {
      const body = xhr.response || {};
      if (xhr.status < 200 || xhr.status >= 300) {
        reject(new Error(getFirst(body, ["detail", "error", "message"], `Upload failed (${xhr.status})`)));
        return;
      }
      try {
        resolve(normalizeDocument(body, file));
      } catch (error) {
        reject(error);
      }
    };
    xhr.send(formData);
  });
}

export async function getDocumentStatus(document) {
  const endpoint = API_CONFIG.statusEndpoint.replace(":documentId", encodeURIComponent(document.id));
  const data = await fetch(apiUrl(endpoint)).then(parseResponse);
  return {
    ...document,
    ...normalizeDocument({ document_id: document.id, ...data }, document),
  };
}

function normalizeSources(data) {
  const sources = getFirst(data, ["sources", "citations", "references"], []);
  if (!Array.isArray(sources)) return [];

  return sources.map((source, index) => {
    if (typeof source === "string") {
      return { id: `${index}-${source}`, source, page: null, text: "" };
    }
    return {
      id: String(source.id ?? `${index}-${source.source || source.file || "source"}`),
      source: getFirst(source, ["source", "filename", "file", "document"], "Uploaded PDF"),
      page: getFirst(source, ["page", "page_number", "pageNumber"]),
      text: getFirst(source, ["text", "content", "chunk", "snippet"], ""),
      score: getFirst(source, ["score", "relevance_score", "relevanceScore"]),
    };
  });
}

export async function askQuestion({ question, documentId, messages }) {
  const response = await fetch(apiUrl(API_CONFIG.queryEndpoint), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      document_id: documentId,
      session_id: documentId,
      history: messages.map(({ role, content }) => ({ role, content })),
    }),
  });
  const data = await parseResponse(response);
  const answer = getFirst(data, ["answer", "response", "message"], getFirst(data.data, ["answer", "response"]));

  if (typeof answer !== "string" || !answer.trim()) {
    throw new Error("The backend returned no answer.");
  }

  return {
    answer: answer.trim(),
    sources: normalizeSources(data),
    metadata: getFirst(data, ["metadata", "meta"], {}),
  };
}
