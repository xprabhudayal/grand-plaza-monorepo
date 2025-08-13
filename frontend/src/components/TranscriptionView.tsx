'use client'

import React, { useEffect, useRef } from 'react'
import { cn, formatTime } from '@/lib/utils'
import type { TranscriptMessage } from '@/types'

interface TranscriptionViewProps {
  messages: TranscriptMessage[]
  className?: string
  isConnected?: boolean
  isTyping?: boolean
}

export default function TranscriptionView({ 
  messages, 
  className,
  isConnected = false,
  isTyping = false
}: TranscriptionViewProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to latest message
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ 
        behavior: 'smooth',
        block: 'end'
      })
    }
  }, [messages])

  const getMessageAlignment = (speaker: 'Guest' | 'AI') => {
    return speaker === 'Guest' ? 'justify-end' : 'justify-start'
  }

  const getMessageStyle = (speaker: 'Guest' | 'AI') => {
    if (speaker === 'Guest') {
      return 'bg-blue-500 text-white ml-auto'
    }
    return 'bg-gray-100 text-gray-900 mr-auto'
  }

  const getAvatarStyle = (speaker: 'Guest' | 'AI') => {
    if (speaker === 'Guest') {
      return 'bg-blue-500 text-white'
    }
    return 'hotel-gradient text-white'
  }

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Header */}
      <div className="flex-shrink-0 border-b border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">Conversation</h3>
          <div className="flex items-center gap-2">
            <div className={cn(
              'w-2 h-2 rounded-full',
              isConnected ? 'bg-green-500' : 'bg-gray-400'
            )}></div>
            <span className="text-sm text-gray-600">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
      </div>

      {/* Messages Container */}
      <div 
        ref={containerRef}
        className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0"
      >
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="hotel-gradient rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                <span className="text-white font-bold text-xl">AI</span>
              </div>
              <p className="text-gray-600 text-sm">
                {isConnected 
                  ? "Say 'Hello' to start your conversation with our AI concierge!"
                  : "Click 'Start Room Service Call' to begin"
                }
              </p>
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <div 
                key={message.id} 
                className={cn('flex gap-3', getMessageAlignment(message.speaker))}
              >
                {message.speaker === 'AI' && (
                  <div className={cn(
                    'w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0',
                    getAvatarStyle(message.speaker)
                  )}>
                    AI
                  </div>
                )}
                
                <div className="flex flex-col max-w-xs lg:max-w-md">
                  <div className={cn(
                    'rounded-lg px-4 py-2 text-sm',
                    getMessageStyle(message.speaker)
                  )}>
                    <p className="whitespace-pre-wrap break-words">{message.text}</p>
                  </div>
                  <span className="text-xs text-gray-500 mt-1 px-1">
                    {formatTime(message.timestamp)}
                  </span>
                </div>

                {message.speaker === 'Guest' && (
                  <div className={cn(
                    'w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0',
                    getAvatarStyle(message.speaker)
                  )}>
                    You
                  </div>
                )}
              </div>
            ))}

            {/* Typing indicator */}
            {isTyping && (
              <div className="flex gap-3 justify-start">
                <div className="hotel-gradient w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white flex-shrink-0">
                  AI
                </div>
                <div className="bg-gray-100 rounded-lg px-4 py-2 text-sm mr-auto">
                  <div className="flex items-center gap-1">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                    <span className="text-gray-500 ml-2">AI is thinking...</span>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
        
        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>

      {/* Status Footer */}
      {isConnected && (
        <div className="flex-shrink-0 border-t border-gray-200 p-3">
          <p className="text-xs text-gray-500 text-center">
            Speak naturally - our AI concierge is listening and ready to help!
          </p>
        </div>
      )}
    </div>
  )
}
