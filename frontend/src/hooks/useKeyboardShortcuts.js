import { useEffect } from 'react';

/**
 * Dashboard-scoped keyboard shortcuts.
 * All callbacks MUST be wrapped in useCallback at the call site.
 * '?' and 'Escape' are handled globally by GlobalShortcutsHandler.
 */
export function useKeyboardShortcuts({ onNewSession, onApproveFirst, onFocusSearch, enabled = true }) {
  useEffect(() => {
    if (!enabled) return;
    function handler(e) {
      const tag = document.activeElement?.tagName;
      const isTyping = ['INPUT', 'TEXTAREA', 'SELECT'].includes(tag)
        || document.activeElement?.contentEditable === 'true';

      // Ctrl+K / Cmd+K — context-sensitive focus (works even when typing = false edge case)
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        onFocusSearch?.();
        return;
      }
      if (isTyping) return;
      if (e.key === 'n' || e.key === 'N') { onNewSession?.(); return; }
      if (e.key === 'a' || e.key === 'A') { onApproveFirst?.(); return; }
    }
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [enabled, onNewSession, onApproveFirst, onFocusSearch]);
}
