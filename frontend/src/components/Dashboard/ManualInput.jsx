import { useState } from 'react';
import { submitManualQuestion } from '../../services/api';

export function ManualInput({ sessionId, token, textareaRef }) {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null); // { type: 'success'|'error', text }

  const lineCount = text ? text.split('\n').filter(l => l.trim()).length : 0;

  async function handleSubmit(e) {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed) return;

    setLoading(true);
    setMessage(null);
    try {
      const result = await submitManualQuestion(sessionId, trimmed, token);
      setText('');
      setMessage({ type: 'success', text: `${result.created} question(s) submitted` });
    } catch (err) {
      const msg = err.message === 'rate_limit'
        ? 'Rate limit hit, try again in 60s'
        : (err.message || 'Failed to submit questions');
      setMessage({ type: 'error', text: msg });
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel">
      <h2>Manual Questions</h2>
      <p className="hint">One question per line, up to 10.</p>
      <form onSubmit={handleSubmit}>
        <textarea
          ref={textareaRef}
          value={text}
          onChange={e => setText(e.target.value)}
          rows={4}
          placeholder={"What is Newton's first law?\nHow do I solve quadratic equations?"}
          style={{ fontFamily: 'var(--font-display)', fontSize: 11 }}
        />
        <p className="hint" style={{ textAlign: 'right', marginBottom: 4, marginTop: 2 }}>
          {lineCount} / 10
        </p>
        {message && (
          <p
            className={message.type === 'error' ? 'error-msg' : ''}
            style={message.type === 'success' ? { color: 'var(--color-success)', fontSize: 11, marginTop: 2, marginBottom: 4 } : {}}
          >
            {message.text}
          </p>
        )}
        <button type="submit" className="btn btn-primary" disabled={loading || lineCount === 0}>
          {loading ? 'Submitting…' : 'Submit Questions'}
        </button>
      </form>
    </section>
  );
}
