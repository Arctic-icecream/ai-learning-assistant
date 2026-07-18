"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Trash2, X } from "lucide-react";
import ReactMarkdown from "react-markdown";
import type { MindMapTree } from "@/components/MindMapView";

const MindMapView = dynamic(() => import("@/components/MindMapView"), {
  ssr: false,
  loading: () => <p className="health-message">Loading mind map canvas...</p>
});

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
  embedded_count: number;
  source_type: string;
  source_url: string | null;
  page_count: number;
  ocr_used: boolean;
  ocr_page_count: number;
  ocr_error: string | null;
  created_at: string;
};

type UploadState = {
  status: "idle" | "loading" | "success" | "error";
  message: string;
  document?: UploadedDocument;
  job?: ProcessingJob;
};

type ProcessingJob = {
  id: number;
  document_id: number;
  job_type: string;
  status: "queued" | "running" | "completed" | "failed";
  stage: string;
  message: string;
  progress_current: number;
  progress_total: number;
  percent: number;
  error: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
};

type ProcessingJobResponse = {
  document: UploadedDocument;
  job: ProcessingJob;
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
  embedded_count: number;
  source_type: string;
  source_url: string | null;
  page_count: number;
  ocr_used: boolean;
  ocr_page_count: number;
  ocr_error: string | null;
  created_at: string;
};

type DocumentChunk = {
  id: number;
  document_id: number;
  chunk_index: number;
  content: string;
  char_count: number;
  embedding_status: string;
  embedding_error: string | null;
};

type SearchResult = {
  chunk_id: number;
  document_id: number;
  filename: string;
  chunk_index: number;
  content: string;
  char_count: number;
  distance: number;
};

type ChatSession = {
  id: number;
  document_id: number;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
};

type ChatMessage = {
  id: number;
  session_id: number;
  role: "user" | "assistant";
  content: string;
  sources: SearchResult[];
  created_at: string;
};

type AnswerState = {
  status: "idle" | "loading" | "success" | "error";
  message: string;
  answer: string;
  sources: SearchResult[];
};

type Flashcard = {
  id: number;
  document_id: number;
  question: string;
  answer: string;
  source_chunk_index: number | null;
  created_at: string;
};

type QuizQuestion = {
  id: number;
  document_id: number;
  question_type: string;
  question: string;
  choices: string[];
  correct_answer: string;
  explanation: string;
  created_at: string;
};

type QuizResponse = {
  question_id: number;
  submitted_answer: string;
  is_correct: boolean | null;
};

type QuizAttempt = {
  id: number;
  document_id: number;
  total_questions: number;
  scored_questions: number;
  correct_answers: number;
  created_at: string;
  responses: QuizResponse[];
};

type SummaryMode = "brief" | "detailed";

type DocumentSummary = {
  id: number;
  document_id: number;
  mode: SummaryMode;
  content: string;
  model_name: string;
  source_chunk_count: number;
  model_call_count: number;
  created_at: string;
};

type DocumentMindMap = {
  id: number;
  document_id: number;
  summary_id: number;
  tree: MindMapTree;
  model_name: string;
  node_count: number;
  created_at: string;
};

type StorageStats = {
  document_count: number;
  tracked_file_bytes: number;
  actual_upload_bytes: number;
  orphan_file_count: number;
  chunk_count: number;
  embedded_chunk_count: number;
  summary_count: number;
  mind_map_count: number;
  flashcard_count: number;
  quiz_question_count: number;
  quiz_attempt_count: number;
  processing_job_count: number;
  chat_session_count: number;
  chat_message_count: number;
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

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
  const [webUrl, setWebUrl] = useState("");
  const [webImport, setWebImport] = useState<UploadState>({
    status: "idle",
    message: "No web page imported yet."
  });
  const [activeJobs, setActiveJobs] = useState<Record<number, ProcessingJob>>({});
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [documentsMessage, setDocumentsMessage] = useState(
    "Document list has not been loaded yet."
  );
  const [reprocessingId, setReprocessingId] = useState<number | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<DocumentRecord | null>(
    null
  );
  const [chunks, setChunks] = useState<DocumentChunk[]>([]);
  const [chunksMessage, setChunksMessage] = useState(
    "Select a document to preview chunks."
  );
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searchMessage, setSearchMessage] = useState(
    "Search your uploaded materials."
  );
  const [answer, setAnswer] = useState<AnswerState>({
    status: "idle",
    message: "Generate an answer after entering a question.",
    answer: "",
    sources: []
  });
  const [chatDocument, setChatDocument] = useState<DocumentRecord | null>(null);
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [activeChatSession, setActiveChatSession] =
    useState<ChatSession | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatMessage, setChatMessage] = useState(
    "Select a parsed document to start a study chat."
  );
  const [creatingChatSession, setCreatingChatSession] = useState(false);
  const [sendingChatMessage, setSendingChatMessage] = useState(false);
  const [flashcards, setFlashcards] = useState<Flashcard[]>([]);
  const [flashcardsMessage, setFlashcardsMessage] = useState(
    "Select a document to view flashcards."
  );
  const [flashcardDocument, setFlashcardDocument] =
    useState<DocumentRecord | null>(null);
  const [generatingCardsId, setGeneratingCardsId] = useState<number | null>(null);
  const [flippedCardIds, setFlippedCardIds] = useState<number[]>([]);
  const [quizQuestions, setQuizQuestions] = useState<QuizQuestion[]>([]);
  const [quizMessage, setQuizMessage] = useState(
    "Select a document to view quiz questions."
  );
  const [quizDocument, setQuizDocument] = useState<DocumentRecord | null>(null);
  const [generatingQuizId, setGeneratingQuizId] = useState<number | null>(null);
  const [revealedQuizIds, setRevealedQuizIds] = useState<number[]>([]);
  const [quizAnswers, setQuizAnswers] = useState<Record<number, string>>({});
  const [submittingQuiz, setSubmittingQuiz] = useState(false);
  const [quizAttempts, setQuizAttempts] = useState<QuizAttempt[]>([]);
  const [summaries, setSummaries] = useState<DocumentSummary[]>([]);
  const [summaryMessage, setSummaryMessage] = useState(
    "Select a document to view saved summaries."
  );
  const [summaryDocument, setSummaryDocument] =
    useState<DocumentRecord | null>(null);
  const [summaryMode, setSummaryMode] = useState<SummaryMode>("brief");
  const [generatingSummaryId, setGeneratingSummaryId] = useState<number | null>(
    null
  );
  const [mindMaps, setMindMaps] = useState<DocumentMindMap[]>([]);
  const [mindMapMessage, setMindMapMessage] = useState(
    "Select a document to view saved mind maps."
  );
  const [mindMapDocument, setMindMapDocument] =
    useState<DocumentRecord | null>(null);
  const [activeMindMapId, setActiveMindMapId] = useState<number | null>(null);
  const [generatingMindMapId, setGeneratingMindMapId] = useState<number | null>(
    null
  );
  const [storageStats, setStorageStats] = useState<StorageStats | null>(null);
  const [storageMessage, setStorageMessage] = useState(
    "Storage statistics have not been loaded yet."
  );
  const [deleteTarget, setDeleteTarget] = useState<DocumentRecord | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  useEffect(() => {
    void loadDocuments();
  }, []);

  useEffect(() => {
    const activeJobIds = Object.keys(activeJobs);
    if (activeJobIds.length === 0) return;

    const intervalId = window.setInterval(() => {
      void refreshActiveJobs();
    }, 1000);

    return () => window.clearInterval(intervalId);
  }, [activeJobs]);

  function trackJob(job: ProcessingJob) {
    setActiveJobs((currentJobs) => ({
      ...currentJobs,
      [job.id]: job
    }));
  }

  async function refreshActiveJobs() {
    const jobs = Object.values(activeJobs);
    if (jobs.length === 0) return;

    const latestJobs = await Promise.all(
      jobs.map(async (job) => {
        const response = await fetch(`http://127.0.0.1:8000/jobs/${job.id}`);
        if (!response.ok) return job;
        return (await response.json()) as ProcessingJob;
      })
    );

    const nextJobs: Record<number, ProcessingJob> = {};
    let shouldRefreshDocuments = false;
    for (const job of latestJobs) {
      if (job.status === "completed" || job.status === "failed") {
        shouldRefreshDocuments = true;
      } else {
        nextJobs[job.id] = job;
      }
    }

    setActiveJobs(nextJobs);
    setUpload((currentUpload) => {
      const matchingJob = latestJobs.find((job) => job.id === currentUpload.job?.id);
      return matchingJob ? { ...currentUpload, job: matchingJob } : currentUpload;
    });
    setWebImport((currentImport) => {
      const matchingJob = latestJobs.find((job) => job.id === currentImport.job?.id);
      return matchingJob ? { ...currentImport, job: matchingJob } : currentImport;
    });

    if (shouldRefreshDocuments) {
      await loadDocuments();
      for (const job of latestJobs) {
        if (job.status === "completed") {
          await loadChunks(job.document_id);
        }
      }
    }
  }

  function jobForDocument(documentId: number) {
    return Object.values(activeJobs).find(
      (job) =>
        job.document_id === documentId &&
        (job.status === "queued" || job.status === "running")
    );
  }

  function renderJobProgress(job: ProcessingJob | undefined) {
    if (!job) return null;

    return (
      <div className={`job-progress ${job.status}`}>
        <div className="job-progress-header">
          <strong>{job.stage}</strong>
          <span>{job.percent}%</span>
        </div>
        <div
          aria-label={`${job.stage} progress`}
          aria-valuemax={100}
          aria-valuemin={0}
          aria-valuenow={job.percent}
          className="progress-track"
          role="progressbar"
        >
          <span style={{ width: `${job.percent}%` }} />
        </div>
        <p>
          {job.message}
          {job.progress_total > 1
            ? ` (${job.progress_current}/${job.progress_total})`
            : ""}
        </p>
        {job.error ? <p className="job-error">{job.error}</p> : null}
      </div>
    );
  }

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
        const errorData = (await response.json().catch(() => null)) as {
          detail?: string;
        } | null;
        throw new Error(
          errorData?.detail ?? `Upload failed with ${response.status}`
        );
      }

      const data = (await response.json()) as ProcessingJobResponse;
      trackJob(data.job);

      setUpload({
        status: "success",
        message: "Document uploaded. Background processing has started.",
        document: data.document,
        job: data.job
      });
      await loadDocuments();
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
      await loadStorageStats();
    } catch (error) {
      setDocumentsMessage(
        error instanceof Error ? error.message : "Could not load documents."
      );
    }
  }

  async function loadStorageStats() {
    setStorageMessage("Loading storage statistics...");
    try {
      const response = await fetch("http://127.0.0.1:8000/storage/stats");
      if (!response.ok) {
        throw new Error(`Storage statistics failed with ${response.status}`);
      }
      setStorageStats((await response.json()) as StorageStats);
      setStorageMessage("Storage statistics loaded.");
    } catch (error) {
      setStorageMessage(
        error instanceof Error ? error.message : "Could not load storage statistics."
      );
    }
  }

  function clearDeletedDocument(documentId: number) {
    setActiveJobs((currentJobs) => {
      const nextJobs: Record<number, ProcessingJob> = {};
      for (const job of Object.values(currentJobs)) {
        if (job.document_id !== documentId) {
          nextJobs[job.id] = job;
        }
      }
      return nextJobs;
    });
    if (selectedDocument?.id === documentId) {
      setSelectedDocument(null);
      setChunks([]);
      setChunksMessage("Select a document to preview chunks.");
    }
    if (flashcardDocument?.id === documentId) {
      setFlashcardDocument(null);
      setFlashcards([]);
      setFlashcardsMessage("Select a document to view flashcards.");
    }
    if (quizDocument?.id === documentId) {
      setQuizDocument(null);
      setQuizQuestions([]);
      setQuizAnswers({});
      setQuizAttempts([]);
      setQuizMessage("Select a document to view quiz questions.");
    }
    if (summaryDocument?.id === documentId) {
      setSummaryDocument(null);
      setSummaries([]);
      setSummaryMessage("Select a document to view saved summaries.");
    }
    if (mindMapDocument?.id === documentId) {
      setMindMapDocument(null);
      setMindMaps([]);
      setActiveMindMapId(null);
      setMindMapMessage("Select a document to view saved mind maps.");
    }
    if (chatDocument?.id === documentId) {
      setChatDocument(null);
      setChatSessions([]);
      setActiveChatSession(null);
      setChatMessages([]);
      setChatInput("");
      setChatMessage("Select a parsed document to start a study chat.");
    }
    if (upload.document?.id === documentId) {
      setUpload({ status: "idle", message: "No file uploaded yet." });
    }
    if (webImport.document?.id === documentId) {
      setWebImport({ status: "idle", message: "No web page imported yet." });
    }
  }

  async function confirmDeleteDocument() {
    if (!deleteTarget) return;

    setDeletingId(deleteTarget.id);
    try {
      const response = await fetch(
        `http://127.0.0.1:8000/documents/${deleteTarget.id}`,
        { method: "DELETE" }
      );
      const data = (await response.json().catch(() => null)) as {
        detail?: string;
        cleanup_warning?: string | null;
      } | null;
      if (!response.ok) {
        throw new Error(data?.detail ?? `Delete failed with ${response.status}`);
      }

      const deletedFilename = deleteTarget.filename;
      clearDeletedDocument(deleteTarget.id);
      setDeleteTarget(null);
      await loadDocuments();
      setDocumentsMessage(
        data?.cleanup_warning ?? `${deletedFilename} and its related data were deleted.`
      );
    } catch (error) {
      setDocumentsMessage(
        error instanceof Error ? error.message : "Could not delete document."
      );
    } finally {
      setDeletingId(null);
    }
  }

  async function importWebPage() {
    if (!webUrl.trim()) {
      setWebImport({
        status: "error",
        message: "Enter a public web page URL first."
      });
      return;
    }

    setWebImport({
      status: "loading",
      message: "Downloading and indexing the web page..."
    });

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/documents/import-url",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ url: webUrl.trim() })
        }
      );

      if (!response.ok) {
        const errorData = (await response.json().catch(() => null)) as {
          detail?: string;
        } | null;
        throw new Error(
          errorData?.detail ?? `Web import failed with ${response.status}`
        );
      }

      const data = (await response.json()) as ProcessingJobResponse;
      trackJob(data.job);
      setWebImport({
        status: "success",
        message: "Web page imported. Background processing has started.",
        document: data.document,
        job: data.job
      });
      await loadDocuments();
    } catch (error) {
      setWebImport({
        status: "error",
        message:
          error instanceof Error ? error.message : "Could not import web page."
      });
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
    await loadChatSessions(document);
    await loadFlashcards(document);
    await loadQuiz(document);
    await loadQuizAttempts(document);
    await loadSummaries(document);
    await loadMindMaps(document);
  }

  async function loadChatSessions(document: DocumentRecord) {
    setChatDocument(document);
    setChatMessage("Loading study chat sessions...");

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/documents/${document.id}/chat-sessions`
      );

      if (!response.ok) {
        throw new Error(`Chat session list failed with ${response.status}`);
      }

      const data = (await response.json()) as ChatSession[];
      setChatSessions(data);
      setChatMessage(
        data.length === 0
          ? "No study chat sessions for this document yet."
          : `${data.length} study chat session${data.length === 1 ? "" : "s"} found.`
      );
      if (data.length > 0) {
        await selectChatSession(data[0]);
      } else {
        setActiveChatSession(null);
        setChatMessages([]);
      }
    } catch (error) {
      setChatMessage(
        error instanceof Error ? error.message : "Could not load study chat sessions."
      );
    }
  }

  async function createChatSession(document: DocumentRecord): Promise<ChatSession | null> {
    setCreatingChatSession(true);
    setChatDocument(document);
    setChatMessage(`Creating a study chat for ${document.filename}...`);

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/documents/${document.id}/chat-sessions`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ title: `Study chat: ${document.filename}` })
        }
      );

      if (!response.ok) {
        throw new Error(`Chat session creation failed with ${response.status}`);
      }

      const session = (await response.json()) as ChatSession;
      setChatSessions((currentSessions) => [session, ...currentSessions]);
      setActiveChatSession(session);
      setChatMessages([]);
      setChatMessage("Study chat created. Ask your first question.");
      return session;
    } catch (error) {
      setChatMessage(
        error instanceof Error ? error.message : "Could not create a study chat."
      );
      return null;
    } finally {
      setCreatingChatSession(false);
    }
  }

  async function selectChatSession(session: ChatSession) {
    setActiveChatSession(session);
    setChatMessage("Loading chat messages...");

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/chat-sessions/${session.id}/messages`
      );

      if (!response.ok) {
        throw new Error(`Chat messages failed with ${response.status}`);
      }

      const data = (await response.json()) as ChatMessage[];
      setChatMessages(data);
      setChatMessage(
        data.length === 0
          ? "This study chat has no messages yet."
          : `${data.length} saved message${data.length === 1 ? "" : "s"} loaded.`
      );
    } catch (error) {
      setChatMessage(
        error instanceof Error ? error.message : "Could not load chat messages."
      );
    }
  }

  async function sendStudyChatMessage() {
    if (!chatDocument) {
      setChatMessage("Select a document before chatting.");
      return;
    }
    if (chatDocument.parse_status !== "parsed") {
      setChatMessage("This document must finish parsing before chat can use it.");
      return;
    }

    let session = activeChatSession;
    if (!session) {
      session = await createChatSession(chatDocument);
      if (!session) return;
    }

    const content = chatInput.trim();
    if (!content) {
      setChatMessage("Enter a question before sending.");
      return;
    }

    setSendingChatMessage(true);
    setChatMessage("Generating a contextual answer...");

    const temporaryUserMessage: ChatMessage = {
      id: Date.now(),
      session_id: session.id,
      role: "user",
      content,
      sources: [],
      created_at: new Date().toISOString()
    };
    setChatMessages((currentMessages) => [...currentMessages, temporaryUserMessage]);
    setChatInput("");

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/chat-sessions/${session.id}/messages`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ content, top_k: 5 })
        }
      );

      if (!response.ok) {
        const errorData = (await response.json().catch(() => null)) as {
          detail?: string;
        } | null;
        throw new Error(
          errorData?.detail ?? `Study chat failed with ${response.status}`
        );
      }

      const data = (await response.json()) as {
        session: ChatSession;
        messages: ChatMessage[];
      };

      setActiveChatSession(data.session);
      setChatSessions((currentSessions) => [
        data.session,
        ...currentSessions.filter((currentSession) => currentSession.id !== data.session.id)
      ]);
      setChatMessages((currentMessages) => [
        ...currentMessages.filter((message) => message.id !== temporaryUserMessage.id),
        ...data.messages
      ]);
      setChatMessage("Answer saved to this study chat.");
    } catch (error) {
      setChatMessages((currentMessages) =>
        currentMessages.filter((message) => message.id !== temporaryUserMessage.id)
      );
      setChatInput(content);
      setChatMessage(
        error instanceof Error ? error.message : "Could not send chat message."
      );
    } finally {
      setSendingChatMessage(false);
    }
  }

  async function reprocessDocument(document: DocumentRecord) {
    setReprocessingId(document.id);
    setDocumentsMessage(`Reprocessing ${document.filename}...`);

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/documents/${document.id}/reprocess`,
        {
          method: "POST"
        }
      );

      if (!response.ok) {
        throw new Error(`Reprocess failed with ${response.status}`);
      }

      const data = (await response.json()) as ProcessingJobResponse;
      const updatedDocument = data.document as DocumentRecord;
      trackJob(data.job);
      setSelectedDocument(updatedDocument);
      setFlashcardDocument(updatedDocument);
      setFlashcards([]);
      setFlashcardsMessage("Flashcards were cleared because the document was reprocessed.");
      setQuizDocument(updatedDocument);
      setQuizQuestions([]);
      setQuizAnswers({});
      setQuizAttempts([]);
      setQuizMessage("Quiz questions were cleared because the document was reprocessed.");
      setSummaryDocument(updatedDocument);
      setSummaries([]);
      setSummaryMessage("Summaries were cleared because the document was reprocessed.");
      setMindMapDocument(updatedDocument);
      setMindMaps([]);
      setActiveMindMapId(null);
      setMindMapMessage("Mind maps were cleared because the document was reprocessed.");
      setChatDocument(updatedDocument);
      setChatSessions([]);
      setActiveChatSession(null);
      setChatMessages([]);
      setChatMessage("Study chats should be reloaded after the document is reprocessed.");
      await loadDocuments();
    } catch (error) {
      setDocumentsMessage(
        error instanceof Error ? error.message : "Could not reprocess document."
      );
    } finally {
      setReprocessingId(null);
    }
  }

  async function searchChunks() {
    if (!query.trim()) {
      setSearchMessage("Please enter a question first.");
      return;
    }

    setSearchMessage("Searching embedded chunks...");

    try {
      const response = await fetch("http://127.0.0.1:8000/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ query, top_k: 5 })
      });

      if (!response.ok) {
        throw new Error(`Search failed with ${response.status}`);
      }

      const data = (await response.json()) as SearchResult[];
      setSearchResults(data);
      setSearchMessage(
        data.length === 0
          ? "No embedded chunks were found."
          : `${data.length} relevant chunk${data.length === 1 ? "" : "s"} found.`
      );
    } catch (error) {
      setSearchMessage(
        error instanceof Error ? error.message : "Could not search chunks."
      );
    }
  }

  async function loadFlashcards(document: DocumentRecord) {
    setFlashcardDocument(document);
    setFlashcardsMessage("Loading flashcards...");

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/documents/${document.id}/flashcards`
      );

      if (!response.ok) {
        throw new Error(`Flashcard list failed with ${response.status}`);
      }

      const data = (await response.json()) as Flashcard[];
      setFlashcards(data);
      setFlippedCardIds([]);
      setFlashcardsMessage(
        data.length === 0
          ? "No flashcards generated for this document yet."
          : `${data.length} flashcard${data.length === 1 ? "" : "s"} ready.`
      );
    } catch (error) {
      setFlashcardsMessage(
        error instanceof Error ? error.message : "Could not load flashcards."
      );
    }
  }

  async function generateFlashcards(document: DocumentRecord) {
    setGeneratingCardsId(document.id);
    setFlashcardDocument(document);
    setFlashcardsMessage(`Generating flashcards for ${document.filename}...`);

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/documents/${document.id}/flashcards/generate`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ count: 10 })
        }
      );

      if (!response.ok) {
        throw new Error(`Flashcard generation failed with ${response.status}`);
      }

      const data = (await response.json()) as Flashcard[];
      setFlashcards(data);
      setFlippedCardIds([]);
      setFlashcardsMessage(`${data.length} flashcards generated.`);
    } catch (error) {
      setFlashcardsMessage(
        error instanceof Error ? error.message : "Could not generate flashcards."
      );
    } finally {
      setGeneratingCardsId(null);
    }
  }

  async function loadQuiz(document: DocumentRecord) {
    setQuizDocument(document);
    setQuizMessage("Loading quiz questions...");

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/documents/${document.id}/quiz`
      );

      if (!response.ok) {
        throw new Error(`Quiz list failed with ${response.status}`);
      }

      const data = (await response.json()) as QuizQuestion[];
      setQuizQuestions(data);
      setRevealedQuizIds([]);
      setQuizAnswers({});
      setQuizMessage(
        data.length === 0
          ? "No quiz questions generated for this document yet."
          : `${data.length} quiz question${data.length === 1 ? "" : "s"} ready.`
      );
    } catch (error) {
      setQuizMessage(
        error instanceof Error ? error.message : "Could not load quiz questions."
      );
    }
  }

  async function generateQuiz(document: DocumentRecord) {
    setGeneratingQuizId(document.id);
    setQuizDocument(document);
    setQuizMessage(`Generating quiz questions for ${document.filename}...`);

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/documents/${document.id}/quiz/generate`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ count: 8 })
        }
      );

      if (!response.ok) {
        throw new Error(`Quiz generation failed with ${response.status}`);
      }

      const data = (await response.json()) as QuizQuestion[];
      setQuizQuestions(data);
      setRevealedQuizIds([]);
      setQuizAnswers({});
      setQuizAttempts([]);
      setQuizMessage(`${data.length} quiz questions generated.`);
    } catch (error) {
      setQuizMessage(
        error instanceof Error ? error.message : "Could not generate quiz questions."
      );
    } finally {
      setGeneratingQuizId(null);
    }
  }

  async function loadQuizAttempts(document: DocumentRecord) {
    try {
      const response = await fetch(
        `http://127.0.0.1:8000/documents/${document.id}/quiz/attempts`
      );

      if (!response.ok) {
        throw new Error(`Quiz attempts failed with ${response.status}`);
      }

      const data = (await response.json()) as QuizAttempt[];
      setQuizAttempts(data);
    } catch (error) {
      setQuizAttempts([]);
      setQuizMessage(
        error instanceof Error ? error.message : "Could not load quiz attempts."
      );
    }
  }

  async function loadSummaries(document: DocumentRecord) {
    setSummaryDocument(document);
    setSummaryMessage("Loading saved summaries...");

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/documents/${document.id}/summaries`
      );

      if (!response.ok) {
        throw new Error(`Summary list failed with ${response.status}`);
      }

      const data = (await response.json()) as DocumentSummary[];
      setSummaries(data);
      setSummaryMessage(
        data.length === 0
          ? "No summaries generated for this document yet."
          : `${data.length} saved summar${data.length === 1 ? "y" : "ies"}.`
      );
    } catch (error) {
      setSummaries([]);
      setSummaryMessage(
        error instanceof Error ? error.message : "Could not load summaries."
      );
    }
  }

  async function generateSummary(document: DocumentRecord) {
    setGeneratingSummaryId(document.id);
    setSummaryDocument(document);
    setSummaryMessage(
      `Generating a ${summaryMode} summary for ${document.filename}...`
    );

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/documents/${document.id}/summaries/generate`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ mode: summaryMode })
        }
      );

      if (!response.ok) {
        const errorData = (await response.json().catch(() => null)) as {
          detail?: string;
        } | null;
        throw new Error(
          errorData?.detail ?? `Summary generation failed with ${response.status}`
        );
      }

      const summary = (await response.json()) as DocumentSummary;
      setSummaries((currentSummaries) => [summary, ...currentSummaries]);
      setSummaryMessage(
        `${summary.mode} summary saved after ${summary.model_call_count} local model call${summary.model_call_count === 1 ? "" : "s"}.`
      );
    } catch (error) {
      setSummaryMessage(
        error instanceof Error ? error.message : "Could not generate summary."
      );
    } finally {
      setGeneratingSummaryId(null);
    }
  }

  async function loadMindMaps(document: DocumentRecord) {
    setMindMapDocument(document);
    setMindMapMessage("Loading saved mind maps...");

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/documents/${document.id}/mind-maps`
      );

      if (!response.ok) {
        throw new Error(`Mind map list failed with ${response.status}`);
      }

      const data = (await response.json()) as DocumentMindMap[];
      setMindMaps(data);
      setActiveMindMapId(data[0]?.id ?? null);
      setMindMapMessage(
        data.length === 0
          ? "No mind maps generated for this document yet."
          : `${data.length} saved mind map${data.length === 1 ? "" : "s"}.`
      );
    } catch (error) {
      setMindMaps([]);
      setActiveMindMapId(null);
      setMindMapMessage(
        error instanceof Error ? error.message : "Could not load mind maps."
      );
    }
  }

  async function generateMindMap(document: DocumentRecord) {
    setGeneratingMindMapId(document.id);
    setMindMapDocument(document);
    setMindMapMessage(`Generating a mind map for ${document.filename}...`);

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/documents/${document.id}/mind-maps/generate`,
        { method: "POST" }
      );

      if (!response.ok) {
        const errorData = (await response.json().catch(() => null)) as {
          detail?: string;
        } | null;
        throw new Error(
          errorData?.detail ?? `Mind map generation failed with ${response.status}`
        );
      }

      const mindMap = (await response.json()) as DocumentMindMap;
      setMindMaps((currentMindMaps) => [mindMap, ...currentMindMaps]);
      setActiveMindMapId(mindMap.id);
      setMindMapMessage(`Mind map saved with ${mindMap.node_count} nodes.`);
    } catch (error) {
      setMindMapMessage(
        error instanceof Error ? error.message : "Could not generate mind map."
      );
    } finally {
      setGeneratingMindMapId(null);
    }
  }

  function setQuizAnswer(questionId: number, answer: string) {
    setQuizAnswers((currentAnswers) => ({
      ...currentAnswers,
      [questionId]: answer
    }));
  }

  async function submitQuiz() {
    if (!quizDocument || quizQuestions.length === 0) {
      setQuizMessage("Load quiz questions before submitting an attempt.");
      return;
    }

    setSubmittingQuiz(true);
    setQuizMessage("Scoring and saving your quiz attempt...");

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/documents/${quizDocument.id}/quiz/submit`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            answers: quizQuestions.map((question) => ({
              question_id: question.id,
              answer: quizAnswers[question.id] ?? ""
            }))
          })
        }
      );

      if (!response.ok) {
        throw new Error(`Quiz submission failed with ${response.status}`);
      }

      const attempt = (await response.json()) as QuizAttempt;
      setQuizAttempts((currentAttempts) => [attempt, ...currentAttempts]);
      setQuizMessage(
        `Attempt saved: ${attempt.correct_answers} of ${attempt.scored_questions} objective questions correct.`
      );
    } catch (error) {
      setQuizMessage(
        error instanceof Error ? error.message : "Could not submit quiz attempt."
      );
    } finally {
      setSubmittingQuiz(false);
    }
  }

  async function generateRagAnswer() {
    if (!query.trim()) {
      setAnswer({
        status: "error",
        message: "Please enter a question first.",
        answer: "",
        sources: []
      });
      return;
    }

    setAnswer({
      status: "loading",
      message: "Generating an answer from retrieved chunks...",
      answer: "",
      sources: []
    });

    try {
      const response = await fetch("http://127.0.0.1:8000/answer", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ query, top_k: 5 })
      });

      if (!response.ok) {
        throw new Error(`Answer failed with ${response.status}`);
      }

      const data = (await response.json()) as {
        answer: string;
        sources: SearchResult[];
      };

      setAnswer({
        status: "success",
        message: `${data.sources.length} source chunk${data.sources.length === 1 ? "" : "s"} used.`,
        answer: data.answer,
        sources: data.sources
      });
      setSearchResults(data.sources);
    } catch (error) {
      setAnswer({
        status: "error",
        message:
          error instanceof Error ? error.message : "Could not generate answer.",
        answer: "",
        sources: []
      });
    }
  }

  function toggleFlashcard(cardId: number) {
    setFlippedCardIds((currentIds) =>
      currentIds.includes(cardId)
        ? currentIds.filter((id) => id !== cardId)
        : [...currentIds, cardId]
    );
  }

  function toggleQuizAnswer(questionId: number) {
    setRevealedQuizIds((currentIds) =>
      currentIds.includes(questionId)
        ? currentIds.filter((id) => id !== questionId)
        : [...currentIds, questionId]
    );
  }

  function exportAnkiCsv() {
    if (!flashcardDocument) {
      setFlashcardsMessage("Select a document before exporting flashcards.");
      return;
    }

    window.location.href = `http://127.0.0.1:8000/documents/${flashcardDocument.id}/flashcards/export`;
  }

  const activeMindMap =
    mindMaps.find((mindMap) => mindMap.id === activeMindMapId) ?? null;

  return (
    <main className="shell">
      <section className="hero">
        <p className="eyebrow">Day 20 study chat</p>
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
            Choose PDF, Word, or PowerPoint material
          </label>
          <input
            accept=".pdf,.docx,.pptx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.presentationml.presentation"
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
              {upload.document.page_count > 0 ? (
                <div>
                  <dt>Pages</dt>
                  <dd>{upload.document.page_count}</dd>
                </div>
              ) : null}
              {upload.document.page_count > 0 ? (
                <div>
                  <dt>OCR pages</dt>
                  <dd>
                    {upload.document.ocr_page_count} / {upload.document.page_count}
                  </dd>
                </div>
              ) : null}
              <div>
                <dt>Chunks</dt>
                <dd>{upload.document.chunk_count}</dd>
              </div>
              <div>
                <dt>Embedded</dt>
                <dd>
                  {upload.document.embedded_count} / {upload.document.chunk_count}
                </dd>
              </div>
              {upload.document.parse_error ? (
                <div>
                  <dt>Parse error</dt>
                  <dd>{upload.document.parse_error}</dd>
                </div>
              ) : null}
              {upload.document.ocr_error ? (
                <div>
                  <dt>OCR warning</dt>
                  <dd>{upload.document.ocr_error}</dd>
                </div>
              ) : null}
            </dl>
          ) : null}
          {renderJobProgress(upload.job)}
          <div className="web-import">
            <label className="file-label" htmlFor="web-url">
              Import a public web page
            </label>
            <input
              id="web-url"
              onChange={(event) => setWebUrl(event.target.value)}
              placeholder="https://example.com/article"
              type="url"
              value={webUrl}
            />
            <button
              className="secondary-button"
              disabled={webImport.status === "loading"}
              onClick={() => void importWebPage()}
              type="button"
            >
              {webImport.status === "loading" ? "Importing..." : "Import Web Page"}
            </button>
            <p className={`health-message ${webImport.status}`}>
              {webImport.message}
            </p>
            {webImport.document ? (
              <dl className="upload-result">
                <div>
                  <dt>Page</dt>
                  <dd>{webImport.document.filename}</dd>
                </div>
                <div>
                  <dt>Source</dt>
                  <dd>{webImport.document.source_url}</dd>
                </div>
                <div>
                  <dt>Text chars</dt>
                  <dd>{webImport.document.text_char_count}</dd>
                </div>
                <div>
                  <dt>Chunks</dt>
                  <dd>{webImport.document.chunk_count}</dd>
                </div>
                <div>
                  <dt>Embedded</dt>
                  <dd>
                    {webImport.document.embedded_count} / {webImport.document.chunk_count}
                  </dd>
                </div>
              </dl>
            ) : null}
            {renderJobProgress(webImport.job)}
          </div>
        </div>
        <div className="documents-panel">
          <div className="documents-heading">
            <h2>Stored documents</h2>
            <button className="secondary-button" onClick={loadDocuments} type="button">
              Refresh
            </button>
          </div>
          {storageStats ? (
            <dl className="storage-stats">
              <div><dt>Documents</dt><dd>{storageStats.document_count}</dd></div>
              <div><dt>Tracked files</dt><dd>{formatBytes(storageStats.tracked_file_bytes)}</dd></div>
              <div><dt>Disk usage</dt><dd>{formatBytes(storageStats.actual_upload_bytes)}</dd></div>
              <div><dt>Chunks</dt><dd>{storageStats.embedded_chunk_count} / {storageStats.chunk_count}</dd></div>
              <div><dt>Summaries</dt><dd>{storageStats.summary_count}</dd></div>
              <div><dt>Mind maps</dt><dd>{storageStats.mind_map_count}</dd></div>
              <div><dt>Flashcards</dt><dd>{storageStats.flashcard_count}</dd></div>
              <div><dt>Quiz attempts</dt><dd>{storageStats.quiz_attempt_count}</dd></div>
              <div><dt>Processing jobs</dt><dd>{storageStats.processing_job_count}</dd></div>
              <div><dt>Chat sessions</dt><dd>{storageStats.chat_session_count}</dd></div>
              <div><dt>Chat messages</dt><dd>{storageStats.chat_message_count}</dd></div>
              <div><dt>Orphan files</dt><dd>{storageStats.orphan_file_count}</dd></div>
            </dl>
          ) : null}
          <p className="storage-message">{storageMessage}</p>
          <p className="health-message">{documentsMessage}</p>
          {documents.length > 0 ? (
            <ul className="documents-list">
              {documents.map((document) => {
                const activeJob = jobForDocument(document.id);

                return (
                <li key={document.id}>
                  <div className="document-identity">
                    <span className="document-name">{document.filename}</span>
                    {document.source_url ? (
                      <a
                        href={document.source_url}
                        rel="noreferrer"
                        target="_blank"
                      >
                        Open source
                      </a>
                    ) : null}
                  </div>
                  <span>{document.content_type}</span>
                  <span>{document.size_bytes} bytes</span>
                  <div className="document-status">
                    <span className={`parse-status ${document.parse_status}`}>
                      {document.parse_status}
                    </span>
                    {document.page_count > 0 ? (
                      <span>
                        {document.ocr_used
                          ? `OCR ${document.ocr_page_count}/${document.page_count}`
                          : `${document.page_count} pages`}
                      </span>
                    ) : null}
                  </div>
                  <span>{document.text_char_count} chars</span>
                  <button
                    className="link-button"
                    onClick={() => void selectDocument(document)}
                    type="button"
                  >
                    {document.chunk_count} chunks
                  </button>
                  <span className="embedding-count">
                    {document.embedded_count} embedded
                  </span>
                  <button
                    className="secondary-button compact-button"
                    disabled={reprocessingId === document.id || Boolean(activeJob)}
                    onClick={() => void reprocessDocument(document)}
                    type="button"
                  >
                    {reprocessingId === document.id || activeJob ? "Working..." : "Reprocess"}
                  </button>
                  <button
                    className="link-button"
                    onClick={() => void loadSummaries(document)}
                    type="button"
                  >
                    Summaries
                  </button>
                  <button
                    className="link-button"
                    onClick={() => void loadMindMaps(document)}
                    type="button"
                  >
                    Mind Maps
                  </button>
                  <button
                    className="secondary-button compact-button"
                    disabled={generatingCardsId === document.id}
                    onClick={() => void generateFlashcards(document)}
                    type="button"
                  >
                    {generatingCardsId === document.id ? "Working..." : "Generate Cards"}
                  </button>
                  <button
                    className="link-button"
                    onClick={() => void loadFlashcards(document)}
                    type="button"
                  >
                    Cards
                  </button>
                  <button
                    className="secondary-button compact-button"
                    disabled={generatingQuizId === document.id}
                    onClick={() => void generateQuiz(document)}
                    type="button"
                  >
                    {generatingQuizId === document.id ? "Working..." : "Generate Quiz"}
                  </button>
                  <button
                    className="link-button"
                    onClick={() => void loadQuiz(document)}
                    type="button"
                  >
                    Quiz
                  </button>
                  <button
                    className="link-button"
                    onClick={() => void loadChatSessions(document)}
                    type="button"
                  >
                    Chat
                  </button>
                  <button
                    aria-label={`Delete ${document.filename}`}
                    className="icon-button danger-button"
                    disabled={deletingId === document.id}
                    onClick={() => setDeleteTarget(document)}
                    title="Delete document"
                    type="button"
                  >
                    <Trash2 aria-hidden="true" size={17} />
                  </button>
                  <span>{new Date(document.created_at).toLocaleString()}</span>
                  {activeJob ? (
                    <div className="document-job">{renderJobProgress(activeJob)}</div>
                  ) : null}
                </li>
                );
              })}
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
                    Chunk {chunk.chunk_index + 1} - {chunk.char_count} chars -{" "}
                    <span className={`embedding-status ${chunk.embedding_status}`}>
                      {chunk.embedding_status}
                    </span>
                  </div>
                  {chunk.embedding_error ? (
                    <p className="chunk-error">{chunk.embedding_error}</p>
                  ) : null}
                  <p>{chunk.content.slice(0, 420)}</p>
                </li>
              ))}
            </ol>
          ) : null}
        </div>
        <div className="summaries-panel">
          <div className="summaries-heading">
            <h2>
              Summaries
              {summaryDocument ? `: ${summaryDocument.filename}` : ""}
            </h2>
            <div className="summary-controls">
              <div className="segmented-control" role="group" aria-label="Summary mode">
                <button
                  className={summaryMode === "brief" ? "active" : ""}
                  onClick={() => setSummaryMode("brief")}
                  type="button"
                >
                  Brief
                </button>
                <button
                  className={summaryMode === "detailed" ? "active" : ""}
                  onClick={() => setSummaryMode("detailed")}
                  type="button"
                >
                  Detailed
                </button>
              </div>
              <button
                className="primary-button"
                disabled={
                  !summaryDocument || generatingSummaryId === summaryDocument.id
                }
                onClick={() =>
                  summaryDocument && void generateSummary(summaryDocument)
                }
                type="button"
              >
                {summaryDocument && generatingSummaryId === summaryDocument.id
                  ? "Generating..."
                  : "Generate Summary"}
              </button>
            </div>
          </div>
          <p className="health-message">{summaryMessage}</p>
          {summaries.length > 0 ? (
            <ol className="summaries-list">
              {summaries.map((summary) => (
                <li key={summary.id}>
                  <article className="summary-entry">
                    <div className="summary-meta">
                      <strong>{summary.mode}</strong>
                      <span>{summary.source_chunk_count} chunks</span>
                      <span>{summary.model_call_count} model calls</span>
                      <span>{new Date(summary.created_at).toLocaleString()}</span>
                    </div>
                    <div className="summary-content">
                      <ReactMarkdown>{summary.content}</ReactMarkdown>
                    </div>
                  </article>
                </li>
              ))}
            </ol>
          ) : null}
        </div>
        <div className="mind-maps-panel">
          <div className="mind-maps-heading">
            <h2>
              Mind maps
              {mindMapDocument ? `: ${mindMapDocument.filename}` : ""}
            </h2>
            <div className="mind-map-actions">
              {mindMaps.length > 0 ? (
                <select
                  aria-label="Mind map version"
                  onChange={(event) => setActiveMindMapId(Number(event.target.value))}
                  value={activeMindMapId ?? ""}
                >
                  {mindMaps.map((mindMap) => (
                    <option key={mindMap.id} value={mindMap.id}>
                      {new Date(mindMap.created_at).toLocaleString()} - {mindMap.node_count} nodes
                    </option>
                  ))}
                </select>
              ) : null}
              <button
                className="primary-button"
                disabled={
                  !mindMapDocument || generatingMindMapId === mindMapDocument.id
                }
                onClick={() =>
                  mindMapDocument && void generateMindMap(mindMapDocument)
                }
                type="button"
              >
                {mindMapDocument && generatingMindMapId === mindMapDocument.id
                  ? "Generating..."
                  : "Generate Mind Map"}
              </button>
            </div>
          </div>
          <p className="health-message">{mindMapMessage}</p>
          {activeMindMap ? <MindMapView tree={activeMindMap.tree} /> : null}
        </div>
        <div className="search-panel">
          <h2>Ask your materials</h2>
          <textarea
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Explain Bell-LaPadula in simple words"
            value={query}
          />
          <div className="search-actions">
            <button className="primary-button" onClick={searchChunks} type="button">
              Search Chunks
            </button>
            <button
              className="secondary-button"
              disabled={answer.status === "loading"}
              onClick={generateRagAnswer}
              type="button"
            >
              {answer.status === "loading" ? "Generating..." : "Generate Answer"}
            </button>
          </div>
          <p className="health-message">{searchMessage}</p>
          {answer.answer ? (
            <div className="answer-box">
              <h3>Local RAG answer</h3>
              <p className={`health-message ${answer.status}`}>{answer.message}</p>
              <p>{answer.answer}</p>
              {answer.sources.length > 0 ? (
                <div className="sources-box">
                  <h4>Sources used</h4>
                  <ol>
                    {answer.sources.map((source, index) => (
                      <li key={source.chunk_id}>
                        <strong>Source {index + 1}</strong>: {source.filename},
                        chunk {source.chunk_index + 1}, distance{" "}
                        {source.distance.toFixed(4)}
                        <p>{source.content.slice(0, 360)}</p>
                      </li>
                    ))}
                  </ol>
                </div>
              ) : null}
            </div>
          ) : (
            <p className={`health-message ${answer.status}`}>{answer.message}</p>
          )}
          {searchResults.length > 0 ? (
            <ol className="search-results">
              {searchResults.map((result) => (
                <li key={result.chunk_id}>
                  <div className="chunk-meta">
                    {result.filename} - chunk {result.chunk_index + 1} -
                    distance {result.distance.toFixed(4)}
                  </div>
                  <p>{result.content.slice(0, 600)}</p>
                </li>
              ))}
            </ol>
          ) : null}
        </div>
        <div className="study-chat-panel">
          <div className="study-chat-heading">
            <h2>
              Study Chat
              {chatDocument ? `: ${chatDocument.filename}` : ""}
            </h2>
            <div className="study-chat-actions">
              {chatDocument ? (
                <button
                  className="secondary-button"
                  disabled={creatingChatSession}
                  onClick={() => void createChatSession(chatDocument)}
                  type="button"
                >
                  {creatingChatSession ? "Creating..." : "New Chat"}
                </button>
              ) : null}
            </div>
          </div>
          <p className="health-message">{chatMessage}</p>
          {chatDocument ? (
            <div className="study-chat-layout">
              <aside className="chat-sessions-list">
                {chatSessions.length > 0 ? (
                  chatSessions.map((session) => (
                    <button
                      className={
                        activeChatSession?.id === session.id ? "active" : ""
                      }
                      key={session.id}
                      onClick={() => void selectChatSession(session)}
                      type="button"
                    >
                      <strong>{session.title}</strong>
                      <span>
                        {session.message_count} message{session.message_count === 1 ? "" : "s"}
                      </span>
                    </button>
                  ))
                ) : (
                  <p>No saved chats yet.</p>
                )}
              </aside>
              <div className="chat-workspace">
                <div className="chat-messages">
                  {chatMessages.length > 0 ? (
                    chatMessages.map((message) => (
                      <article
                        className={`chat-bubble ${message.role}`}
                        key={message.id}
                      >
                        <span className="chat-role">{message.role}</span>
                        <p>{message.content}</p>
                        {message.role === "assistant" && message.sources.length > 0 ? (
                          <div className="chat-sources">
                            <strong>Sources</strong>
                            <ol>
                              {message.sources.map((source, index) => (
                                <li key={`${message.id}-${source.chunk_id}`}>
                                  Source {index + 1}: {source.filename}, chunk{" "}
                                  {source.chunk_index + 1}, distance{" "}
                                  {source.distance.toFixed(4)}
                                  <p>{source.content.slice(0, 260)}</p>
                                </li>
                              ))}
                            </ol>
                          </div>
                        ) : null}
                      </article>
                    ))
                  ) : (
                    <p className="health-message">
                      Ask a question to begin a saved multi-turn study chat.
                    </p>
                  )}
                </div>
                <div className="chat-composer">
                  <textarea
                    disabled={sendingChatMessage}
                    onChange={(event) => setChatInput(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
                        void sendStudyChatMessage();
                      }
                    }}
                    placeholder="Ask a follow-up question about this document"
                    value={chatInput}
                  />
                  <button
                    className="primary-button"
                    disabled={sendingChatMessage || !chatDocument}
                    onClick={() => void sendStudyChatMessage()}
                    type="button"
                  >
                    {sendingChatMessage ? "Thinking..." : "Send"}
                  </button>
                </div>
              </div>
            </div>
          ) : null}
        </div>
        <div className="flashcards-panel">
          <div className="flashcards-heading">
            <h2>
              Flashcards
              {flashcardDocument ? `: ${flashcardDocument.filename}` : ""}
            </h2>
            <button
              className="secondary-button"
              disabled={flashcards.length === 0}
              onClick={exportAnkiCsv}
              type="button"
            >
              Export Anki CSV
            </button>
          </div>
          <p className="health-message">{flashcardsMessage}</p>
          {flashcards.length > 0 ? (
            <ol className="flashcards-list">
              {flashcards.map((card) => (
                <li key={card.id}>
                  <button
                    className={`flashcard ${flippedCardIds.includes(card.id) ? "flipped" : ""}`}
                    onClick={() => toggleFlashcard(card.id)}
                    type="button"
                  >
                    <span className="flashcard-label">
                      {flippedCardIds.includes(card.id) ? "Answer" : "Question"}
                    </span>
                    <span className="flashcard-content">
                      {flippedCardIds.includes(card.id)
                        ? card.answer
                        : card.question}
                    </span>
                  </button>
                </li>
              ))}
            </ol>
          ) : null}
        </div>
        <div className="quiz-panel">
          <h2>
            Quiz
            {quizDocument ? `: ${quizDocument.filename}` : ""}
          </h2>
          <p className="health-message">{quizMessage}</p>
          {quizQuestions.length > 0 ? (
            <ol className="quiz-list">
              {quizQuestions.map((question) => {
                const isRevealed = revealedQuizIds.includes(question.id);

                return (
                  <li key={question.id}>
                    <div className="quiz-question">
                      <span className="quiz-type">
                        {question.question_type.replace("_", " ")}
                      </span>
                      <h3>{question.question}</h3>
                      {question.choices.length > 0 ? (
                        <div className="quiz-choices">
                          {question.choices.map((choice) => (
                            <label key={choice} className="quiz-choice">
                              <input
                                checked={quizAnswers[question.id] === choice}
                                name={`quiz-question-${question.id}`}
                                onChange={() => setQuizAnswer(question.id, choice)}
                                type="radio"
                                value={choice}
                              />
                              <span>{choice}</span>
                            </label>
                          ))}
                        </div>
                      ) : (
                        <textarea
                          className="quiz-text-answer"
                          onChange={(event) =>
                            setQuizAnswer(question.id, event.target.value)
                          }
                          placeholder="Write your answer"
                          value={quizAnswers[question.id] ?? ""}
                        />
                      )}
                      <button
                        className="secondary-button compact-button"
                        onClick={() => toggleQuizAnswer(question.id)}
                        type="button"
                      >
                        {isRevealed ? "Hide Answer" : "Show Answer"}
                      </button>
                      {isRevealed ? (
                        <div className="quiz-answer">
                          <strong>Correct answer:</strong>
                          <p>{question.correct_answer}</p>
                          <strong>Explanation:</strong>
                          <p>{question.explanation}</p>
                        </div>
                      ) : null}
                    </div>
                  </li>
                );
              })}
            </ol>
          ) : null}
          {quizQuestions.length > 0 ? (
            <button
              className="primary-button"
              disabled={submittingQuiz}
              onClick={() => void submitQuiz()}
              type="button"
            >
              {submittingQuiz ? "Submitting..." : "Submit Quiz"}
            </button>
          ) : null}
          {quizAttempts.length > 0 ? (
            <div className="quiz-attempts">
              <h3>Saved attempts</h3>
              <ol>
                {quizAttempts.map((attempt) => (
                  <li key={attempt.id}>
                    <strong>
                      {attempt.correct_answers} / {attempt.scored_questions}
                    </strong>{" "}
                    objective questions correct. {attempt.total_questions - attempt.scored_questions} short answer response{attempt.total_questions - attempt.scored_questions === 1 ? "" : "s"} saved. {new Date(attempt.created_at).toLocaleString()}
                  </li>
                ))}
              </ol>
            </div>
          ) : null}
        </div>
      </section>
      {deleteTarget ? (
        <div className="modal-backdrop" role="presentation">
          <div
            aria-labelledby="delete-dialog-title"
            aria-modal="true"
            className="delete-dialog"
            role="dialog"
          >
            <div className="dialog-heading">
              <h2 id="delete-dialog-title">Delete document?</h2>
              <button
                aria-label="Close delete dialog"
                className="icon-button"
                disabled={deletingId === deleteTarget.id}
                onClick={() => setDeleteTarget(null)}
                title="Close"
                type="button"
              >
                <X aria-hidden="true" size={18} />
              </button>
            </div>
            <p>
              <strong>{deleteTarget.filename}</strong> and all of its chunks,
              summaries, mind maps, flashcards, and quiz data will be permanently
              deleted.
            </p>
            <div className="dialog-actions">
              <button
                className="secondary-button"
                disabled={deletingId === deleteTarget.id}
                onClick={() => setDeleteTarget(null)}
                type="button"
              >
                Cancel
              </button>
              <button
                className="danger-action"
                disabled={deletingId === deleteTarget.id}
                onClick={() => void confirmDeleteDocument()}
                type="button"
              >
                {deletingId === deleteTarget.id ? "Deleting..." : "Delete permanently"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
