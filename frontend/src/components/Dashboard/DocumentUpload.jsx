import { useState, useEffect, useRef } from 'react';
import { uploadDocument, getDocuments, deleteDocument } from '../../services/api';

export function DocumentUpload({ token }) {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState(null); // { type: 'success' | 'error', message }
  const [deletingId, setDeletingId] = useState(null);
  const fileRef = useRef(null);

  useEffect(() => {
    fetchDocs();
  }, [token]);

  async function fetchDocs() {
    try {
      setLoading(true);
      const data = await getDocuments(token);
      setDocs(data || []);
    } catch {
      setDocs([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload(e) {
    e.preventDefault();
    const file = fileRef.current?.files[0];
    if (!file) return;
    setUploading(true);
    setStatus(null);
    try {
      const result = await uploadDocument(file, token);
      const n = result.chunks_created;
      setStatus({ type: 'success', message: `Uploaded — ${n} chunk${n !== 1 ? 's' : ''} indexed.` });
      if (fileRef.current) fileRef.current.value = '';
      await fetchDocs();
    } catch (e) {
      setStatus({ type: 'error', message: e.message });
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(docId) {
    setDeletingId(docId);
    try {
      await deleteDocument(docId, token);
      setDocs(prev => prev.filter(d => d.id !== docId));
    } catch {
      // deletion failed — list will re-sync on next fetchDocs
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <section className="panel">
      <h2>RAG Documents</h2>
      <p className="hint" style={{ marginBottom: 10 }}>
        Upload PDF or DOCX files to give the AI extra context when generating answers.
      </p>

      <form onSubmit={handleUpload}>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.docx"
          style={{ display: 'block', marginBottom: 8, fontSize: 13, width: '100%' }}
        />
        {status && (
          <p
            className={status.type === 'error' ? 'error-msg' : 'hint'}
            style={{ marginBottom: 6 }}
          >
            {status.message}
          </p>
        )}
        <button type="submit" className="btn btn-primary" disabled={uploading}>
          {uploading ? 'Uploading...' : 'Upload'}
        </button>
      </form>

      <div style={{ marginTop: 14 }}>
        {loading ? (
          <p style={{ fontSize: 13, color: 'var(--color-muted)' }}>Loading documents...</p>
        ) : docs.length === 0 ? (
          <p className="hint">No documents uploaded yet.</p>
        ) : (
          <>
            <p className="hint" style={{ marginBottom: 6 }}>
              Indexed chunks ({docs.length}):
            </p>
            <div style={{ maxHeight: 180, overflowY: 'auto' }}>
              {docs.map(doc => (
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
                      title={doc.title}
                    >
                      {doc.title}
                    </span>
                    {doc.source_type && (
                      <span className="badge" style={{ fontSize: 10, marginTop: 2 }}>
                        {doc.source_type.toUpperCase()}
                      </span>
                    )}
                  </div>
                  <button
                    className="btn btn-danger-sm"
                    onClick={() => handleDelete(doc.id)}
                    disabled={deletingId === doc.id}
                    style={{ flexShrink: 0 }}
                  >
                    {deletingId === doc.id ? '…' : 'Delete'}
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
