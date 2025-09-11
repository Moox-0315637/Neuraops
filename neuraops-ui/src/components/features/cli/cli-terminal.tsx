'use client'

import { useState, useEffect, useRef } from 'react'
import { cn } from '@/lib/utils'

interface CommandOutput {
  command: string
  output: string
  timestamp: Date
  type: 'success' | 'error' | 'info'
}

export default function CLITerminal() {
  const [input, setInput] = useState('')
  const [history, setHistory] = useState<CommandOutput[]>([])
  const [isConnected] = useState(true)
  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Mock initial connection message
  useEffect(() => {
    const initialMessages: CommandOutput[] = [
      {
        command: '',
        output: '● NeuraOps CLI v2.0.0 - AI-Powered DevOps Assistant',
        timestamp: new Date(),
        type: 'success'
      },
      {
        command: '',
        output: 'Connected to Ollama: gpt-oss:20b',
        timestamp: new Date(),
        type: 'info'
      },
      {
        command: '',
        output: "Type 'help' for available commands",
        timestamp: new Date(),
        type: 'info'
      }
    ]
    setHistory(initialMessages)
  }, [])

  // Auto-scroll to bottom
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [history])

  // Mock command responses
  const mockCommands: Record<string, { output: string; type: 'success' | 'error' | 'info' }> = {
    help: {
      output: `Available commands:
  health          Check system health and Ollama connectivity
  logs analyze    Analyze log files with AI insights
  infra generate  Generate infrastructure code
  incident        Handle incidents with AI automation
  agent list      List all registered agents
  clear           Clear terminal screen
  version         Show NeuraOps version`,
      type: 'info'
    },
    health: {
      output: `✅ NeuraOps Core: Healthy
✅ Ollama Connection: Active (gpt-oss:20b)
✅ Cache System: 78% hit rate
✅ Security: All checks passed
🚀 System ready for operations`,
      type: 'success'
    },
    version: {
      output: 'NeuraOps CLI v2.0.0 - Built for OpenAI Hackathon 2024',
      type: 'info'
    },
    'agent list': {
      output: `Active Agents:
  📡 production-agent-01    Status: Online    Last seen: 2min ago
  📡 staging-agent-02       Status: Online    Last seen: 5min ago
  📡 dev-agent-03           Status: Offline   Last seen: 1h ago
  📡 monitoring-agent-04    Status: Online    Last seen: 1min ago`,
      type: 'success'
    },
    'logs analyze': {
      output: `🔍 Analyzing log files...
📊 Found 156 entries, 3 warnings, 0 errors
⚠️  High memory usage pattern detected
💡 Recommendation: Scale up memory allocation
✅ Analysis complete - No critical issues found`,
      type: 'success'
    },
    'infra generate': {
      output: `🏗️  Generating infrastructure code...
🎯 Target: AWS 3-tier web application
📝 Generated: terraform/main.tf (247 lines)
📝 Generated: terraform/variables.tf (56 lines)
📝 Generated: terraform/outputs.tf (23 lines)
✅ Infrastructure code ready for deployment`,
      type: 'success'
    },
    incident: {
      output: `🚨 Incident Response System
📋 Recent incidents: 0 critical, 2 warnings
🔧 Auto-response: Enabled
🛡️  Safety checks: Active
💚 All systems operational`,
      type: 'success'
    },
    clear: {
      output: '',
      type: 'info'
    }
  }

  const handleCommand = (cmd: string) => {
    const command = cmd.trim().toLowerCase()
    
    if (command === 'clear') {
      setHistory([])
      return
    }

    const response = mockCommands[command] || {
      output: `Command not found: ${cmd}. Type 'help' for available commands.`,
      type: 'error' as const
    }

    const newEntry: CommandOutput = {
      command: cmd,
      output: response.output,
      timestamp: new Date(),
      type: response.type
    }

    setHistory(prev => [...prev, newEntry])
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && input.trim()) {
      handleCommand(input)
      setInput('')
    }
  }

  const handleTerminalClick = () => {
    inputRef.current?.focus()
  }

  return (
    <div className="font-mono text-sm">
      {/* Terminal Header */}
      <div className="flex items-center justify-between bg-gray-800 px-4 py-2 border-b border-gray-700">
        <div className="flex items-center space-x-2">
          <div className="flex space-x-1">
            <div className="w-3 h-3 rounded-full bg-red-500"></div>
            <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
          </div>
          <span className="text-white font-medium ml-4">neuraops@container-01</span>
        </div>
        <div className="flex items-center space-x-4">
          <button
            onClick={() => setHistory([])}
            className="text-gray-400 hover:text-white text-xs bg-gray-700 px-2 py-1 rounded"
          >
            Clear
          </button>
          <div className={cn(
            'flex items-center space-x-1 text-xs',
            isConnected ? 'text-green-400' : 'text-red-400'
          )}>
            <div className={cn(
              'w-2 h-2 rounded-full',
              isConnected ? 'bg-green-500' : 'bg-red-500'
            )}></div>
            <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
          </div>
        </div>
      </div>

      {/* Terminal Content */}
      <div className="relative">
        <button
          onClick={handleTerminalClick}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              handleTerminalClick()
            }
          }}
          className="absolute inset-0 w-full h-full bg-transparent border-none outline-none cursor-text opacity-0 z-10"
          aria-label="Focus terminal input"
        />
        <div
          ref={containerRef}
          className="bg-black p-4 h-96 overflow-y-auto cursor-text"
        >
        {/* Command History */}
        {history.map((entry, index) => (
          <div key={`${entry.timestamp.getTime()}-${index}`} className="mb-2">
            {entry.command && (
              <div className="flex items-center space-x-2 mb-1">
                <span className="text-green-400">neuraops@container-01:~$</span>
                <span className="text-white">{entry.command}</span>
              </div>
            )}
            {entry.output && (
              <div className={cn(
                'whitespace-pre-line ml-0 mb-2',
                entry.type === 'error' && 'text-red-400',
                entry.type === 'success' && 'text-green-400',
                entry.type === 'info' && 'text-blue-400'
              )}>
                {entry.output}
              </div>
            )}
          </div>
        ))}

        {/* Current Input Line */}
        <div className="flex items-center space-x-2">
          <span className="text-green-400">neuraops@container-01:~$</span>
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1 bg-transparent text-white outline-none"
            placeholder="Type a command..."
            autoFocus
          />
          <div className="w-2 h-4 bg-white animate-pulse"></div>
        </div>
        </div>
      </div>
    </div>
  )
}
