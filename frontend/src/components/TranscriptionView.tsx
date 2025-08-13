'use client'

import React, { useEffect, useRef } from 'react'
import { 
  SparklesIcon,
  UserIcon,
  SpeakerWaveIcon,
  MicrophoneIcon
} from '@heroicons/react/24/outline'
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
      return 'bg-gradient-to-r from-blue-500 to-blue-600 text-white shadow-lg shadow-blue-200'
    }
    return 'bg-gradient-to-r from-gray-50 to-blue-50 text-gray-900 border border-gray-100 shadow-sm'
  }

  const getAvatarStyle = (speaker: 'Guest' | 'AI') => {
    if (speaker === 'Guest') {
      return 'bg-gradient-to-r from-blue-500 to-blue-600 text-white shadow-lg'
    }
    return 'hotel-gradient text-white shadow-lg'
  }

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Enhanced Header */}
      <div className="flex-shrink-0 border-b border-gray-100 p-6 bg-gradient-to-r from-slate-50 to-blue-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="hotel-gradient w-10 h-10 rounded-xl flex items-center justify-center shadow-lg">
              <SparklesIcon className="h-5 w-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-bold hotel-heading">Live Conversation</h3>
              <p className="text-sm hotel-subheading">Real-time voice interaction</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className={cn(
              'flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium',
              isConnected 
                ? 'bg-green-100 text-green-700' 
                : 'bg-gray-100 text-gray-600'
            )}>
              <div className={cn(
                'w-2 h-2 rounded-full',
                isConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
              )}></div>
              {isConnected ? 'Connected' : 'Disconnected'}
            </div>
          </div>
        </div>
      </div>

      {/* Messages Container */}
      <div 
        ref={containerRef}
        className="flex-1 overflow-y-auto p-6 space-y-6 min-h-0"
      >
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md">
              <div className="relative mb-6">
                <div className="hotel-gradient rounded-full w-20 h-20 flex items-center justify-center mx-auto shadow-2xl">
                  <SparklesIcon className="h-10 w-10 text-white" />
                </div>
                <div className="absolute -inset-2 rounded-full border-2 border-yellow-200 animate-pulse"></div>
              </div>
              <h4 className="text-xl font-bold hotel-heading mb-3">
                Ready to Chat!
              </h4>
              <p className="hotel-text leading-relaxed">
                {isConnected 
                  ? "Say 'Hello' to start your conversation with our AI concierge. I'm here to help you with your room service order!"
                  : "Click 'Start Room Service Call' to begin your personalized ordering experience."
                }
              </p>
              {isConnected && (
                <div className="mt-6 flex items-center justify-center gap-4 text-sm hotel-subheading">
                  <div className="flex items-center gap-2">
                    <MicrophoneIcon className="h-4 w-4" />
                    Listening
                  </div>
                  <div className="flex items-center gap-2">
                    <SpeakerWaveIcon className="h-4 w-4" />
                    Speaking
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          <>
            {messages.map((message, index) => (
              <div 
                key={message.id} 
                className={cn(
                  'flex gap-4 animate-fade-in-up',
                  getMessageAlignment(message.speaker)
                )}
                style={{ animationDelay: `${index * 0.1}s` }}
              >
                {message.speaker === 'AI' && (
                  <div className={cn(
                    'w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold flex-shrink-0',
                    getAvatarStyle(message.speaker)
                  )}>
                    <SparklesIcon className="h-5 w-5" />
                  </div>
                )}
                
                <div className="flex flex-col max-w-xs lg:max-w-md">
                  <div className={cn(
                    'rounded-2xl px-6 py-4 text-sm leading-relaxed',
                    getMessageStyle(message.speaker)
                  )}>
                    <p className="whitespace-pre-wrap break-words">{message.text}</p>
                  </div>
                  <div className="flex items-center gap-2 mt-2 px-2">
                    <span className="text-xs hotel-subheading">
                      {formatTime(message.timestamp)}
                    </span>
                    {message.speaker === 'AI' && (
                      <div className="hotel-badge hotel-badge-gold text-xs">
                        AI Concierge
                      </div>
                    )}
                  </div>
                </div>

                {message.speaker === 'Guest' && (
                  <div className={cn(
                    'w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold flex-shrink-0',
                    getAvatarStyle(message.speaker)
                  )}>
                    <UserIcon className="h-5 w-5" />
                  </div>
                )}
              </div>
            ))}

            {/* Enhanced Typing indicator */}
            {isTyping && (
              <div className="flex gap-4 justify-start animate-fade-in">
                <div className="hotel-gradient w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold text-white flex-shrink-0 shadow-lg">
                  <SparklesIcon className="h-5 w-5" />
                </div>
                <div className="bg-gradient-to-r from-gray-50 to-blue-50 rounded-2xl px-6 py-4 text-sm mr-auto border border-gray-100 shadow-sm">
                  <div className="flex items-center gap-3">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                    <span className="hotel-subheading">AI is thinking...</span>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Enhanced Status Footer */}
      {isConnected && (
        <div className="flex-shrink-0 border-t border-gray-100 p-4 bg-gradient-to-r from-slate-50 to-blue-50">
          <div className="flex items-center justify-center gap-4 text-sm">
            <div className="flex items-center gap-2 hotel-subheading">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              Voice AI Active
            </div>
            <div className="w-px h-4 bg-gray-300"></div>
            <p className="hotel-text text-center">
              🎤 Speak naturally - I'm listening and ready to help!
            </p>
          </div>
        </div>
      )}
    </div>
  )
}