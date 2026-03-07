const DEFAULT_MESSAGES = {
  warning: 'YouTube API quota is running low. New comments may stop being processed soon.',
  critical: 'YouTube API quota exhausted. Comment processing and posting are paused until quota resets.',
};

const WarningIcon = () => (
  <svg
    className="quota-banner-icon"
    viewBox="0 0 20 20"
    fill="currentColor"
    aria-hidden="true"
  >
    <path
      fillRule="evenodd"
      d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z"
      clipRule="evenodd"
    />
  </svg>
);

const DismissIcon = () => (
  <svg
    viewBox="0 0 14 14"
    fill="currentColor"
    aria-hidden="true"
    width="14"
    height="14"
  >
    <path d="M1.293 1.293a1 1 0 011.414 0L7 5.586l4.293-4.293a1 1 0 111.414 1.414L8.414 7l4.293 4.293a1 1 0 01-1.414 1.414L7 8.414l-4.293 4.293a1 1 0 01-1.414-1.414L5.586 7 1.293 2.707a1 1 0 010-1.414z" />
  </svg>
);

export function QuotaBanner({ level, message, onDismiss }) {
  const text = message || DEFAULT_MESSAGES[level];
  return (
    <div className={`quota-banner quota-banner-${level}`} role="alert">
      <WarningIcon />
      <span className="quota-banner-text">{text}</span>
      <button
        className="quota-banner-dismiss"
        onClick={onDismiss}
        aria-label="Dismiss quota alert"
        type="button"
      >
        <DismissIcon />
      </button>
    </div>
  );
}
