import { Navigate, Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export default function LandingPage() {
  const { isAuthenticated } = useAuth();
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;

  return (
    <div className="landing">
      {/* Header */}
      <header className="landing-header anim-nav">
        <span className="logo">AI Doubt Manager</span>
        <nav className="landing-nav">
          <Link to="/login" className="btn btn-sm">Login</Link>
          <Link to="/register" className="btn btn-primary btn-sm">Get Started</Link>
        </nav>
      </header>

      {/* Hero */}
      <section className="landing-hero">
        <h1 className="anim-1">AI Live Doubt Manager</h1>
        <p className="tagline anim-2">Intelligent Q&A management for YouTube live streams</p>
        <p className="subtitle anim-3">
          Automatically detect, cluster, and answer student questions in real-time using AI
        </p>
        <div className="landing-ctas anim-4">
          <Link to="/register" className="btn btn-primary">Get Started</Link>
          <Link to="/login" className="btn">Login</Link>
        </div>
      </section>

      {/* Combined Features + Steps */}
      <section className="landing-features">
        <h2>How It Works</h2>
        <div className="features-grid">
          <div className="feature-card">
            <span className="card-number">01</span>
            <div className="feature-emoji">🔗</div>
            <h3>Connect Your Stream</h3>
            <p>Link your YouTube live stream and let the system start monitoring comments in real-time.</p>
          </div>
          <div className="feature-card">
            <span className="card-number">02</span>
            <div className="feature-emoji">🤖</div>
            <h3>AI Processes Questions</h3>
            <p>AI classifies comments as questions and clusters similar ones together automatically.</p>
          </div>
          <div className="feature-card">
            <span className="card-number">03</span>
            <div className="feature-emoji">💡</div>
            <h3>Review & Post Answers</h3>
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
