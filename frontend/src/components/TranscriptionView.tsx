'use client'

import React, { useEffect, useRef } from 'react'
import { ChatBubbleLeftRightIcon, UserIcon, ComputerDesktopIcon } from '@heroicons/react/24/outline'

interface TranscriptionViewProps {
  messages: any[]
  isConnected: boolean
  className?: string
}

export default function TranscriptionView({ 
  messages, 
  isConnected,
  className = ''
}: TranscriptionViewProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <div className={`flex flex-col h-full ${className}`}>
      <div className="flex-1 overflow-y-auto space-y-4 p-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <ChatBubbleLeftRightIcon className="h-12 w-12 text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              {isConnected ? 'Conversation Started' : 'No Conversation Yet'}
            </h3>
            <p className="text-gray-500 max-w-xs">
              {isConnected 
                ? 'Speak naturally to order food from our menu. Your conversation will appear here.' 
                : 'Start a call to begin your voice ordering experience.'}
            </p>
          </div>
        ) : (
          messages.map((message) => (
            <div 
              key={message.id} 
              className={`chat ${message.role === 'user' ? 'chat-end' : 'chat-start'}`}
            >
              <div className="chat-image avatar">
                <div className="w-10 rounded-full">
                  {message.role === 'user' ? (
                    <UserIcon className="h-10 w-10 bg-primary text-white p-2 rounded-full" />
                  ) : (
                    <ComputerDesktopIcon className="h-10 w-10 bg-secondary text-white p-2 rounded-full" />
                  )}
                </div>
              </div>
              <div className="chat-header">
                {message.role === 'user' ? 'You' : 'AI Concierge'}
              </div>
              <div className={`chat-bubble ${message.role === 'user' ? 'chat-bubble-primary' : 'chat-bubble-secondary'}`}>
                {message.content}
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>
      
      {isConnected && (
        <div className="border-t border-base-200 p-4">
          <div className="flex items-center">
            <div className="flex space-x-1">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse delay-75"></div>
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse delay-150"></div>
            </div>
            <span className="ml-2 text-sm text-gray-600">Listening...</span>
          </div>
        </div>
      )}
    </div>
  )
}