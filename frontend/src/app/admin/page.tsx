'use client'

import React, { useState, useEffect } from 'react'
import { 
  ArrowRightStartOnRectangleIcon,
  CogIcon,
  BellIcon,
  SparklesIcon,
  ShieldCheckIcon
} from '@heroicons/react/24/outline'
import AdminDashboard from '@/components/AdminDashboard'

export default function AdminPage() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const ADMIN_CREDENTIALS = {
    username: 'admin',
    password: 'hotel123'
  }

  useEffect(() => {
    const authStatus = localStorage.getItem('hotelAdminAuth')
    if (authStatus === 'authenticated') {
      setIsAuthenticated(true)
    }
  }, [])

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    await new Promise(resolve => setTimeout(resolve, 1000))

    if (username === ADMIN_CREDENTIALS.username && password === ADMIN_CREDENTIALS.password) {
      setIsAuthenticated(true)
      localStorage.setItem('hotelAdminAuth', 'authenticated')
    } else {
      setError('Invalid username or password')
    }

    setLoading(false)
  }

  const handleLogout = () => {
    setIsAuthenticated(false)
    localStorage.removeItem('hotelAdminAuth')
    setUsername('')
    setPassword('')
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full">
          <div className="hotel-card p-8">
            <div className="text-center mb-8">
              <div className="hotel-gradient w-20 h-20 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-2xl">
                <ShieldCheckIcon className="h-10 w-10 text-white" />
              </div>
              <h1 className="text-3xl font-bold hotel-heading mb-2">
                {process.env.NEXT_PUBLIC_HOTEL_NAME || 'Hotel'} Admin
              </h1>
              <p className="hotel-subheading">Staff Dashboard Access</p>
            </div>

            <form onSubmit={handleLogin} className="space-y-6">
              <div>
                <label htmlFor="username" className="block text-sm font-semibold hotel-subheading mb-3">
                  Username
                </label>
                <input
                  type="text"
                  id="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="hotel-input w-full"
                  placeholder="Enter username"
                  required
                />
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-semibold hotel-subheading mb-3">
                  Password
                </label>
                <input
                  type="password"
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="hotel-input w-full"
                  placeholder="Enter password"
                  required
                />
              </div>

              {error && (
                <div className="hotel-card p-4 bg-red-50 border border-red-200">
                  <p className="text-red-600 font-medium text-sm">{error}</p>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="hotel-button-primary w-full text-lg py-4 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <div className="flex items-center justify-center gap-3">
                    <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent"></div>
                    Signing in...
                  </div>
                ) : (
                  <div className="flex items-center justify-center gap-3">
                    <ArrowRightStartOnRectangleIcon className="h-5 w-5" />
                    Sign In
                  </div>
                )}
              </button>
            </form>

            <div className="mt-8 pt-6 border-t border-gray-200">
              <div className="hotel-card p-4 bg-gradient-to-r from-blue-50 to-indigo-50">
                <h3 className="text-sm font-semibold hotel-heading mb-3">Demo Credentials</h3>
                <div className="space-y-2 text-sm hotel-text">
                  <div className="flex justify-between">
                    <span className="font-medium">Username:</span>
                    <span className="font-mono">admin</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-medium">Password:</span>
                    <span className="font-mono">hotel123</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      {/* Enhanced Header */}
      <header className="hotel-glass sticky top-0 z-40 border-b border-white/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-20">
            <div className="flex items-center space-x-4">
              <div className="hotel-gradient w-14 h-14 rounded-2xl flex items-center justify-center shadow-lg">
                <SparklesIcon className="h-8 w-8 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold hotel-heading">
                  {process.env.NEXT_PUBLIC_HOTEL_NAME || 'Hotel'} Admin
                </h1>
                <p className="text-sm hotel-subheading">Staff Dashboard & Order Management</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <button className="hotel-button-secondary p-3">
                <BellIcon className="h-5 w-5" />
              </button>
              <button className="hotel-button-secondary p-3">
                <CogIcon className="h-5 w-5" />
              </button>
              <div className="hidden sm:block text-right">
                <div className="hotel-badge hotel-badge-gold">Admin User</div>
                <p className="text-sm hotel-subheading mt-1">Staff Member</p>
              </div>
              <button
                onClick={handleLogout}
                className="hotel-button-secondary flex items-center gap-2 px-4 py-3"
              >
                <ArrowRightStartOnRectangleIcon className="h-4 w-4" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h2 className="text-3xl font-bold hotel-heading mb-2">Room Service Orders</h2>
          <p className="hotel-text text-lg">
            Monitor and manage all room service orders in real-time
          </p>
        </div>

        <AdminDashboard />
      </div>
    </div>
  )
}