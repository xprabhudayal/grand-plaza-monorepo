'use client'

import React, { useState, useEffect } from 'react'
import { 
  ChatBubbleLeftRightIcon,
  ClipboardDocumentListIcon,
  ShoppingCartIcon,
  Bars3Icon,
  XMarkIcon,
  SparklesIcon,
  PhoneIcon,
  StarIcon
} from '@heroicons/react/24/outline'
import MenuDisplay from '@/components/MenuDisplay'
import TranscriptionView from '@/components/TranscriptionView'
import OrderSummaryCard from '@/components/OrderSummaryCard'
import { getGuestByRoom } from '@/lib/apiService'

type TabType = 'menu' | 'conversation' | 'order'

export default function GuestInterface() {
  const [activeTab, setActiveTab] = useState<TabType>('menu')
  const [transcriptMessages, setTranscriptMessages] = useState<any[]>([])
  const [isCallConnected, setIsCallConnected] = useState(false)
  const [cart, setCart] = useState<any>({ items: [], total: 0 })
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [roomNumber, setRoomNumber] = useState('101')
  const [guestName, setGuestName] = useState('Guest')
  const [loadingGuest, setLoadingGuest] = useState(true)

  // Load guest information based on room number
  useEffect(() => {
    const loadGuestInfo = async () => {
      try {
        setLoadingGuest(true)
        const guest = await getGuestByRoom(roomNumber)
        if (guest) {
          setGuestName(guest.name)
        } else {
          setGuestName('Guest')
        }
      } catch (error) {
        console.error('Error loading guest info:', error)
        setGuestName('Guest')
      } finally {
        setLoadingGuest(false)
      }
    }

    loadGuestInfo()
  }, [roomNumber])

  // Update cart total when items change
  useEffect(() => {
    const total = cart.items.reduce((sum: number, item: any) => 
      sum + (item.quantity * item.menu_item.price), 0
    )
    setCart((prev: any) => ({ ...prev, total }))
  }, [cart.items])

  // Auto-switch to conversation tab when call connects
  useEffect(() => {
    if (isCallConnected && activeTab === 'menu') {
      setActiveTab('conversation')
    }
  }, [isCallConnected, activeTab])

  const handleTranscriptUpdate = (messages: any[]) => {
    setTranscriptMessages(messages)
  }

  const handleCallStateChange = (connected: boolean) => {
    setIsCallConnected(connected)
  }

  const handleMenuItemSelect = (item: any) => {
    setCart((prev: any) => {
      const existingItemIndex = prev.items.findIndex(
        (cartItem: any) => cartItem.menu_item_id === item.id
      )

      let newItems: any[]
      if (existingItemIndex >= 0) {
        newItems = prev.items.map((cartItem: any, index: number) => 
          index === existingItemIndex 
            ? { ...cartItem, quantity: cartItem.quantity + 1 }
            : cartItem
        )
      } else {
        const newItem = {
          menu_item_id: item.id,
          menu_item: item,
          quantity: 1
        }
        newItems = [...prev.items, newItem]
      }

      return { ...prev, items: newItems }
    })
  }

  const tabs = [
    {
      id: 'menu' as TabType,
      name: 'Menu',
      icon: ClipboardDocumentListIcon,
      count: undefined,
      description: 'Browse our selection'
    },
    {
      id: 'conversation' as TabType,
      name: 'AI Chat',
      icon: ChatBubbleLeftRightIcon,
      count: transcriptMessages.length > 0 ? transcriptMessages.length : undefined,
      description: 'Voice conversation'
    },
    {
      id: 'order' as TabType,
      name: 'Your Order',
      icon: ShoppingCartIcon,
      count: cart.items.length > 0 ? cart.items.length : undefined,
      description: 'Review & confirm'
    }
  ]

  const renderTabContent = () => {
    switch (activeTab) {
      case 'menu':
        return (
          <MenuDisplay
            onItemSelect={handleMenuItemSelect}
            selectedItems={new Set(cart.items.map((item: any) => item.menu_item_id))}
          />
        )
      case 'conversation':
        return (
          <TranscriptionView
            messages={transcriptMessages}
            isConnected={isCallConnected}
          />
        )
      case 'order':
        return (
          <OrderSummaryCard
            order={null}
            cart={cart}
          />
        )
      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-white/20 bg-white/80 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-20">
            <div className="flex items-center space-x-4">
              <div className="bg-gradient-to-r from-amber-500 to-orange-500 w-14 h-14 rounded-2xl flex items-center justify-center shadow-lg">
                <SparklesIcon className="h-8 w-8 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  Grand Plaza Hotel
                </h1>
                <p className="text-sm text-gray-600 flex items-center gap-2">
                  <PhoneIcon className="h-4 w-4" />
                  AI Room Service Concierge
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-6">
              <div className="hidden sm:block text-right">
                <div className="badge badge-warning gap-2">
                  Room {roomNumber}
                </div>
                {loadingGuest ? (
                  <div className="loading loading-spinner loading-xs"></div>
                ) : (
                  <p className="text-sm text-gray-600 mt-1">Welcome, {guestName}</p>
                )}
              </div>
              
              {/* Mobile menu button */}
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="lg:hidden btn btn-ghost btn-circle"
              >
                {sidebarOpen ? (
                  <XMarkIcon className="h-6 w-6" />
                ) : (
                  <Bars3Icon className="h-6 w-6" />
                )}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Welcome Banner */}
        <div className="card bg-base-100 shadow-xl mb-8">
          <div className="card-body text-center">
            <div className="flex items-center justify-center gap-2 mb-4">
              <StarIcon className="h-8 w-8 text-yellow-500" />
              <StarIcon className="h-8 w-8 text-yellow-500" />
              <StarIcon className="h-8 w-8 text-yellow-500" />
              <StarIcon className="h-8 w-8 text-yellow-500" />
              <StarIcon className="h-8 w-8 text-yellow-500" />
            </div>
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              Experience Luxury Room Service
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Order from our curated menu using our AI-powered voice assistant. 
              Simply start a call and speak naturally to place your order.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-5 gap-8 min-h-[calc(100vh-20rem)]">
          {/* Left Column: Video Avatar */}
          <div className="xl:col-span-3">
            <div className="card bg-base-100 shadow-xl h-full min-h-[500px]">
              <div className="card-body flex flex-col items-center justify-center">
                <div className="text-center mb-6">
                  <div className="avatar placeholder mb-4">
                    <div className="bg-neutral text-neutral-content rounded-full w-24 h-24">
                      <SparklesIcon className="h-12 w-12" />
                    </div>
                  </div>
                  <h3 className="text-2xl font-bold">AI Concierge</h3>
                  <p className="text-gray-600">Ready to take your order</p>
                </div>
                
                <div className="flex flex-col gap-4 w-full max-w-md">
                  {!isCallConnected ? (
                    <>
                      <button 
                        className="btn btn-primary btn-lg"
                        onClick={() => setIsCallConnected(true)}
                      >
                        <PhoneIcon className="h-5 w-5" />
                        Start Room Service Call
                      </button>
                      <p className="text-sm text-gray-500 text-center">
                        Click to begin your voice ordering experience
                      </p>
                    </>
                  ) : (
                    <>
                      <button 
                        className="btn btn-error btn-lg"
                        onClick={() => setIsCallConnected(false)}
                      >
                        <PhoneIcon className="h-5 w-5" />
                        End Call
                      </button>
                      <p className="text-sm text-gray-500 text-center">
                        Currently connected to AI concierge
                      </p>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Tabbed Interface */}
          <div className="xl:col-span-2">
            <div className="card bg-base-100 shadow-xl h-full min-h-[500px] flex flex-col">
              {/* Tab Navigation */}
              <div className="tabs tabs-lifted">
                {tabs.map((tab) => {
                  const Icon = tab.icon
                  const isActive = activeTab === tab.id
                  
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`tab flex-1 ${isActive ? 'tab-active' : ''}`}
                    >
                      <div className="flex items-center gap-2">
                        <Icon className="h-5 w-5" />
                        {tab.count !== undefined && (
                          <span className="badge badge-sm">
                            {tab.count}
                          </span>
                        )}
                        <span>{tab.name}</span>
                      </div>
                    </button>
                  )
                })}
              </div>

              {/* Tab Content */}
              <div className="flex-1 overflow-hidden p-4">
                {renderTabContent()}
              </div>
            </div>
          </div>
        </div>

        {/* Call to Action */}
        {!isCallConnected && (
          <div className="card bg-base-100 shadow-xl mt-8">
            <div className="card-body text-center">
              <div className="max-w-md mx-auto">
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  Ready to Order?
                </h3>
                <p className="text-gray-600 mb-4">
                  Click "Start Room Service Call" above to begin your personalized ordering experience with our AI concierge.
                </p>
                <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
                  <SparklesIcon className="h-4 w-4" />
                  Available 24/7 • Instant Response • Natural Conversation
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Mobile Sidebar */}
      {sidebarOpen && (
        <div className="lg:hidden fixed inset-0 z-50 bg-black/50 backdrop-blur-sm">
          <div className="fixed inset-y-0 right-0 w-full max-w-sm bg-base-100 shadow-2xl">
            <div className="flex items-center justify-between p-6 border-b border-base-200">
              <h2 className="text-xl font-semibold">Room Service</h2>
              <button
                onClick={() => setSidebarOpen(false)}
                className="btn btn-ghost btn-circle"
              >
                <XMarkIcon className="h-6 w-6" />
              </button>
            </div>
            <div className="p-6 h-full overflow-y-auto">
              {renderTabContent()}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}