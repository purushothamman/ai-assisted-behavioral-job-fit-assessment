// src/App.jsx
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import Navbar from './components/Navbar'
import ProtectedRoute from './components/ProtectedRoute'

import LoginPage       from './pages/LoginPage'
import DashboardPage   from './pages/DashboardPage'
import DimensionsPage  from './pages/DimensionsPage'
import JobsPage        from './pages/JobsPage'
import CreateJobPage   from './pages/CreateJobPage'
import JobDetailPage   from './pages/JobDetailPage'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div style={{ minHeight: '100vh', background: 'var(--color-bg)' }}>
          <Navbar />
          <Routes>
            {/* Public */}
            <Route path="/login" element={<LoginPage />} />

            {/* Protected — recruiter only */}
            <Route path="/dashboard"   element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
            <Route path="/dimensions"  element={<ProtectedRoute><DimensionsPage /></ProtectedRoute>} />
            <Route path="/jobs"        element={<ProtectedRoute><JobsPage /></ProtectedRoute>} />
            <Route path="/jobs/new"    element={<ProtectedRoute><CreateJobPage /></ProtectedRoute>} />
            <Route path="/jobs/:id"    element={<ProtectedRoute><JobDetailPage /></ProtectedRoute>} />

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </div>
      </BrowserRouter>
    </AuthProvider>
  )
}
