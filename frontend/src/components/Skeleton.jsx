export function Skeleton({ className = '' }) {
  return <div className={`skeleton${className ? ' ' + className : ''}`} />;
}
