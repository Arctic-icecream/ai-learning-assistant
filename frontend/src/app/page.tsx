"use client";

import { useEffect, useState } from "react";

type HealthState = {
  status: "idle" | "loading" | "success" | "error";
  message: string;
};

type UploadedDocument = {
  id: number;
  filename: string;
  content_type: string;
  size_bytes: number;
  parse_status: string;
  text_char_count: number;
  parse_error: string | null;
  chunk_count: number;
};

type UploadState = {
  status: "idle" | "loading" | "success" | "error";
  message: string;
  document?: UploadedDocument;
};

type DocumentRecord = {
  id: number;
  filename: string;
  content_type: string;
  size_bytes: number;
  parse_status: string;
  text_char_count: number;
  parse_error: string | null;
  chunk_count: number;
  created_at: string;
};

type DocumentChunk = {
  id: number;
  document_id: number;
  chunk_index: number;
  content: string;
  char_count: number;
};

export default function Home() {
  const [health, setHealth] = useState<HealthState>({
    status: "idle",
    message: "Backend has not been checked yet."
  });
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [upload, setUpload] = useState<UploadState>({
    status: "idle",
    message: "No file uploaded yet."
  });
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [documentsMessage, setDocumentsMessage] = useState(
    "Document list has not been loaded yet."
  );
  const [selectedDocument, setSelectedDocument] = useState<DocumentRecord | null>(
    null
  );
  const [chunks, setChunks] = useState<DocumentChunk[]>([]);
  const [chunksMessage, setChunksMessage] = useState(
    "Select a document to preview chunks."
  );

  useEffect(() => {
    void loadDocuments();
  }, []);

  async function checkBackend() {
    setHealth({
      status: "loading",
      message: "Checking backend..."
    });

    try {
      const response = await fetch("http://127.0.0.1:8000/health");

      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`);
      }

      const data = (await response.json()) as { status: string };

      setHealth({
        status: "success",
        message: data.status
      });
    } catch (error) {
      setHealth({
        status: "error",
        message:
          error instanceof Error
            ? error.message
            : "Could not connect to the backend."
      });
    }
  }

  async function uploadDocument() {
    if (!selectedFile) {
      setUpload({
        status: "error",
        message: "Please choose a file first."
      });
      return;
    }

    setUpload({
      status: "loading",
      message: "Uploading document..."
    });

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await fetch("http://127.0.0.1:8000/documents/upload", {
        method: "POST",
        body: formData
      });

      if (!response.ok) {
        throw new Error(`Upload failed with ${response.status}`);
      }

      const data = (await response.json()) as UploadedDocument;

      setUpload({
        status: "success",
        message: "Document uploaded and saved to the database.",
        document: data
      });
      await loadDocuments();
      await loadChunks(data.id);
    } catch (error) {
      setUpload({
        status: "error",
        message:
          error instanceof Error ? error.message : "Could not upload document."
      });
    }
  }

  async function loadDocuments() {
    setDocumentsMessage("Loading documents from the database...");

    try {
      const response = await fetch("http://127.0.0.1:8000/documents");

      if (!response.ok) {
        throw new Error(`Document list failed with ${response.status}`);
      }

      const data = (await response.json()) as DocumentRecord[];
      setDocuments(data);
      setDocumentsMessage(
        data.length === 0
          ? "No documents are stored yet."
          : `${data.length} document record${data.length === 1 ? "" : "s"} stored.`
      );
    } catch (error) {
      setDocumentsMessage(
        error instanceof Error ? error.message : "Could not load documents."
      );
    }
  }

  async function loadChunks(documentId: number) {
    setChunksMessage("Loading chunks...");

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/documents/${documentId}/chunks`
      );

      if (!response.ok) {
        throw new Error(`Chunk list failed with ${response.status}`);
      }

      const data = (await response.json()) as DocumentChunk[];
      setChunks(data);
      setChunksMessage(
        data.length === 0
          ? "No chunks stored for this document."
          : `${data.length} chunk${data.length === 1 ? "" : "s"} stored.`
      );
    } catch (error) {
      setChunksMessage(
        error instanceof Error ? error.message : "Could not load chunks."
      );
    }
  }

  async function selectDocument(document: DocumentRecord) {
    setSelectedDocument(document);
    await loadChunks(document.id);
  }

  return (
    <main className="shell">
      <section className="hero">
        <p className="eyebrow">Day 5 chunking</p>
        <h1>AI Learning Assistant</h1>
        <p className="summary">
          Upload learning materials, build a knowledge base, and ask questions
          with AI. Let's get started!
        </p>
        <div className="health-panel">
          <button
            className="primary-button"
            disabled={health.status === "loading"}
            onClick={checkBackend}
            type="button"
          >
            {health.status === "loading" ? "Checking..." : "Check Backend"}
          </button>
          <p className={`health-message ${health.status}`}>
            Backend status: {health.message}
          </p>
        </div>
        <div className="upload-panel">
          <label className="file-label" htmlFor="document-upload">
            Choose study material
          </label>
          <input
            id="document-upload"
            onChange={(event) =>
              setSelectedFile(event.target.files?.[0] ?? null)
            }
            type="file"
          />
          <button
            className="primary-button"
            disabled={upload.status === "loading"}
            onClick={uploadDocument}
            type="button"
          >
            {upload.status === "loading" ? "Uploading..." : "Upload File"}
          </button>
          <p className={`health-message ${upload.status}`}>{upload.message}</p>
          {upload.document ? (
            <dl className="upload-result">
              <div>
                <dt>Database ID</dt>
                <dd>{upload.document.id}</dd>
              </div>
              <div>
                <dt>Filename</dt>
                <dd>{upload.document.filename}</dd>
              </div>
              <div>
                <dt>Content type</dt>
                <dd>{upload.document.content_type}</dd>
              </div>
              <div>
                <dt>Size</dt>
                <dd>{upload.document.size_bytes} bytes</dd>
              </div>
              <div>
                <dt>Parse status</dt>
                <dd>{upload.document.parse_status}</dd>
              </div>
              <div>
                <dt>Text chars</dt>
                <dd>{upload.document.text_char_count}</dd>
              </div>
              <div>
                <dt>Chunks</dt>
                <dd>{upload.document.chunk_count}</dd>
              </div>
              {upload.document.parse_error ? (
                <div>
                  <dt>Parse error</dt>
                  <dd>{upload.document.parse_error}</dd>
                </div>
              ) : null}
            </dl>
          ) : null}
        </div>
        <div className="documents-panel">
          <div className="documents-heading">
            <h2>Stored documents</h2>
            <button className="secondary-button" onClick={loadDocuments} type="button">
              Refresh
            </button>
          </div>
          <p className="health-message">{documentsMessage}</p>
          {documents.length > 0 ? (
            <ul className="documents-list">
              {documents.map((document) => (
                <li key={document.id}>
                  <span className="document-name">{document.filename}</span>
                  <span>{document.content_type}</span>
                  <span>{document.size_bytes} bytes</span>
                  <span className={`parse-status ${document.parse_status}`}>
                    {document.parse_status}
                  </span>
                  <span>{document.text_char_count} chars</span>
                  <button
                    className="link-button"
                    onClick={() => void selectDocument(document)}
                    type="button"
                  >
                    {document.chunk_count} chunks
                  </button>
                  <span>{new Date(document.created_at).toLocaleString()}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
        <div className="chunks-panel">
          <h2>
            Chunk preview
            {selectedDocument ? `: ${selectedDocument.filename}` : ""}
          </h2>
          <p className="health-message">{chunksMessage}</p>
          {chunks.length > 0 ? (
            <ol className="chunks-list">
              {chunks.slice(0, 5).map((chunk) => (
                <li key={chunk.id}>
                  <div className="chunk-meta">
                    Chunk {chunk.chunk_index + 1} · {chunk.char_count} chars
                  </div>
                  <p>{chunk.content.slice(0, 420)}</p>
                </li>
              ))}
            </ol>
          ) : null}
        </div>
      </section>
    </main>
  );
}
