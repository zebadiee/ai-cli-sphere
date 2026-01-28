import { useState } from 'react'
import { ECIRForm } from './components/forms/ECIRForm'

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-blue-600 text-white py-6 shadow-lg">
        <div className="container mx-auto px-4">
          <h1 className="text-3xl font-bold">ECIR Studio</h1>
          <p className="text-blue-100 mt-2">Electrical Installation Condition Report System</p>
        </div>
      </header>
      
      <main className="container mx-auto px-4 py-8">
        <ECIRForm />
      </main>
      
      <footer className="bg-gray-800 text-white py-6 mt-12">
        <div className="container mx-auto px-4 text-center">
          <p>&copy; 2026 ECIR Studio. All rights reserved.</p>
          <p className="text-gray-400 text-sm mt-2">
            Critical fields require explicit human assertion. No auto-compliance.
          </p>
        </div>
      </footer>
    </div>
  )
}

export default App
