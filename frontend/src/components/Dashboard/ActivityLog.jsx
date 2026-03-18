const EVENT_META = {
  comment_created:    { icon: '💬', label: () => 'New question received' },
  comment_classified: { icon: '🏷',  label: () => 'Question classified' },
  cluster_created:    { icon: '🗂',  label: (d) => `Cluster created: ${d?.title ?? ''}` },
  cluster_updated:    { icon: '🔄', label: () => 'Cluster updated' },
  answer_ready:       { icon: '🤖', label: () => 'Answer generated' },
  answer_posted:      { icon: '✅', label: () => 'Answer posted to YouTube' },
  session_started:    { icon: '▶',  label: () => 'Session started' },
  session_ended:      { icon: '⏹',  label: () => 'Session ended' },
  quota_alert:        { icon: '⚠',  label: () => 'YouTube quota alert' },
  quota_exceeded:     { icon: '🚫', label: () => 'YouTube quota exceeded' },
};

function relativeTime(isoStr) {
  const diff = Math.floor((Date.now() - new Date(isoStr)) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

export function ActivityLog({ sessionEvents }) {
  const events = (sessionEvents || [])
    .filter(m => EVENT_META[m.type])
    .slice(-20)
    .reverse();

  if (events.length === 0) {
    return <p className="empty-msg">No activity yet — events will appear as they arrive.</p>;
  }

  return (
    <div className="activity-log">
      {events.map((msg) => {
        const meta = EVENT_META[msg.type];
        return (
          <div key={msg.timestamp + '-' + msg.type} className="activity-item">
            <span className="activity-icon">{meta.icon}</span>
            <span className="activity-text">{meta.label(msg.data)}</span>
            <span className="activity-time">{relativeTime(msg.timestamp)}</span>
          </div>
        );
      })}
    </div>
  );
}
