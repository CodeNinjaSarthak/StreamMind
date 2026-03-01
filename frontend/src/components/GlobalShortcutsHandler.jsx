import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { KeyboardShortcutsModal } from './Dashboard/KeyboardShortcutsModal';

export function GlobalShortcutsHandler() {
  const { isAuthenticated } = useAuth();
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) return; // don't register on login/register pages

    function handler(e) {
      const tag = document.activeElement?.tagName;
      const isTyping = ['INPUT', 'TEXTAREA', 'SELECT'].includes(tag)
        || document.activeElement?.contentEditable === 'true';
      if (e.key === 'Escape') { setShow(false); return; }
      if (isTyping) return;
      if (e.key === '?') setShow(true);
    }
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isAuthenticated]);

  return show ? <KeyboardShortcutsModal onClose={() => setShow(false)} /> : null;
}
