'use client'

/**
 * NeuraOps Dynamic CLI Terminal
 * Real terminal that executes commands on neuraops-core container
 */
import { useState, useEffect, useRef } from 'react'
import { cn } from '@/lib/utils'
import { apiService } from '@/services/api'

interface CommandOutput {
  command: string
  output: string
  error?: string
  timestamp: Date
  type: 'success' | 'error' | 'info' | 'running'
  exitCode?: number
}

interface CLIExecuteRequest {
  command: string
  args?: string[]
  timeout?: number
}

export default function DynamicCLITerminal() {
  const [input, setInput] = useState('')
  const [history, setHistory] = useState<CommandOutput[]>([])
  const [commandHistory, setCommandHistory] = useState<string[]>([])
  const [historyIndex, setHistoryIndex] = useState(-1)
  const [isConnected, setIsConnected] = useState(true)
  const [isExecuting, setIsExecuting] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Initialize terminal with welcome messages
  useEffect(() => {
    const checkConnection = async () => {
      try {
        await apiService.healthCheck()
        setIsConnected(true)
        const initialMessages: CommandOutput[] = [
          {
            command: '',
            output: '● NeuraOps Dynamic CLI v2.0.0 - Connected to Core',
            timestamp: new Date(),
            type: 'success'
          },
          {
            command: '',
            output: '✅ API Connection: Active',
            timestamp: new Date(),
            type: 'info'
          },
          {
            command: '',
            output: "Type 'help' to see available NeuraOps commands",
            timestamp: new Date(),
            type: 'info'
          }
        ]
        setHistory(initialMessages)
      } catch (error) {
        setIsConnected(false)
        const errorMessage: CommandOutput[] = [
          {
            command: '',
            output: '❌ NeuraOps CLI - Connection Failed',
            timestamp: new Date(),
            type: 'error'
          },
          {
            command: '',
            output: 'Unable to connect to NeuraOps Core API',
            timestamp: new Date(),
            type: 'error'
          }
        ]
        setHistory(errorMessage)
      }
    }

    checkConnection()
  }, [])

  // Auto-scroll to bottom when new content is added
  useEffect(() => {
    if (containerRef.current) {
      const container = containerRef.current
      // Always scroll to bottom when new content is added
      setTimeout(() => {
        container.scrollTo({
          top: container.scrollHeight,
          behavior: 'smooth'
        })
      }, 100) // Slightly longer delay to ensure content is rendered
    }
  }, [history])

  // Focus input when terminal container is clicked
  useEffect(() => {
    const container = containerRef.current
    if (container) {
      const handleClick = (e: MouseEvent) => {
        // Only focus if clicking in the terminal content area, not on scrollbars
        if (e.target === container || container.contains(e.target as Node)) {
          inputRef.current?.focus()
        }
      }
      
      container.addEventListener('click', handleClick)
      return () => container.removeEventListener('click', handleClick)
    }
  }, [])

  // Helper function to scroll to bottom
  const scrollToBottom = () => {
    if (containerRef.current) {
      setTimeout(() => {
        const container = containerRef.current
        if (container) {
          container.scrollTop = container.scrollHeight
        }
      }, 50)
    }
  }

  const executeCommand = async (commandLine: string) => {
    if (!commandLine.trim()) return

    const parts = commandLine.trim().split(' ')
    let command = parts[0]
    let args = parts.slice(1)

    // Handle 'neuraops' prefix - remove it since API already runs python -m src.main
    if (command === 'neuraops') {
      if (args.length > 0) {
        command = args[0]
        args = args.slice(1)
      } else {
        // If just 'neuraops' is typed, show help
        command = '--help'
        args = []
      }
    }

    // Add command to history immediately
    const commandEntry: CommandOutput = {
      command: commandLine,
      output: '',
      timestamp: new Date(),
      type: 'running'
    }
    setHistory(prev => [...prev, commandEntry])
    scrollToBottom()

    // Handle clear command locally
    if (command === 'clear') {
      setHistory([])
      return
    }

    setIsExecuting(true)

    try {
      // Prepare request for API
      const request: CLIExecuteRequest = {
        command,
        args,
        timeout: 300
      }

      // Debug: Check if we have a token
      console.log('API Service Token:', apiService.getCurrentToken())
      console.log('API Service Authenticated:', apiService.isAuthenticated())
      
      // Execute via API with 5-minute timeout
      const response = await apiService.request<any>('/api/cli/execute', {
        method: 'POST',
        body: JSON.stringify(request)
      }, 300000) // 5 minutes in milliseconds

      console.log('CLI Response:', response) // Debug log

      // Extract result data
      const resultData = response.data ?? response
      const success = resultData.success ?? false
      const stdout = resultData.stdout ?? ''
      const stderr = resultData.stderr ?? ''
      const exitCode = resultData.return_code ?? resultData.returncode ?? (success ? 0 : 1)

      // Create result entry
      const resultEntry: CommandOutput = {
        command: commandLine,
        output: stdout ?? stderr ?? 'Command completed',
        error: stderr,
        timestamp: new Date(),
        type: success ? 'success' : 'error',
        exitCode
      }

      // Update the running command entry with results
      setHistory(prev => {
        const updated = [...prev]
        const lastIndex = updated.length - 1
        if (lastIndex >= 0 && updated[lastIndex].type === 'running') {
          updated[lastIndex] = resultEntry
        } else {
          updated.push(resultEntry)
        }
        return updated
      })
      scrollToBottom()

    } catch (error: any) {
      console.error('CLI execution error:', error)
      
      // Create error entry
      const errorEntry: CommandOutput = {
        command: commandLine,
        output: '',
        error: error.message ?? 'Command execution failed',
        timestamp: new Date(),
        type: 'error',
        exitCode: 1
      }

      // Update history with error
      setHistory(prev => {
        const updated = [...prev]
        const lastIndex = updated.length - 1
        if (lastIndex >= 0 && updated[lastIndex].type === 'running') {
          updated[lastIndex] = errorEntry
        } else {
          updated.push(errorEntry)
        }
        return updated
      })
      scrollToBottom()
    } finally {
      setIsExecuting(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    // Handle Enter key - Execute command
    if (e.key === 'Enter' && input.trim() && !isExecuting) {
      // Add to command history if not duplicate
      if (commandHistory[commandHistory.length - 1] !== input.trim()) {
        setCommandHistory(prev => [...prev, input.trim()])
      }
      setHistoryIndex(-1) // Reset history index
      executeCommand(input)
      setInput('')
      return
    }

    // Handle Up Arrow - Previous command in history
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      if (commandHistory.length > 0) {
        const newIndex = historyIndex === -1 
          ? commandHistory.length - 1 
          : Math.max(0, historyIndex - 1)
        setHistoryIndex(newIndex)
        setInput(commandHistory[newIndex])
      }
      return
    }

    // Handle Down Arrow - Next command in history
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      if (historyIndex >= 0) {
        const newIndex = historyIndex + 1
        if (newIndex >= commandHistory.length) {
          setHistoryIndex(-1)
          setInput('')
        } else {
          setHistoryIndex(newIndex)
          setInput(commandHistory[newIndex])
        }
      }
      return
    }

    // Handle Ctrl+C - Cancel current input
    if (e.key === 'c' && e.ctrlKey) {
      e.preventDefault()
      if (!isExecuting) {
        setInput('')
        setHistoryIndex(-1)
      }
      return
    }

    // Handle Ctrl+L - Clear screen
    if (e.key === 'l' && e.ctrlKey) {
      e.preventDefault()
      setHistory([])
      return
    }

    // Reset history index when typing
    if (e.key.length === 1 || e.key === 'Backspace' || e.key === 'Delete') {
      setHistoryIndex(-1)
    }
  }


  const formatOutput = (entry: CommandOutput) => {
    if (entry.type === 'running') {
      return '🔄 Executing...'
    }
    
    let output = entry.output
    if (entry.error && entry.error !== entry.output) {
      output = entry.error
    }
    
    return output ?? 'No output'
  }

  const getOutputColor = (entry: CommandOutput) => {
    switch (entry.type) {
      case 'error': return 'text-red-400'
      case 'success': return 'text-green-400'
      case 'info': return 'text-blue-400'
      case 'running': return 'text-yellow-400'
      default: return 'text-gray-300'
    }
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
          <span className="text-white font-medium ml-4">neuraops@core-container</span>
        </div>
        <div className="flex items-center space-x-4">
          <button
            onClick={() => setHistory([])}
            className="text-gray-400 hover:text-white text-xs bg-gray-700 px-2 py-1 rounded"
            disabled={isExecuting}
          >
            Clear
          </button>
          {commandHistory.length > 0 && (
            <div className="text-gray-400 text-xs">
              History: {commandHistory.length} commands
            </div>
          )}
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
        <div
          ref={containerRef}
          className="bg-black p-4 h-[600px] overflow-y-auto cursor-text scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-900 hover:scrollbar-thumb-gray-500"
          style={{ 
            scrollBehavior: 'smooth',
            maxHeight: '37.5rem'
          }}
        >
          {/* Command History */}
          {history.map((entry, index) => (
            <div key={`${entry.timestamp.getTime()}-${index}`} className="mb-2">
              {entry.command && (
                <div className="flex items-center space-x-2 mb-1">
                  <span className="text-green-400">neuraops@core:~$</span>
                  <span className="text-white">{entry.command}</span>
                  {entry.exitCode !== undefined && (
                    <span className={cn(
                      'text-xs px-1',
                      entry.exitCode === 0 ? 'text-green-400' : 'text-red-400'
                    )}>
                      [exit: {entry.exitCode}]
                    </span>
                  )}
                </div>
              )}
              {(entry.output || entry.error || entry.type === 'running') && (
                <div className={cn(
                  'whitespace-pre-line ml-0 mb-2',
                  getOutputColor(entry)
                )}>
                  {formatOutput(entry)}
                </div>
              )}
            </div>
          ))}

          {/* Current Input Line */}
          <div className="flex items-center space-x-2">
            <span className="text-green-400">neuraops@core:~$</span>
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              className="flex-1 bg-transparent text-white outline-none"
              placeholder={
                isExecuting 
                  ? "Executing..." 
                  : historyIndex >= 0 
                    ? "Browsing history (↑↓)" 
                    : "Type a command (↑↓ for history, Ctrl+L to clear)..."
              }
              autoFocus
              disabled={isExecuting || !isConnected}
            />
            <div className={cn(
              'w-2 h-4 animate-pulse',
              isExecuting ? 'bg-yellow-500' : 'bg-white'
            )}></div>
          </div>
        </div>
      </div>
    </div>
  )
}