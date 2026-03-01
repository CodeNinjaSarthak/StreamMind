const SHORTCUTS = [
  { keys: '?',       description: 'Show keyboard shortcuts' },
  { keys: 'N',       description: 'Focus new session title input' },
  { keys: 'A',       description: 'Approve first pending cluster' },
  { keys: 'Ctrl+K',  description: 'Focus primary action input' },
  { keys: 'Esc',     description: 'Close modal' },
];

export function KeyboardShortcutsModal({ onClose }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h3>Keyboard Shortcuts</h3>
        <table className="shortcuts-table">
          <tbody>
            {SHORTCUTS.map(s => (
              <tr key={s.keys}>
                <td><kbd className="kbd">{s.keys}</kbd></td>
                <td>{s.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="modal-actions">
          <button className="btn btn-sm" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
