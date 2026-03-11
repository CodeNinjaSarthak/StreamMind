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
  const [sectionExpanded, setSectionExpanded] = useState(false);
  const fileRef = useRef(null);
  const uploadXhrRef = useRef(null);

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
      <div
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer', marginBottom: sectionExpanded ? 10 : 0 }}
        onClick={() => setSectionExpanded(e => !e)}
      >
        <span className="sidebar-section-title" style={{ marginBottom: 0 }}>
          RAG DOCS {docs.length > 0 && `(${docs.length})`}
        </span>
        <span style={{ color: 'var(--color-muted)', fontSize: 10, fontFamily: 'var(--font-display)' }}>
          {sectionExpanded ? '▲' : '▼'}
        </span>
      </div>

      {sectionExpanded && (
        <>
          <p className="hint" style={{ marginBottom: 8, marginTop: 6 }}>
            Upload files (.pdf, .docx, .txt) to give the AI context.
          </p>

          <form onSubmit={handleUpload}>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.docx,.txt"
              style={{ display: 'block', marginBottom: 8, fontSize: 11, width: '100%', color: 'var(--color-muted)' }}
            />
            {pct > 0 && pct < 100 && (
              <div style={{ background: 'var(--color-border)', height: 3, margin: '6px 0' }}>
                <div style={{ width: `${pct}%`, height: '100%', background: 'var(--color-accent)', transition: 'width 0.2s' }} />
              </div>
            )}
            <button type="submit" className="btn btn-primary" disabled={uploading}>
              {uploading ? 'Uploading…' : 'Upload'}
            </button>
          </form>

          <div style={{ marginTop: 12 }}>
            {isLoadingInitial ? (
              <div className="skeleton-list">
                {[1, 2].map(i => <Skeleton key={i} className="sk-doc-row" />)}
              </div>
            ) : docs.length === 0 ? (
              <p className="hint" style={{ textAlign: 'center', paddingTop: 8 }}>No documents yet</p>
            ) : (
              docs.map(doc => (
                <div
                  key={doc.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 8,
                    padding: '5px 0',
                    borderBottom: '1px solid var(--color-border)',
                  }}
                >
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <span
                      style={{
                        fontSize: 11,
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
                    <span style={{ fontSize: 10, color: 'var(--color-muted)', fontFamily: 'var(--font-display)' }}>
                      {formatBytes(doc.file_size_bytes)}
                    </span>
                  </div>
                  <button
                    className="btn btn-danger-sm"
                    onClick={() => handleDelete(doc.id)}
                    style={{ flexShrink: 0 }}
                  >
                    ✕
                  </button>
                </div>
              ))
            )}
          </div>
        </>
      )}
    </section>
  );
}
