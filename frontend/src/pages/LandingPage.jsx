import { Navigate, Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export default function LandingPage() {
  const { isAuthenticated } = useAuth();
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;

  return (
    <div className="landing">
      {/* Header */}
      <header className="landing-header">
        <span className="logo">AI Doubt Manager</span>
        <nav className="landing-nav">
          <Link to="/login" className="btn btn-sm">Login</Link>
          <Link to="/register" className="btn btn-primary btn-sm">Get Started</Link>
        </nav>
      </header>

      {/* Hero */}
      <section className="landing-hero">
        <h1>AI Live Doubt Manager</h1>
        <p className="tagline">Intelligent Q&A management for YouTube live streams</p>
        <p className="subtitle">
          Automatically detect, cluster, and answer student questions in real-time using AI
        </p>
        <div className="landing-ctas">
          <Link to="/register" className="btn btn-primary">Get Started</Link>
          <Link to="/login" className="btn">Login</Link>
        </div>
      </section>

      {/* Combined Features + Steps */}
      <section className="landing-features">
        <h2>How It Works</h2>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-emoji">🔗</div>
            <h3>1. Connect Your Stream</h3>
            <p>Link your YouTube live stream and let the system start monitoring comments in real-time.</p>
          </div>
          <div className="feature-card">
            <div className="feature-emoji">🤖</div>
            <h3>2. AI Processes Questions</h3>
            <p>AI classifies comments as questions and clusters similar ones together automatically.</p>
          </div>
          <div className="feature-card">
            <div className="feature-emoji">💡</div>
            <h3>3. Review & Post Answers</h3>
            <p>Generate comprehensive answers using RAG and Gemini AI, then post them to your audience.</p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        Built with FastAPI, React, PostgreSQL, and Google Gemini
      </footer>
    </div>
  );
}
