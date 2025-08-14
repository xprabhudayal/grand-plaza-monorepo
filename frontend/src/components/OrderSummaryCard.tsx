'use client'

import React, { useState } from 'react'
import apiClient from '@/lib/apiClient'
import { Cart } from '@/types'

interface OrderSummaryCardProps {
  order: any
  cart: Cart
  className?: string
}

export default function OrderSummaryCard({ 
  order, 
  cart,
  className = ''
}: OrderSummaryCardProps) {
  const [isPlacingOrder, setIsPlacingOrder] = useState(false)
  const [orderPlaced, setOrderPlaced] = useState(false)
  const [orderId, setOrderId] = useState<string | null>(null)

  const handlePlaceOrder = async () => {
    if (cart.items.length === 0) return
    
    try {
      setIsPlacingOrder(true)
      
      // In a real implementation, you would get the actual guest ID
      // For now, we'll use a placeholder
      const guestId = "guest_placeholder"
      
      // Prepare order data according to API specification
      const orderData = {
        guest_id: guestId,
        special_requests: "",
        delivery_notes: "",
        order_items: cart.items.map(item => ({
          menu_item_id: item.menu_item_id,
          quantity: item.quantity,
          special_notes: ""
        }))
      }

      const response = await apiClient.post('/orders', orderData)
      
      // Handle successful order creation
      setOrderId(response.data.id)
      setOrderPlaced(true)
      alert(`Order placed successfully! Order ID: ${response.data.id}`)
    } catch (error: any) {
      console.error('Error placing order:', error)
      alert(`Failed to place order: ${error.response?.data?.detail || error.message || 'Please try again.'}`)
    } finally {
      setIsPlacingOrder(false)
    }
  }

  const handleClearCart = () => {
    // In a real implementation, this would update your cart state
    alert('Cart cleared! In a real implementation, this would update your cart state.')
  }

  if (orderPlaced) {
    return (
      <div className={`flex flex-col items-center justify-center h-full ${className}`}>
        <div className="text-center">
          <div className="bg-green-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h3 className="text-xl font-bold text-gray-900 mb-2">Order Placed Successfully!</h3>
          <p className="text-gray-600 mb-4">Your order has been received and is being processed.</p>
          <div className="bg-gray-100 rounded-lg p-4 mb-4">
            <p className="text-sm text-gray-500">Order ID</p>
            <p className="font-mono text-lg">{orderId}</p>
          </div>
          <button 
            className="btn btn-primary"
            onClick={() => {
              setOrderPlaced(false)
              setOrderId(null)
              handleClearCart()
            }}
          >
            Place Another Order
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className={`flex flex-col h-full ${className}`}>
      <div className="flex-1 overflow-y-auto">
        {cart.items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-8">
            <div className="bg-gray-200 border-2 border-dashed rounded-xl w-16 h-16 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Your cart is empty</h3>
            <p className="text-gray-500 max-w-xs">
              Add items from the menu to start building your order.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="space-y-3">
              {cart.items.map((item) => (
                <div key={item.menu_item_id} className="flex justify-between items-center p-3 bg-base-100 rounded-lg">
                  <div>
                    <div className="font-medium">{item.menu_item.name}</div>
                    <div className="text-sm text-gray-500">Qty: {item.quantity}</div>
                  </div>
                  <div className="font-medium">
                    ${(item.menu_item.price * item.quantity).toFixed(2)}
                  </div>
                </div>
              ))}
            </div>
            
            <div className="divider"></div>
            
            <div className="space-y-2">
              <div className="flex justify-between">
                <span>Subtotal</span>
                <span>${cart.total.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span>Tax</span>
                <span>${(cart.total * 0.08).toFixed(2)}</span>
              </div>
              <div className="flex justify-between font-bold text-lg">
                <span>Total</span>
                <span>${(cart.total * 1.08).toFixed(2)}</span>
              </div>
            </div>
            
            <div className="alert alert-info mt-4">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" className="stroke-current flex-shrink-0 w-6 h-6"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
              <span>Estimated delivery: 20-30 minutes</span>
            </div>
          </div>
        )}
      </div>
      
      {cart.items.length > 0 && (
        <div className="border-t border-base-200 p-4 space-y-3">
          <button 
            className={`btn btn-primary btn-block ${isPlacingOrder ? 'loading' : ''}`}
            onClick={handlePlaceOrder}
            disabled={isPlacingOrder}
          >
            {isPlacingOrder ? 'Placing Order...' : 'Place Order'}
          </button>
          <button 
            className="btn btn-outline btn-block"
            onClick={handleClearCart}
          >
            Clear Cart
          </button>
        </div>
      )}
    </div>
  )
}