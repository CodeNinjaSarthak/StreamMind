import { useState, useEffect, useRef } from 'react';
import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { getSessionAnalytics, getSessionClusters, getClusterComments } from '../../services/api';
import { ActivityLog } from './ActivityLog';
import { Skeleton } from '../Skeleton';

const ANALYTICS_EVENTS = new Set([
  'comment_created', 'comment_classified',
  'cluster_created', 'cluster_updated',
  'answer_ready', 'answer_posted',
]);

const TOOLTIP_STYLE = {
  contentStyle: {
    background: 'var(--color-surface)',
    border: '1px solid var(--color-border)',
    borderRadius: 6,
    fontSize: 12,
  },
};

function formatHour(isoStr) {
  return new Date(isoStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function downloadBlob(content, mimeType, filename) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function AnalyticsPanel({ sessionId, token, sessionEvents }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [exporting, setExporting] = useState(false);
  const debounceRef = useRef(null);

  function loadAnalytics() {
    return getSessionAnalytics(sessionId, token)
      .then(d => { setData(d); setError(null); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }

  // Initial fetch
  useEffect(() => {
    setLoading(true);
    setData(null);
    setError(null);
    loadAnalytics();
  }, [sessionId, token]);

  // Live update: debounce 2s on relevant WS events
  useEffect(() => {
    if (!sessionEvents || sessionEvents.length === 0) return;
    const last = sessionEvents[sessionEvents.length - 1];
    if (!last || !ANALYTICS_EVENTS.has(last.type)) return;
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => loadAnalytics(), 2000);
    return () => clearTimeout(debounceRef.current);
  }, [sessionEvents]);

  async function handleExportCSV() {
    setExporting(true);
    try {
      const clusters = await getSessionClusters(sessionId, token);
      const rows = [['Question', 'Answer', 'Cluster', 'Timestamp', 'Is Posted']];
      for (const cluster of (clusters || [])) {
        let comments;
        try {
          comments = await getClusterComments(cluster.id, token);
        } catch (e) {
          console.warn(`Skipping cluster ${cluster.id} in export:`, e.message);
          continue;
        }
        const latestAnswer = cluster.answers?.[cluster.answers.length - 1];
        for (const comment of (comments || [])) {
          rows.push([
            comment.text,
            latestAnswer?.text || '',
            cluster.title,
            new Date(comment.created_at).toLocaleString(),
            latestAnswer?.is_posted ? 'Yes' : 'No',
          ]);
        }
      }
      const csv = rows
        .map(row => row.map(cell => `"${String(cell ?? '').replace(/"/g, '""')}"`).join(','))
        .join('\n');
      downloadBlob(csv, 'text/csv', `qa-export-${sessionId}-${Date.now()}.csv`);
    } catch (e) {
      alert(`Export failed: ${e.message}`);
    } finally {
      setExporting(false);
    }
  }

  async function handleExportJSON() {
    setExporting(true);
    try {
      const clusters = await getSessionClusters(sessionId, token);
      const output = [];
      for (const cluster of (clusters || [])) {
        let comments;
        try {
          comments = await getClusterComments(cluster.id, token);
        } catch (e) {
          console.warn(`Skipping cluster ${cluster.id} in export:`, e.message);
          continue;
        }
        output.push({
          cluster_id: cluster.id,
          title: cluster.title,
          comment_count: cluster.comment_count,
          answer: cluster.answers?.[cluster.answers.length - 1]?.text || null,
          is_posted: cluster.answers?.[cluster.answers.length - 1]?.is_posted ?? false,
          questions: (comments || []).map(c => ({
            text: c.text,
            author: c.author_name,
            timestamp: c.created_at,
          })),
        });
      }
      downloadBlob(
        JSON.stringify(output, null, 2),
        'application/json',
        `qa-export-${sessionId}-${Date.now()}.json`,
      );
    } catch (e) {
      alert(`Export failed: ${e.message}`);
    } finally {
      setExporting(false);
    }
  }

  if (loading) return (
    <div className="panel">
      <h2>Session Analytics</h2>
      <div className="analytics-stats">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="analytics-stat">
            <Skeleton className="sk-analytics-value" />
            <Skeleton className="sk-analytics-label" />
          </div>
        ))}
      </div>
      <Skeleton className="sk-analytics-chart" />
    </div>
  );
  if (error) return <div className="panel"><p className="error-msg">{error}</p></div>;

  // Derive cumulative line chart data
  let running = 0;
  const cumulativeData = data.questions_over_time.map(d => ({
    hour: formatHour(d.hour),
    total: (running += d.count),
  }));
  const hourlyData = data.questions_over_time.map(d => ({
    hour: formatHour(d.hour),
    count: d.count,
  }));

  const maxCount = data.top_clusters[0]?.comment_count || 1;

  return (
    <>
      <section className="panel">
        <h2>Session Analytics</h2>

        <div className="analytics-stats">
          <div className="analytics-stat">
            <div className="analytics-stat-value">{data.total_questions}</div>
            <div className="analytics-stat-label">Total Questions</div>
          </div>
          <div className="analytics-stat">
            <div className="analytics-stat-value">{Math.round(data.response_rate * 100)}%</div>
            <div className="analytics-stat-label">Clusters Answered</div>
          </div>
          <div className="analytics-stat">
            <div className="analytics-stat-value">{data.avg_cluster_size}</div>
            <div className="analytics-stat-label">Avg Cluster Size</div>
          </div>
          <div className="analytics-stat">
            <div className="analytics-stat-value">{data.total_clusters}</div>
            <div className="analytics-stat-label">Clusters</div>
          </div>
          {data.peak_hour && (
            <div className="analytics-stat" style={{ gridColumn: 'span 2' }}>
              <div className="analytics-stat-value">{formatHour(data.peak_hour)}</div>
              <div className="analytics-stat-label">Peak Activity Hour</div>
            </div>
          )}
        </div>

        {data.questions_over_time.length > 0 ? (
          <>
            <div className="analytics-chart">
              <h3>Total Questions Over Time</h3>
              <ResponsiveContainer width="100%" height={160}>
                <LineChart data={cumulativeData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis dataKey="hour" tick={{ fontSize: 11, fill: 'var(--color-muted)' }} />
                  <YAxis tick={{ fontSize: 11, fill: 'var(--color-muted)' }} allowDecimals={false} />
                  <Tooltip {...TOOLTIP_STYLE} />
                  <Line type="monotone" dataKey="total" name="Total" stroke="var(--color-primary)" dot={false} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="analytics-chart">
              <h3>Questions per Hour</h3>
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={hourlyData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis dataKey="hour" tick={{ fontSize: 11, fill: 'var(--color-muted)' }} />
                  <YAxis tick={{ fontSize: 11, fill: 'var(--color-muted)' }} allowDecimals={false} />
                  <Tooltip {...TOOLTIP_STYLE} />
                  <Bar dataKey="count" name="Questions" fill="var(--color-primary)" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </>
        ) : (
          <div className="empty-state" style={{ marginBottom: 16 }}>
            <span className="empty-state-icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/>
                <line x1="6" y1="20" x2="6" y2="14"/><line x1="2" y1="20" x2="22" y2="20"/>
              </svg>
            </span>
            <p className="empty-state-title">No data yet</p>
            <p className="empty-state-description">Analytics will appear once questions start coming in</p>
          </div>
        )}

        {data.top_clusters.length > 0 && (
          <>
            <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Top Question Topics</h3>
            <ul className="top-topics-list">
              {data.top_clusters.map((c, i) => (
                <li key={i} className="top-topics-item">
                  <span style={{ color: 'var(--color-muted)', minWidth: 16 }}>{i + 1}</span>
                  <span style={{ flex: 1, marginLeft: 8 }}>{c.title}</span>
                  <div className="top-topics-bar-wrap">
                    <div className="top-topics-bar" style={{ width: `${(c.comment_count / maxCount) * 100}%` }} />
                  </div>
                  <span style={{ color: 'var(--color-muted)', minWidth: 28, textAlign: 'right' }}>{c.comment_count}</span>
                </li>
              ))}
            </ul>
          </>
        )}

        <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Export Q&amp;A Data</h3>
        <div className="export-row">
          <button className="btn btn-sm" onClick={handleExportCSV} disabled={exporting}>
            {exporting ? 'Exporting...' : '⬇ Export CSV'}
          </button>
          <button className="btn btn-sm" onClick={handleExportJSON} disabled={exporting}>
            {exporting ? 'Exporting...' : '⬇ Export JSON'}
          </button>
        </div>
      </section>

      <section className="panel">
        <h2>Activity Log</h2>
        <ActivityLog sessionEvents={sessionEvents} />
      </section>
    </>
  );
}
