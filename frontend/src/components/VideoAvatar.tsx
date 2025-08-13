'use client'

import React, { useEffect, useRef, useState } from 'react'
import { 
  MicrophoneIcon, 
  VideoCameraIcon,
  PhoneIcon,
  PhoneXMarkIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'
import useDaily from '@/hooks/useDaily'
import type { TranscriptMessage } from '@/types'

interface VideoAvatarProps {
  className?: string
  onTranscriptUpdate?: (messages: TranscriptMessage[]) => void
  onCallStateChange?: (connected: boolean) => void
  roomNumber?: string
  guestName?: string
}

export default function VideoAvatar({
  className,
  onTranscriptUpdate,
  onCallStateChange,
  roomNumber = '101',
  guestName = 'Guest'
}: VideoAvatarProps) {
  const videoRef = useRef<HTMLDivElement>(null)
  const [transcriptMessages, setTranscriptMessages] = useState<TranscriptMessage[]>([])
  const [isConnecting, setIsConnecting] = useState(false)

  const {
    callObject,
    callState,
    joinCall,
    leaveCall,
    toggleMicrophone,
    toggleCamera,
    isMicrophoneEnabled,
    isCameraEnabled,
  } = useDaily({
    roomUrl: process.env.NEXT_PUBLIC_DAILY_ROOM_URL,
    onJoined: () => {
      console.log('Successfully joined call')
      setIsConnecting(false)
      onCallStateChange?.(true)
      
      // Add welcome message
      const welcomeMessage: TranscriptMessage = {
        id: `welcome-${Date.now()}`,
        speaker: 'AI',
        text: `Hello! Welcome to ${process.env.NEXT_PUBLIC_HOTEL_NAME || 'Grand Plaza Hotel'} room service. I'm your AI concierge assistant. How may I help you today?`,
        timestamp: new Date()
      }
      
      setTranscriptMessages([welcomeMessage])
      onTranscriptUpdate?.([welcomeMessage])
    },
    onLeft: () => {
      console.log('Left call')
      setIsConnecting(false)
      onCallStateChange?.(false)
    },
    onError: (error) => {
      console.error('Call error:', error)
      setIsConnecting(false)
      onCallStateChange?.(false)
    },
    onParticipantJoined: (participant) => {
      console.log('Participant joined:', participant)
    },
    onParticipantLeft: (participant) => {
      console.log('Participant left:', participant)
    }
  })

  // Set up video container when call object is ready
  useEffect(() => {
    if (callObject && videoRef.current && callState.isConnected) {
      try {
        callObject.join({
          url: process.env.NEXT_PUBLIC_DAILY_ROOM_URL,
          userName: `${guestName} (Room ${roomNumber})`,
        })
      } catch (error) {
        console.error('Error setting up video:', error)
      }
    }
  }, [callObject, callState.isConnected, guestName, roomNumber])

  const handleStartCall = async () => {
    if (callState.isConnected || isConnecting) return
    
    try {
      setIsConnecting(true)
      await joinCall({
        userName: `${guestName} (Room ${roomNumber})`,
      })
    } catch (error) {
      console.error('Failed to start call:', error)
      setIsConnecting(false)
    }
  }

  const handleEndCall = async () => {
    if (!callState.isConnected) return
    
    try {
      await leaveCall()
      setTranscriptMessages([])
      onTranscriptUpdate?.([])
    } catch (error) {
      console.error('Failed to end call:', error)
    }
  }

  // Mock transcript simulation for demo purposes
  // In a real implementation, this would come from the voice pipeline
  useEffect(() => {
    if (!callState.isConnected) return

    // Simulate AI responses for demo
    const simulateConversation = () => {
      const responses = [
        "I'd be happy to help you with room service today. What would you like to order?",
        "Great choice! I'll add that to your order. Would you like anything else?",
        "Perfect! Your order has been placed and will be delivered within 30-45 minutes.",
        "Is there anything specific you'd like me to note for the kitchen?",
        "Thank you for your order! Have a wonderful day!"
      ]

      let responseIndex = 0
      const interval = setInterval(() => {
        if (responseIndex < responses.length && callState.isConnected) {
          const newMessage: TranscriptMessage = {
            id: `ai-${Date.now()}-${responseIndex}`,
            speaker: 'AI',
            text: responses[responseIndex],
            timestamp: new Date()
          }
          
          setTranscriptMessages(prev => {
            const updated = [...prev, newMessage]
            onTranscriptUpdate?.(updated)
            return updated
          })
          
          responseIndex++
        } else {
          clearInterval(interval)
        }
      }, 10000) // Every 10 seconds

      return () => clearInterval(interval)
    }

    const cleanup = simulateConversation()
    return cleanup
  }, [callState.isConnected, onTranscriptUpdate])

  return (
    <div className={cn('bg-white rounded-lg border border-gray-200 overflow-hidden', className)}>
      {/* Header */}
      <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-gray-900">AI Concierge</h3>
            <p className="text-sm text-gray-600">
              {callState.isConnected 
                ? `Connected - Room ${roomNumber}` 
                : 'Ready to assist you'
              }
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className={cn(
              'w-2 h-2 rounded-full',
              callState.isConnected ? 'bg-green-500' : 'bg-gray-400'
            )}></div>
            <span className="text-xs text-gray-600">
              {callState.isConnected ? 'Live' : 'Offline'}
            </span>
          </div>
        </div>
      </div>

      {/* Video Container */}
      <div className="relative aspect-video bg-gray-900">
        <div 
          ref={videoRef} 
          className="w-full h-full"
        />
        
        {/* Overlay when not connected */}
        {!callState.isConnected && (
          <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-blue-900 to-purple-900">
            <div className="text-center text-white">
              <div className="w-24 h-24 hotel-gradient rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl font-bold">AI</span>
              </div>
              <h4 className="text-xl font-semibold mb-2">
                {process.env.NEXT_PUBLIC_HOTEL_NAME || 'Hotel'} AI Concierge
              </h4>
              <p className="text-sm opacity-90 mb-6 max-w-sm">
                Your personal assistant for room service orders. I can help you browse the menu, 
                place orders, and answer any questions about your stay.
              </p>
              
              {!isConnecting ? (
                <button
                  onClick={handleStartCall}
                  className="inline-flex items-center gap-2 bg-white text-gray-900 px-6 py-3 rounded-full font-medium hover:bg-gray-100 transition-colors"
                >
                  <PhoneIcon className="h-5 w-5" />
                  Start Room Service Call
                </button>
              ) : (
                <div className="flex items-center justify-center gap-2">
                  <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent"></div>
                  <span>Connecting...</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Error overlay */}
        {callState.hasError && (
          <div className="absolute inset-0 flex items-center justify-center bg-red-900 bg-opacity-90">
            <div className="text-center text-white">
              <ExclamationTriangleIcon className="h-12 w-12 mx-auto mb-4" />
              <h4 className="text-lg font-semibold mb-2">Connection Error</h4>
              <p className="text-sm opacity-90 mb-4">
                {callState.errorMessage || 'Unable to connect to video service'}
              </p>
              <button
                onClick={handleStartCall}
                className="bg-white text-red-900 px-4 py-2 rounded-lg font-medium hover:bg-gray-100 transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        )}

        {/* Participant count indicator */}
        {callState.isConnected && (
          <div className="absolute top-4 left-4 bg-black bg-opacity-50 text-white px-3 py-1 rounded-full text-sm">
            {callState.participants.length + 1} participant{callState.participants.length !== 0 ? 's' : ''}
          </div>
        )}
      </div>

      {/* Controls */}
      {callState.isConnected && (
        <div className="bg-gray-50 px-4 py-3 border-t border-gray-200">
          <div className="flex items-center justify-center gap-4">
            <button
              onClick={toggleMicrophone}
              className={cn(
                'w-10 h-10 rounded-full flex items-center justify-center transition-colors',
                isMicrophoneEnabled 
                  ? 'bg-gray-200 text-gray-700 hover:bg-gray-300' 
                  : 'bg-red-500 text-white hover:bg-red-600'
              )}
              title={isMicrophoneEnabled ? 'Mute microphone' : 'Unmute microphone'}
            >
              <MicrophoneIcon className="h-5 w-5" />
            </button>

            <button
              onClick={toggleCamera}
              className={cn(
                'w-10 h-10 rounded-full flex items-center justify-center transition-colors',
                isCameraEnabled 
                  ? 'bg-gray-200 text-gray-700 hover:bg-gray-300' 
                  : 'bg-red-500 text-white hover:bg-red-600'
              )}
              title={isCameraEnabled ? 'Turn off camera' : 'Turn on camera'}
            >
              <VideoCameraIcon className="h-5 w-5" />
            </button>

            <button
              onClick={handleEndCall}
              className="w-10 h-10 rounded-full bg-red-500 text-white flex items-center justify-center hover:bg-red-600 transition-colors"
              title="End call"
            >
              <PhoneXMarkIcon className="h-5 w-5" />
            </button>
          </div>

          <div className="mt-3 text-center">
            <p className="text-xs text-gray-600">
              Speak naturally - the AI can hear and respond to you
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
