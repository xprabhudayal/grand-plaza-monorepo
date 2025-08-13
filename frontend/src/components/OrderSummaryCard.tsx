'use client'

import React from 'react'
import { 
  ClockIcon, 
  CheckCircleIcon, 
  ExclamationCircleIcon,
  TruckIcon 
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
  // Show cart if no order is provided
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
      <div className={cn('bg-white rounded-lg border border-gray-200 p-6', className)}>
        <div className="text-center">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <TruckIcon className="h-8 w-8 text-gray-400" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No Active Order</h3>
          <p className="text-gray-600 text-sm">
            Start a room service call to place your order
          </p>
        </div>
      </div>
    )
  }

  if (displayCart) {
    return (
      <div className={cn('bg-white rounded-lg border border-gray-200 p-6', className)}>
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
            <TruckIcon className="h-6 w-6 text-blue-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Current Selection</h3>
            <p className="text-sm text-gray-600">Items ready to order</p>
          </div>
        </div>

        {cart.items.length === 0 ? (
          <p className="text-gray-600 text-sm text-center py-4">
            No items selected yet
          </p>
        ) : (
          <>
            <div className="space-y-3 mb-4">
              {cart.items.map((item, index) => (
                <div key={`${item.menu_item_id}-${index}`} className="flex justify-between items-start">
                  <div className="flex-1">
                    <p className="font-medium text-gray-900">{item.menu_item.name}</p>
                    {item.special_notes && (
                      <p className="text-sm text-gray-600 italic">Note: {item.special_notes}</p>
                    )}
                  </div>
                  <div className="text-right ml-3">
                    <p className="font-medium">
                      {item.quantity} × {formatCurrency(item.menu_item.price)}
                    </p>
                    <p className="text-sm text-gray-600">
                      = {formatCurrency(item.quantity * item.menu_item.price)}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            <div className="border-t pt-3">
              <div className="flex justify-between items-center">
                <span className="font-semibold text-gray-900">Total</span>
                <span className="font-semibold text-lg">{formatCurrency(cart.total)}</span>
              </div>
            </div>
          </>
        )}
      </div>
    )
  }

  // Display order
  if (!order) return null

  return (
    <div className={cn('bg-white rounded-lg border border-gray-200 p-6', className)}>
      {/* Order Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className={cn(
          'w-10 h-10 rounded-full flex items-center justify-center',
          getStatusColor(order.status)
        )}>
          {getStatusIcon(order.status)}
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            Order #{order.id.slice(-8).toUpperCase()}
          </h3>
          <p className="text-sm text-gray-600">
            {getStatusMessage(order.status)}
          </p>
        </div>
      </div>

      {/* Order Items */}
      <div className="space-y-3 mb-4">
        {order.order_items.map((item) => (
          <div key={item.id} className="flex justify-between items-start">
            <div className="flex-1">
              <p className="font-medium text-gray-900">Item #{item.menu_item_id}</p>
              {item.special_notes && (
                <p className="text-sm text-gray-600 italic">Note: {item.special_notes}</p>
              )}
            </div>
            <div className="text-right ml-3">
              <p className="font-medium">
                {item.quantity} × {formatCurrency(item.unit_price)}
              </p>
              <p className="text-sm text-gray-600">
                = {formatCurrency(item.total_price)}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Order Total */}
      <div className="border-t pt-3 mb-4">
        <div className="flex justify-between items-center">
          <span className="font-semibold text-gray-900">Total</span>
          <span className="font-semibold text-lg">{formatCurrency(order.total_amount)}</span>
        </div>
      </div>

      {/* Special Requests */}
      {order.special_requests && (
        <div className="mb-4">
          <p className="text-sm font-medium text-gray-900 mb-1">Special Requests:</p>
          <p className="text-sm text-gray-600 italic">&ldquo;{order.special_requests}&rdquo;</p>
        </div>
      )}

      {/* Delivery Information */}
      {showEstimatedTime && (
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-2">
            <ClockIcon className="h-4 w-4 text-gray-500" />
            <span className="text-sm font-medium text-gray-900">Delivery Information</span>
          </div>
          
          {order.estimated_delivery_time && (
            <p className="text-sm text-gray-600 mb-1">
              <span className="font-medium">Estimated delivery:</span>{' '}
              {formatDateTime(order.estimated_delivery_time)}
            </p>
          )}
          
          {order.actual_delivery_time && (
            <p className="text-sm text-gray-600">
              <span className="font-medium">Delivered at:</span>{' '}
              {formatDateTime(order.actual_delivery_time)}
            </p>
          )}
          
          {order.delivery_notes && (
            <p className="text-sm text-gray-600 mt-2">
              <span className="font-medium">Delivery notes:</span> {order.delivery_notes}
            </p>
          )}
        </div>
      )}

      {/* Order Metadata */}
      <div className="mt-4 pt-3 border-t text-xs text-gray-500">
        <p>Ordered: {formatDateTime(order.created_at)}</p>
        <p>Payment: {order.payment_status}</p>
      </div>
    </div>
  )
}
