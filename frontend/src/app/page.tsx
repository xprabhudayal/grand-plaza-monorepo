'use client'

import React, { useState, useEffect } from 'react'
import { 
  ChatBubbleBottomCenterTextIcon,
  ClipboardDocumentListIcon,
  ShoppingCartIcon,
  Bars3Icon,
  XMarkIcon,
  SparklesIcon,
  PhoneIcon
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'
import VideoAvatar from '@/components/VideoAvatar'
import MenuDisplay from '@/components/MenuDisplay'
import TranscriptionView from '@/components/TranscriptionView'
import OrderSummaryCard from '@/components/OrderSummaryCard'
import type { TranscriptMessage, MenuItem, Cart, CartItem } from '@/types'

type TabType = 'menu' | 'conversation' | 'order'

export default function GuestInterface() {
  const [activeTab, setActiveTab] = useState<TabType>('menu')
  const [transcriptMessages, setTranscriptMessages] = useState<TranscriptMessage[]>([])
  const [isCallConnected, setIsCallConnected] = useState(false)
  const [cart, setCart] = useState<Cart>({ items: [], total: 0 })
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [roomNumber] = useState('101')
  const [guestName] = useState('Guest')

  // Update cart total when items change
  useEffect(() => {
    const total = cart.items.reduce((sum, item) => 
      sum + (item.quantity * item.menu_item.price), 0
    )
    setCart(prev => ({ ...prev, total }))
  }, [cart.items])

  // Auto-switch to conversation tab when call connects
  useEffect(() => {
    if (isCallConnected && activeTab === 'menu') {
      setActiveTab('conversation')
    }
  }, [isCallConnected, activeTab])

  const handleTranscriptUpdate = (messages: TranscriptMessage[]) => {
    setTranscriptMessages(messages)
  }

  const handleCallStateChange = (connected: boolean) => {
    setIsCallConnected(connected)
  }

  const handleMenuItemSelect = (item: MenuItem) => {
    setCart(prev => {
      const existingItemIndex = prev.items.findIndex(
        cartItem => cartItem.menu_item_id === item.id
      )

      let newItems: CartItem[]
      if (existingItemIndex >= 0) {
        newItems = prev.items.map((cartItem, index) => 
          index === existingItemIndex 
            ? { ...cartItem, quantity: cartItem.quantity + 1 }
            : cartItem
        )
      } else {
        const newItem: CartItem = {
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
      icon: ChatBubbleBottomCenterTextIcon,
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
            selectedItems={new Set(cart.items.map(item => item.menu_item_id))}
            className="h-full"
          />
        )
      case 'conversation':
        return (
          <TranscriptionView
            messages={transcriptMessages}
            isConnected={isCallConnected}
            className="h-full"
          />
        )
      case 'order':
        return (
          <OrderSummaryCard
            order={null}
            cart={cart}
            className="h-full"
          />
        )
      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      {/* Elegant Header */}
      <header className="hotel-glass sticky top-0 z-40 border-b border-white/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-20">
            <div className="flex items-center space-x-4">
              <div className="hotel-gradient w-14 h-14 rounded-2xl flex items-center justify-center shadow-lg">
                <SparklesIcon className="h-8 w-8 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold hotel-heading">
                  {process.env.NEXT_PUBLIC_HOTEL_NAME || 'Grand Plaza Hotel'}
                </h1>
                <p className="text-sm hotel-subheading flex items-center gap-2">
                  <PhoneIcon className="h-4 w-4" />
                  AI Room Service Concierge
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-6">
              <div className="hidden sm:block text-right">
                <div className="hotel-badge hotel-badge-gold">
                  Room {roomNumber}
                </div>
                <p className="text-sm hotel-text mt-1">Welcome, {guestName}</p>
              </div>
              
              {/* Mobile menu button */}
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="lg:hidden hotel-button-secondary p-3"
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
        <div className="hotel-card p-8 mb-8 animate-fade-in-up">
          <div className="text-center">
            <h2 className="text-3xl font-bold hotel-heading mb-4">
              Experience Luxury Room Service
            </h2>
            <p className="text-lg hotel-text max-w-2xl mx-auto">
              Order from our curated menu using our AI-powered voice assistant. 
              Simply start a call and speak naturally to place your order.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-5 gap-8 min-h-[calc(100vh-20rem)]">
          {/* Left Column: Video Avatar - Takes more space */}
          <div className="xl:col-span-3 animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
            <VideoAvatar
              onTranscriptUpdate={handleTranscriptUpdate}
              onCallStateChange={handleCallStateChange}
              roomNumber={roomNumber}
              guestName={guestName}
              className="h-full min-h-[500px]"
            />
          </div>

          {/* Right Column: Tabbed Interface */}
          <div className="xl:col-span-2 animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
            <div className="hotel-card overflow-hidden h-full min-h-[500px] flex flex-col">
              {/* Enhanced Tab Navigation */}
              <div className="border-b border-gray-100 bg-gray-50/50">
                <nav className="flex">
                  {tabs.map((tab) => {
                    const Icon = tab.icon
                    const isActive = activeTab === tab.id
                    
                    return (
                      <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={cn(
                          'flex-1 flex flex-col items-center justify-center gap-2 px-4 py-4 text-sm font-medium border-b-3 transition-all duration-300',
                          isActive
                            ? 'border-yellow-400 text-yellow-600 bg-yellow-50/50'
                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-200 hover:bg-gray-50'
                        )}
                      >
                        <div className="flex items-center gap-2">
                          <Icon className="h-5 w-5" />
                          {tab.count !== undefined && (
                            <span className={cn(
                              'hotel-badge text-xs',
                              isActive ? 'hotel-badge-gold' : 'hotel-badge-gray'
                            )}>
                              {tab.count}
                            </span>
                          )}
                        </div>
                        <div className="text-center">
                          <div className="font-semibold">{tab.name}</div>
                          <div className="text-xs opacity-75 hidden sm:block">{tab.description}</div>
                        </div>
                      </button>
                    )
                  })}
                </nav>
              </div>

              {/* Tab Content */}
              <div className="flex-1 overflow-hidden">
                {renderTabContent()}
              </div>
            </div>
          </div>
        </div>

        {/* Call to Action */}
        {!isCallConnected && (
          <div className="hotel-card p-6 mt-8 text-center animate-fade-in-up" style={{ animationDelay: '0.3s' }}>
            <div className="max-w-md mx-auto">
              <h3 className="text-xl font-semibold hotel-heading mb-2">
                Ready to Order?
              </h3>
              <p className="hotel-text mb-4">
                Click "Start Room Service Call" above to begin your personalized ordering experience with our AI concierge.
              </p>
              <div className="flex items-center justify-center gap-2 text-sm hotel-subheading">
                <SparklesIcon className="h-4 w-4" />
                Available 24/7 • Instant Response • Natural Conversation
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Enhanced Mobile Sidebar */}
      {sidebarOpen && (
        <div className="lg:hidden fixed inset-0 z-50 bg-black/50 backdrop-blur-sm">
          <div className="fixed inset-y-0 right-0 w-full max-w-sm hotel-glass shadow-2xl">
            <div className="flex items-center justify-between p-6 border-b border-white/20">
              <h2 className="text-xl font-semibold hotel-heading">Room Service</h2>
              <button
                onClick={() => setSidebarOpen(false)}
                className="hotel-button-secondary p-2"
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