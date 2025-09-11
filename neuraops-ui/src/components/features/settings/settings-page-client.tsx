/**
 * NeuraOps Settings Page Client Component
 * Client-side settings management with API configuration
 */
'use client'

import React, { useState } from 'react'
import ApiConfiguration from './api-configuration'

const settingsItems = [
  { id: 'profile', name: 'Profile', icon: '👤' },
  { id: 'security', name: 'Security', icon: '🔒' },
  { id: 'notifications', name: 'Notifications', icon: '🔔' },
  { id: 'theme', name: 'Theme', icon: '🎨' },
  { id: 'api', name: 'API Configuration', icon: '🔑' },
  { id: 'integrations', name: 'Integrations', icon: '🔌' }
]

export default function SettingsPageClient() {
  const [activeTab, setActiveTab] = useState('api') // Default to API configuration

  const renderContent = () => {
    switch (activeTab) {
      case 'api':
        return <ApiConfiguration />
      
      case 'profile':
        return (
          <div className="space-y-6">
            <div className="bg-dark-800 rounded-lg border border-gray-700">
              <div className="p-6 border-b border-gray-700">
                <h2 className="text-xl font-semibold text-white">Profile Settings</h2>
                <p className="text-gray-400 text-sm mt-1">Manage your personal information and account details</p>
              </div>
              <div className="p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label htmlFor="fullName" className="block text-sm font-medium text-gray-300 mb-2">
                      Full Name
                    </label>
                    <input
                      id="fullName"
                      type="text"
                      defaultValue="Admin User"
                      className="w-full bg-dark-700 border border-gray-600 rounded-lg px-3 py-2 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-2">
                      Email Address
                    </label>
                    <input
                      id="email"
                      type="email"
                      defaultValue="admin@neuraops.dev"
                      className="w-full bg-dark-700 border border-gray-600 rounded-lg px-3 py-2 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                  </div>
                </div>
                <div className="mt-6 flex justify-end space-x-3">
                  <button className="px-4 py-2 border border-gray-600 rounded-lg text-gray-400 hover:text-white hover:border-gray-500 transition-colors">
                    Cancel
                  </button>
                  <button className="px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors">
                    Save Changes
                  </button>
                </div>
              </div>
            </div>
          </div>
        )

      default:
        return (
          <div className="bg-dark-800 rounded-lg border border-gray-700 p-8">
            <div className="text-center text-gray-400">
              <span className="text-4xl mb-4 block">{settingsItems.find(item => item.id === activeTab)?.icon}</span>
              <h3 className="text-lg font-medium text-white mb-2">
                {settingsItems.find(item => item.id === activeTab)?.name}
              </h3>
              <p>This section is under development.</p>
            </div>
          </div>
        )
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Settings</h1>
        <p className="text-gray-400 mt-2">
          Configure your preferences and system settings
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Settings Navigation */}
        <div className="lg:col-span-1">
          <div className="bg-dark-800 rounded-lg border border-gray-700 p-4 sticky top-4">
            <nav className="space-y-2">
              {settingsItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-left transition-colors ${
                    activeTab === item.id
                      ? 'bg-primary-500/20 text-primary-500 border border-primary-500/30' 
                      : 'text-gray-400 hover:text-white hover:bg-dark-700'
                  }`}
                >
                  <span className="text-lg">{item.icon}</span>
                  <span>{item.name}</span>
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* Settings Content */}
        <div className="lg:col-span-3">
          {renderContent()}
        </div>
      </div>
    </div>
  )
}