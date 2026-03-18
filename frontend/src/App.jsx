import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { ProtectedRoute } from './components/Layout/ProtectedRoute';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { DashboardPage } from './pages/DashboardPage';
import LandingPage from './pages/LandingPage';
import { SettingsPage } from './pages/SettingsPage';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ToastContainer } from './components/Toast/Toast';
import { GlobalShortcutsHandler } from './components/GlobalShortcutsHandler';

export default function App() {
  return (
    <AuthProvider>
      <ThemeProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <ErrorBoundary>
                    <DashboardPage />
                  </ErrorBoundary>
                </ProtectedRoute>
              }
            />
            <Route
              path="/settings"
              element={
                <ProtectedRoute>
                  <ErrorBoundary>
                    <SettingsPage />
                  </ErrorBoundary>
                </ProtectedRoute>
              }
            />
          </Routes>
          <ToastContainer />
          <GlobalShortcutsHandler />
        </BrowserRouter>
      </ThemeProvider>
    </AuthProvider>
  );
}
