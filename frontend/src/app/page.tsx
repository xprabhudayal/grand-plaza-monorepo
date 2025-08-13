'use client'

import React, { useState, useEffect } from 'react'
import { 
  ChatBubbleBottomCenterTextIcon,
  ClipboardDocumentListIcon,
  ShoppingCartIcon,
  Bars3Icon,
  XMarkIcon
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
  const [roomNumber] = useState('101') // This would come from auth/context in real app
  const [guestName] = useState('Guest') // This would come from auth/context in real app

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
    // Add item to cart or increase quantity
    setCart(prev => {
      const existingItemIndex = prev.items.findIndex(
        cartItem => cartItem.menu_item_id === item.id
      )

      let newItems: CartItem[]
      if (existingItemIndex >= 0) {
        // Increase quantity
        newItems = prev.items.map((cartItem, index) => 
          index === existingItemIndex 
            ? { ...cartItem, quantity: cartItem.quantity + 1 }
            : cartItem
        )
      } else {
        // Add new item
        const newItem: CartItem = {
          menu_item_id: item.id,
          menu_item: item,
          quantity: 1
        }
        newItems = [...prev.items, newItem]
      }

      return { ...prev, items: newItems }
    })

    // Show a brief feedback that item was added
    // TODO: Add toast notification
  }

  const tabs = [
    {
      id: 'menu' as TabType,
      name: 'Menu',
      icon: ClipboardDocumentListIcon,
      count: undefined
    },
    {
      id: 'conversation' as TabType,
      name: 'Conversation',
      icon: ChatBubbleBottomCenterTextIcon,
      count: transcriptMessages.length > 0 ? transcriptMessages.length : undefined
    },
    {
      id: 'order' as TabType,
      name: 'Order',
      icon: ShoppingCartIcon,
      count: cart.items.length > 0 ? cart.items.length : undefined
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
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <div className="hotel-gradient w-10 h-10 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-lg">H</span>
              </div>
              <div className="ml-3">
                <h1 className="text-xl font-bold text-gray-900">
                  {process.env.NEXT_PUBLIC_HOTEL_NAME || 'Grand Plaza Hotel'}
                </h1>
                <p className="text-sm text-gray-600">Room Service</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="hidden sm:block text-right">
                <p className="text-sm font-medium text-gray-900">Room {roomNumber}</p>
                <p className="text-xs text-gray-600">{guestName}</p>
              </div>
              
              {/* Mobile menu button */}
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="lg:hidden p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100"
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

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[calc(100vh-8rem)]">
          {/* Left Column: Video Avatar */}
          {/* FIX: Added min-h-0 to constrain the flex container within the grid cell */}
          <div className="flex flex-col min-h-0">
            <VideoAvatar
              onTranscriptUpdate={handleTranscriptUpdate}
              onCallStateChange={handleCallStateChange}
              roomNumber={roomNumber}
              guestName={guestName}
              className="flex-1"
            />
          </div>

          {/* Right Column: Tabbed Interface */}
          {/* FIX: Added min-h-0 to constrain the flex container within the grid cell */}
          <div className="flex flex-col bg-white rounded-lg border border-gray-200 overflow-hidden min-h-0">
            {/* Tab Navigation */}
            <div className="border-b border-gray-200">
              <nav className="flex">
                {tabs.map((tab) => {
                  const Icon = tab.icon
                  const isActive = activeTab === tab.id
                  
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={cn(
                        'flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors',
                        isActive
                          ? 'border-blue-500 text-blue-600 bg-blue-50'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      )}
                    >
                      <Icon className="h-5 w-5" />
                      <span className="hidden sm:inline">{tab.name}</span>
                      {tab.count !== undefined && (
                        <span className={cn(
                          'inline-flex items-center justify-center px-2 py-1 text-xs font-bold rounded-full',
                          isActive 
                            ? 'bg-blue-600 text-white' 
                            : 'bg-gray-100 text-gray-600'
                        )}>
                          {tab.count}
                        </span>
                      )}
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

        {/* Mobile Sidebar Overlay */}
        {sidebarOpen && (
          <div className="lg:hidden fixed inset-0 z-50 bg-black bg-opacity-50">
            <div className="fixed inset-y-0 right-0 w-80 bg-white shadow-xl">
              <div className="flex items-center justify-between p-4 border-b border-gray-200">
                <h2 className="text-lg font-semibold">Menu & Orders</h2>
                <button
                  onClick={() => setSidebarOpen(false)}
                  className="p-2 rounded-md text-gray-400 hover:text-gray-500"
                >
                  <XMarkIcon className="h-6 w-6" />
                </button>
              </div>
              <div className="p-4 h-full overflow-y-auto">
                {renderTabContent()}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}