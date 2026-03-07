import { useState, useEffect, useRef } from 'react';
import { uploadDocument, getDocuments, deleteDocument } from '../../services/api';
import { showToast } from '../../hooks/useToast';
import { Skeleton } from '../Skeleton';

const MAX_SIZE = 10 * 1024 * 1024;
const ALLOWED = ['.pdf', '.docx', '.txt'];

function formatBytes(bytes) {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function DocumentUpload({ sessionId, token }) {
  const [docs, setDocs] = useState([]);
  const [isLoadingInitial, setIsLoadingInitial] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [pct, setPct] = useState(0);
  const fileRef = useRef(null);
  const uploadXhrRef = useRef(null);

  // Fetch docs for current session — stale closure guard
  useEffect(() => {
    let stale = false;
    async function run() {
      setIsLoadingInitial(true);
      try {
        const data = await getDocuments({ token, sessionId });
        if (!stale) setDocs(data || []);
      } catch {
        if (!stale) setDocs([]);
      } finally {
        if (!stale) setIsLoadingInitial(false);
      }
    }
    run();
    return () => { stale = true; };
  }, [sessionId, token]);

  // Abort in-flight upload when session changes
  useEffect(() => {
    return () => {
      if (uploadXhrRef.current) {
        uploadXhrRef.current.abort();
        uploadXhrRef.current = null;
      }
    };
  }, [sessionId]);

  async function handleUpload(e) {
    e.preventDefault();
    const file = fileRef.current?.files[0];
    if (!file) return;

    if (file.size > MAX_SIZE) {
      showToast('File must be under 10MB', 'error');
      return;
    }
    if (!ALLOWED.some(ext => file.name.toLowerCase().endsWith(ext))) {
      showToast('Only .pdf, .docx, .txt files allowed', 'error');
      return;
    }

    const boundSessionId = sessionId;
    setUploading(true);
    setPct(0);
    try {
      const result = await uploadDocument(sessionId, file, token, setPct, uploadXhrRef);
      if (sessionId === boundSessionId) {
        const n = result.chunks_created;
        showToast(`Uploaded — ${n} chunk${n !== 1 ? 's' : ''} indexed.`, 'success');
        if (fileRef.current) fileRef.current.value = '';
        // Refetch docs for this session
        const data = await getDocuments({ token, sessionId });
        setDocs(data || []);
      }
    } catch (err) {
      if (err.message === 'aborted') return;
      if (sessionId === boundSessionId) showToast(err.message, 'error');
    } finally {
      setUploading(false);
      setPct(0);
    }
  }

  async function handleDelete(docId) {
    const idx = docs.findIndex(d => d.id === docId);
    const removed = docs[idx];
    setDocs(prev => prev.filter(d => d.id !== docId));
    try {
      await deleteDocument(docId, token);
    } catch {
      if (removed !== undefined) {
        setDocs(prev => {
          const next = [...prev];
          next.splice(idx, 0, removed);
          return next;
        });
      }
    }
  }

  return (
    <section className="panel">
      <h2>RAG Documents</h2>
      <p className="hint" style={{ marginBottom: 10 }}>
        Upload files to give the AI extra context when generating answers.
      </p>

      <form onSubmit={handleUpload}>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.docx,.txt"
          style={{ display: 'block', marginBottom: 8, fontSize: 13, width: '100%' }}
        />
        {pct > 0 && pct < 100 && (
          <div style={{ background: 'var(--color-border)', borderRadius: 4, height: 4, margin: '6px 0' }}>
            <div style={{ width: `${pct}%`, height: '100%', background: 'var(--color-primary)', borderRadius: 4, transition: 'width 0.2s' }} />
          </div>
        )}
        <button type="submit" className="btn btn-primary" disabled={uploading}>
          {uploading ? 'Uploading...' : 'Upload'}
        </button>
      </form>

      <div style={{ marginTop: 14 }}>
        {isLoadingInitial ? (
          <div className="skeleton-list">
            {[1, 2].map(i => <Skeleton key={i} className="sk-doc-row" />)}
          </div>
        ) : docs.length === 0 ? (
          <div className="empty-state">
            <span className="empty-state-icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14,2 14,8 20,8"/>
                <line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="16" y2="17"/>
              </svg>
            </span>
            <p className="empty-state-title">No documents uploaded</p>
            <p className="empty-state-description">Upload PDFs to give the AI context when answering</p>
          </div>
        ) : (
          <>
            <p className="hint" style={{ marginBottom: 6 }}>
              Indexed documents ({docs.length}):
            </p>
            <div style={{ maxHeight: 200, overflowY: 'auto' }}>
              {docs.map(doc => (
                <div
                  key={doc.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 8,
                    padding: '6px 0',
                    borderBottom: '1px solid var(--color-border)',
                  }}
                >
                  <div style={{ minWidth: 0 }}>
                    <span
                      style={{
                        fontSize: 12,
                        color: 'var(--color-text)',
                        display: 'block',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                      title={doc.filename || doc.title}
                    >
                      {doc.filename || doc.title}
                    </span>
                    <span style={{ fontSize: 11, color: 'var(--color-muted)' }}>
                      {formatBytes(doc.file_size_bytes)}
                      {doc.created_at && ` · ${new Date(doc.created_at).toLocaleDateString()}`}
                    </span>
                  </div>
                  <button
                    className="btn btn-danger-sm"
                    onClick={() => handleDelete(doc.id)}
                    style={{ flexShrink: 0 }}
                  >
                    Delete
                  </button>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </section>
  );
}
