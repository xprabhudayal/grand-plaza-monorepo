'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import DailyIframe, { 
  DailyCall, 
  DailyEventObject,
  DailyParticipant,
  DailyCallOptions 
} from '@daily-co/daily-js'
import type { CallState } from '@/types'

export interface UseDailyOptions {
  roomUrl?: string
  onJoined?: () => void
  onLeft?: () => void
  onError?: (error: Error) => void
  onParticipantJoined?: (participant: DailyParticipant) => void
  onParticipantLeft?: (participant: DailyParticipant) => void
}

export interface UseDailyReturn {
  callObject: DailyCall | null
  callState: CallState
  joinCall: (options?: DailyCallOptions) => Promise<void>
  leaveCall: () => Promise<void>
  toggleMicrophone: () => void
  toggleCamera: () => void
  isMicrophoneEnabled: boolean
  isCameraEnabled: boolean
}

export default function useDaily(options: UseDailyOptions = {}): UseDailyReturn {
  const {
    roomUrl,
    onJoined,
    onLeft,
    onError,
    onParticipantJoined,
    onParticipantLeft
  } = options

  const [callObject, setCallObject] = useState<DailyCall | null>(null)
  const [callState, setCallState] = useState<CallState>({
    isConnected: false,
    isJoining: false,
    hasError: false,
    participants: []
  })
  const [isMicrophoneEnabled, setIsMicrophoneEnabled] = useState(true)
  const [isCameraEnabled, setIsCameraEnabled] = useState(true)

  const callObjectRef = useRef<DailyCall | null>(null)

  // Initialize Daily call object
  useEffect(() => {
    if (!callObjectRef.current) {
      const daily = DailyIframe.createCallObject({
        audioSource: true,
        videoSource: true,
      })
      
      callObjectRef.current = daily
      setCallObject(daily)
    }

    return () => {
      if (callObjectRef.current) {
        callObjectRef.current.destroy()
        callObjectRef.current = null
      }
    }
  }, [])

  // Set up event listeners
  useEffect(() => {
    if (!callObject) return

    const handleJoinedMeeting = (event?: DailyEventObject) => {
      console.log('Joined meeting:', event)
      setCallState(prev => ({
        ...prev,
        isConnected: true,
        isJoining: false,
        hasError: false,
        localParticipant: event?.participants?.local
      }))
      onJoined?.()
    }

    const handleLeftMeeting = (event?: DailyEventObject) => {
      console.log('Left meeting:', event)
      setCallState(prev => ({
        ...prev,
        isConnected: false,
        isJoining: false,
        participants: [],
        localParticipant: undefined
      }))
      onLeft?.()
    }

    const handleParticipantJoined = (event?: DailyEventObject) => {
      if (event?.participant) {
        console.log('Participant joined:', event.participant)
        setCallState(prev => ({
          ...prev,
          participants: [...prev.participants.filter((p: unknown) => (p as any).session_id !== event.participant.session_id), event.participant]
        }))
        onParticipantJoined?.(event.participant)
      }
    }

    const handleParticipantLeft = (event?: DailyEventObject) => {
      if (event?.participant) {
        console.log('Participant left:', event.participant)
        setCallState(prev => ({
          ...prev,
          participants: prev.participants.filter((p: unknown) => (p as any).session_id !== event.participant.session_id)
        }))
        onParticipantLeft?.(event.participant)
      }
    }

    const handleError = (event?: DailyEventObject) => {
      console.error('Daily call error:', event)
      const error = new Error(event?.errorMsg || 'Unknown call error')
      setCallState(prev => ({
        ...prev,
        hasError: true,
        errorMessage: error.message,
        isJoining: false
      }))
      onError?.(error)
    }

    const handleCameraError = (event?: DailyEventObject) => {
      console.warn('Camera error:', event)
      setIsCameraEnabled(false)
    }

    const handleParticipantUpdated = (event?: DailyEventObject) => {
      if (event?.participant) {
        setCallState(prev => ({
          ...prev,
          participants: prev.participants.map((p: unknown) => 
            (p as any).session_id === event.participant.session_id ? event.participant : p
          )
        }))
      }
    }

    // Add event listeners
    callObject
      .on('joined-meeting', handleJoinedMeeting)
      .on('left-meeting', handleLeftMeeting)
      .on('participant-joined', handleParticipantJoined)
      .on('participant-left', handleParticipantLeft)
      .on('participant-updated', handleParticipantUpdated)
      .on('error', handleError)
      .on('camera-error', handleCameraError)

    return () => {
      // Remove event listeners
      callObject
        .off('joined-meeting', handleJoinedMeeting)
        .off('left-meeting', handleLeftMeeting)
        .off('participant-joined', handleParticipantJoined)
        .off('participant-left', handleParticipantLeft)
        .off('participant-updated', handleParticipantUpdated)
        .off('error', handleError)
        .off('camera-error', handleCameraError)
    }
  }, [callObject, onJoined, onLeft, onError, onParticipantJoined, onParticipantLeft])

  const joinCall = useCallback(async (options: DailyCallOptions = {}) => {
    if (!callObject || callState.isConnected || callState.isJoining) {
      return
    }

    try {
      setCallState(prev => ({ ...prev, isJoining: true, hasError: false, errorMessage: undefined }))
      
      const url = options.url || roomUrl || process.env.NEXT_PUBLIC_DAILY_ROOM_URL
      if (!url) {
        throw new Error('No room URL provided')
      }

      await callObject.join({
        url,
        userName: options.userName || 'Guest',
        ...options
      })
    } catch (error) {
      console.error('Failed to join call:', error)
      setCallState(prev => ({
        ...prev,
        isJoining: false,
        hasError: true,
        errorMessage: error instanceof Error ? error.message : 'Failed to join call'
      }))
      throw error
    }
  }, [callObject, callState.isConnected, callState.isJoining, roomUrl])

  const leaveCall = useCallback(async () => {
    if (!callObject || !callState.isConnected) {
      return
    }

    try {
      await callObject.leave()
    } catch (error) {
      console.error('Failed to leave call:', error)
      throw error
    }
  }, [callObject, callState.isConnected])

  const toggleMicrophone = useCallback(() => {
    if (!callObject) return
    
    const newState = !isMicrophoneEnabled
    callObject.setLocalAudio(newState)
    setIsMicrophoneEnabled(newState)
  }, [callObject, isMicrophoneEnabled])

  const toggleCamera = useCallback(() => {
    if (!callObject) return
    
    const newState = !isCameraEnabled
    callObject.setLocalVideo(newState)
    setIsCameraEnabled(newState)
  }, [callObject, isCameraEnabled])

  return {
    callObject,
    callState,
    joinCall,
    leaveCall,
    toggleMicrophone,
    toggleCamera,
    isMicrophoneEnabled,
    isCameraEnabled,
  }
}
