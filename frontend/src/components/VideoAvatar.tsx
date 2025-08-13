'use client'

import React, { useEffect, useRef, useState } from 'react'
import { 
  MicrophoneIcon, 
  VideoCameraIcon,
  PhoneIcon,
  PhoneXMarkIcon,
  ExclamationTriangleIcon,
  SparklesIcon,
  SpeakerWaveIcon,
  SignalIcon
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
  const [audioLevel, setAudioLevel] = useState(0)

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

  // Audio level animation effect
  useEffect(() => {
    if (callState.isConnected) {
      const interval = setInterval(() => {
        setAudioLevel(Math.random() * 100)
      }, 200)
      return () => clearInterval(interval)
    }
  }, [callState.isConnected])

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

  // Mock transcript simulation for demo
  useEffect(() => {
    if (!callState.isConnected) return

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
      }, 10000)

      return () => clearInterval(interval)
    }

    const cleanup = simulateConversation()
    return cleanup
  }, [callState.isConnected, onTranscriptUpdate])

  return (
    <div className={cn('hotel-card overflow-hidden', className)}>
      {/* Enhanced Header */}
      <div className="bg-gradient-to-r from-slate-50 to-blue-50 px-6 py-4 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="hotel-gradient w-12 h-12 rounded-xl flex items-center justify-center shadow-lg">
              <SparklesIcon className="h-6 w-6 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-bold hotel-heading">AI Concierge</h3>
              <div className="flex items-center gap-2">
                <div className={cn(
                  'w-2 h-2 rounded-full transition-colors',
                  callState.isConnected ? 'bg-green-500' : 'bg-gray-400'
                )}></div>
                <span className="text-sm hotel-subheading">
                  {callState.isConnected 
                    ? `Connected - Room ${roomNumber}` 
                    : 'Ready to assist you'
                  }
                </span>
              </div>
            </div>
          </div>
          
          {callState.isConnected && (
            <div className="flex items-center gap-2">
              <SignalIcon className="h-4 w-4 text-green-500" />
              <div className="hotel-badge hotel-badge-green text-xs">
                Live
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Video Container */}
      <div className="relative aspect-video bg-gradient-to-br from-slate-900 via-blue-900 to-indigo-900">
        <div 
          ref={videoRef} 
          className="w-full h-full"
        />
        
        {/* Overlay when not connected */}
        {!callState.isConnected && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center text-white max-w-md mx-auto p-8">
              {/* Animated Avatar */}
              <div className="relative mb-8">
                <div className="w-32 h-32 hotel-gradient rounded-full flex items-center justify-center mx-auto shadow-2xl">
                  <SparklesIcon className="h-16 w-16 text-white" />
                </div>
                <div className="absolute -inset-4 rounded-full border-2 border-white/20 animate-pulse"></div>
                <div className="absolute -inset-8 rounded-full border border-white/10 animate-ping"></div>
              </div>
              
              <h4 className="text-2xl font-bold mb-3">
                {process.env.NEXT_PUBLIC_HOTEL_NAME || 'Hotel'} AI Concierge
              </h4>
              <p className="text-blue-100 mb-8 leading-relaxed">
                Your personal assistant for room service orders. I can help you browse the menu, 
                place orders, and answer any questions about your stay.
              </p>
              
              {!isConnecting ? (
                <button
                  onClick={handleStartCall}
                  className="hotel-button-primary text-lg px-8 py-4 inline-flex items-center gap-3 shadow-2xl hover:scale-105 transition-transform"
                >
                  <PhoneIcon className="h-6 w-6" />
                  Start Room Service Call
                </button>
              ) : (
                <div className="flex items-center justify-center gap-3 text-lg">
                  <div className="animate-spin rounded-full h-6 w-6 border-2 border-white border-t-transparent"></div>
                  <span>Connecting to your concierge...</span>
                </div>
              )}
              
              <div className="mt-8 flex items-center justify-center gap-6 text-sm text-blue-200">
                <div className="flex items-center gap-2">
                  <SparklesIcon className="h-4 w-4" />
                  AI Powered
                </div>
                <div className="flex items-center gap-2">
                  <SpeakerWaveIcon className="h-4 w-4" />
                  Natural Voice
                </div>
                <div className="flex items-center gap-2">
                  <SignalIcon className="h-4 w-4" />
                  24/7 Available
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Error overlay */}
        {callState.hasError && (
          <div className="absolute inset-0 flex items-center justify-center bg-red-900/90 backdrop-blur-sm">
            <div className="text-center text-white max-w-md mx-auto p-8">
              <ExclamationTriangleIcon className="h-16 w-16 mx-auto mb-4 text-red-300" />
              <h4 className="text-xl font-bold mb-3">Connection Error</h4>
              <p className="text-red-100 mb-6">
                {callState.errorMessage || 'Unable to connect to video service'}
              </p>
              <button
                onClick={handleStartCall}
                className="hotel-button-primary"
              >
                Try Again
              </button>
            </div>
          </div>
        )}

        {/* Audio level indicator */}
        {callState.isConnected && (
          <div className="absolute top-4 left-4 flex items-center gap-2 bg-black/50 backdrop-blur-sm text-white px-4 py-2 rounded-full">
            <SpeakerWaveIcon className="h-4 w-4" />
            <div className="flex items-center gap-1">
              {[...Array(5)].map((_, i) => (
                <div
                  key={i}
                  className={cn(
                    'w-1 h-4 bg-white rounded-full transition-all',
                    audioLevel > i * 20 ? 'opacity-100' : 'opacity-30'
                  )}
                />
              ))}
            </div>
          </div>
        )}

        {/* Participant count */}
        {callState.isConnected && (
          <div className="absolute top-4 right-4 bg-black/50 backdrop-blur-sm text-white px-4 py-2 rounded-full text-sm">
            {callState.participants.length + 1} participant{callState.participants.length !== 0 ? 's' : ''}
          </div>
        )}
      </div>

      {/* Enhanced Controls */}
      {callState.isConnected && (
        <div className="bg-gradient-to-r from-slate-50 to-blue-50 px-6 py-4 border-t border-gray-100">
          <div className="flex items-center justify-center gap-4">
            <button
              onClick={toggleMicrophone}
              className={cn(
                'w-12 h-12 rounded-xl flex items-center justify-center transition-all shadow-lg',
                isMicrophoneEnabled 
                  ? 'bg-white text-gray-700 hover:bg-gray-50 border-2 border-gray-200' 
                  : 'bg-red-500 text-white hover:bg-red-600 shadow-red-200'
              )}
              title={isMicrophoneEnabled ? 'Mute microphone' : 'Unmute microphone'}
            >
              <MicrophoneIcon className="h-5 w-5" />
            </button>

            <button
              onClick={toggleCamera}
              className={cn(
                'w-12 h-12 rounded-xl flex items-center justify-center transition-all shadow-lg',
                isCameraEnabled 
                  ? 'bg-white text-gray-700 hover:bg-gray-50 border-2 border-gray-200' 
                  : 'bg-red-500 text-white hover:bg-red-600 shadow-red-200'
              )}
              title={isCameraEnabled ? 'Turn off camera' : 'Turn on camera'}
            >
              <VideoCameraIcon className="h-5 w-5" />
            </button>

            <button
              onClick={handleEndCall}
              className="w-12 h-12 rounded-xl bg-red-500 text-white flex items-center justify-center hover:bg-red-600 transition-all shadow-lg shadow-red-200"
              title="End call"
            >
              <PhoneXMarkIcon className="h-5 w-5" />
            </button>
          </div>

          <div className="mt-4 text-center">
            <p className="text-sm hotel-text">
              🎤 Speak naturally - the AI can hear and respond to you
            </p>
          </div>
        </div>
      )}
    </div>
  )
}