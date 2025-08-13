'use client'

import React from 'react'
import { 
  ClockIcon, 
  CheckCircleIcon, 
  ExclamationCircleIcon,
  TruckIcon,
  ShoppingBagIcon,
  CurrencyDollarIcon,
  SparklesIcon,
  MinusIcon,
  PlusIcon
} from '@heroicons/react/24/outline'
import { cn, formatCurrency, formatDateTime, getStatusColor } from '@/lib/utils'
import type { Order, Cart } from '@/types'

interface OrderSummaryCardProps {
  order?: Order | null
  cart?: Cart | null
  className?: string
  showEstimatedTime?: boolean
}

export default function OrderSummaryCard({ 
  order, 
  cart,
  className,
  showEstimatedTime = true
}: OrderSummaryCardProps) {
  const displayCart = !order && cart

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'pending':
        return <ClockIcon className="h-5 w-5" />
      case 'confirmed':
        return <CheckCircleIcon className="h-5 w-5" />
      case 'preparing':
        return <ClockIcon className="h-5 w-5" />
      case 'ready':
        return <CheckCircleIcon className="h-5 w-5" />
      case 'delivered':
        return <TruckIcon className="h-5 w-5" />
      case 'cancelled':
        return <ExclamationCircleIcon className="h-5 w-5" />
      default:
        return <ClockIcon className="h-5 w-5" />
    }
  }

  const getStatusMessage = (status: string) => {
    switch (status.toLowerCase()) {
      case 'pending':
        return 'Order received and pending confirmation'
      case 'confirmed':
        return 'Order confirmed and being prepared'
      case 'preparing':
        return 'Your order is being prepared'
      case 'ready':
        return 'Order ready for delivery'
      case 'delivered':
        return 'Order has been delivered'
      case 'cancelled':
        return 'Order has been cancelled'
      default:
        return 'Order status unknown'
    }
  }

  if (!order && !displayCart) {
    return (
      <div className={cn('h-full flex flex-col', className)}>
        {/* Header */}
        <div className="p-6 border-b border-gray-100 bg-gradient-to-r from-slate-50 to-blue-50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gray-100 rounded-xl flex items-center justify-center">
              <ShoppingBagIcon className="h-5 w-5 text-gray-400" />
            </div>
            <div>
              <h3 className="text-lg font-bold hotel-heading">Your Order</h3>
              <p className="text-sm hotel-subheading">No active order</p>
            </div>
          </div>
        </div>

        {/* Empty State */}
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center max-w-sm">
            <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <TruckIcon className="h-10 w-10 text-gray-400" />
            </div>
            <h4 className="text-xl font-bold hotel-heading mb-3">No Active Order</h4>
            <p className="hotel-text leading-relaxed">
              Start a room service call to place your order and track it here in real-time.
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (displayCart) {
    return (
      <div className={cn('h-full flex flex-col', className)}>
        {/* Header */}
        <div className="p-6 border-b border-gray-100 bg-gradient-to-r from-slate-50 to-blue-50">
          <div className="flex items-center gap-3">
            <div className="hotel-gradient w-10 h-10 rounded-xl flex items-center justify-center shadow-lg">
              <ShoppingBagIcon className="h-5 w-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-bold hotel-heading">Your Selection</h3>
              <p className="text-sm hotel-subheading">
                {cart.items.length} item{cart.items.length !== 1 ? 's' : ''} ready to order
              </p>
            </div>
          </div>
        </div>

        {/* Cart Content */}
        <div className="flex-1 overflow-y-auto">
          {cart.items.length === 0 ? (
            <div className="flex items-center justify-center h-full p-6">
              <div className="text-center">
                <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <ShoppingBagIcon className="h-8 w-8 text-gray-400" />
                </div>
                <p className="hotel-text">No items selected yet</p>
                <p className="text-sm hotel-subheading mt-1">
                  Browse the menu and add items to get started
                </p>
              </div>
            </div>
          ) : (
            <div className="p-6 space-y-4">
              {cart.items.map((item, index) => (
                <div key={`${item.menu_item_id}-${index}`} className="hotel-card p-4">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <h4 className="font-semibold hotel-heading mb-1">{item.menu_item.name}</h4>
                      {item.special_notes && (
                        <p className="text-sm hotel-text italic mb-2">
                          Note: {item.special_notes}
                        </p>
                      )}
                      <div className="flex items-center gap-4 text-sm hotel-subheading">
                        <span>Qty: {item.quantity}</span>
                        <span>{formatCurrency(item.menu_item.price)} each</span>
                      </div>
                    </div>
                    <div className="text-right ml-4">
                      <div className="text-lg font-bold hotel-heading">
                        {formatCurrency(item.quantity * item.menu_item.price)}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Total */}
        {cart.items.length > 0 && (
          <div className="border-t border-gray-100 p-6 bg-gradient-to-r from-slate-50 to-blue-50">
            <div className="flex justify-between items-center mb-4">
              <span className="text-lg font-bold hotel-heading">Total</span>
              <span className="text-2xl font-bold hotel-heading">{formatCurrency(cart.total)}</span>
            </div>
            <div className="hotel-badge hotel-badge-blue w-full text-center py-2">
              Ready to order via voice call
            </div>
          </div>
        )}
      </div>
    )
  }

  // Display order
  if (!order) return null

  return (
    <div className={cn('h-full flex flex-col', className)}>
      {/* Order Header */}
      <div className="p-6 border-b border-gray-100 bg-gradient-to-r from-slate-50 to-blue-50">
        <div className="flex items-center gap-3 mb-4">
          <div className={cn(
            'w-12 h-12 rounded-xl flex items-center justify-center shadow-lg',
            getStatusColor(order.status)
          )}>
            {getStatusIcon(order.status)}
          </div>
          <div>
            <h3 className="text-lg font-bold hotel-heading">
              Order #{order.id.slice(-8).toUpperCase()}
            </h3>
            <p className="text-sm hotel-subheading">
              {getStatusMessage(order.status)}
            </p>
          </div>
        </div>
        
        <div className={cn(
          'hotel-badge text-sm font-semibold',
          `status-${order.status.toLowerCase()}`
        )}>
          {order.status}
        </div>
      </div>

      {/* Order Items */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {order.order_items.map((item) => (
          <div key={item.id} className="hotel-card p-4">
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <h4 className="font-semibold hotel-heading mb-1">
                  Item #{item.menu_item_id}
                </h4>
                {item.special_notes && (
                  <p className="text-sm hotel-text italic mb-2">
                    Note: {item.special_notes}
                  </p>
                )}
                <div className="flex items-center gap-4 text-sm hotel-subheading">
                  <span>Qty: {item.quantity}</span>
                  <span>{formatCurrency(item.unit_price)} each</span>
                </div>
              </div>
              <div className="text-right ml-4">
                <div className="text-lg font-bold hotel-heading">
                  {formatCurrency(item.total_price)}
                </div>
              </div>
            </div>
          </div>
        ))}

        {/* Special Requests */}
        {order.special_requests && (
          <div className="hotel-card p-4 bg-gradient-to-r from-blue-50 to-indigo-50">
            <h4 className="font-semibold hotel-heading mb-2 flex items-center gap-2">
              <SparklesIcon className="h-4 w-4" />
              Special Requests
            </h4>
            <p className="hotel-text italic">"{order.special_requests}"</p>
          </div>
        )}

        {/* Delivery Information */}
        {showEstimatedTime && (
          <div className="hotel-card p-4 bg-gradient-to-r from-green-50 to-emerald-50">
            <div className="flex items-center gap-2 mb-3">
              <TruckIcon className="h-5 w-5 text-green-600" />
              <span className="font-semibold hotel-heading">Delivery Information</span>
            </div>
            
            {order.estimated_delivery_time && (
              <p className="text-sm hotel-text mb-2">
                <span className="font-medium">Estimated delivery:</span>{' '}
                {formatDateTime(order.estimated_delivery_time)}
              </p>
            )}
            
            {order.actual_delivery_time && (
              <p className="text-sm hotel-text mb-2">
                <span className="font-medium">Delivered at:</span>{' '}
                {formatDateTime(order.actual_delivery_time)}
              </p>
            )}
            
            {order.delivery_notes && (
              <p className="text-sm hotel-text">
                <span className="font-medium">Delivery notes:</span> {order.delivery_notes}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Order Total & Footer */}
      <div className="border-t border-gray-100 p-6 bg-gradient-to-r from-slate-50 to-blue-50">
        <div className="flex justify-between items-center mb-4">
          <span className="text-lg font-bold hotel-heading">Total Amount</span>
          <span className="text-2xl font-bold hotel-heading">{formatCurrency(order.total_amount)}</span>
        </div>
        
        <div className="space-y-2 text-xs hotel-subheading">
          <div className="flex justify-between">
            <span>Ordered:</span>
            <span>{formatDateTime(order.created_at)}</span>
          </div>
          <div className="flex justify-between">
            <span>Payment:</span>
            <span className={cn(
              'hotel-badge text-xs',
              order.payment_status === 'PAID' ? 'hotel-badge-green' : 'hotel-badge-gray'
            )}>
              {order.payment_status}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}