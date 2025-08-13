'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import apiClient from '@/lib/apiClient'
import type { Order, OrderStatus } from '@/types'

export interface UseOrdersOptions {
  pollingInterval?: number
  guestId?: string
  status?: OrderStatus
  autoRefresh?: boolean
}

export interface UseOrdersReturn {
  orders: Order[]
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
  createOrder: (orderData: unknown) => Promise<Order>
  updateOrderStatus: (orderId: string, status: OrderStatus) => Promise<Order>
  getOrderById: (orderId: string) => Promise<Order>
}

export default function useOrders(options: UseOrdersOptions = {}): UseOrdersReturn {
  const {
    pollingInterval = 30000, // 30 seconds default
    guestId,
    status,
    autoRefresh = true
  } = options

  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  const mountedRef = useRef(true)

  const fetchOrders = useCallback(async () => {
    if (!mountedRef.current) return

    try {
      setLoading(true)
      setError(null)

      const params: any = {}
      if (guestId) params.guest_id = guestId
      if (status) params.status = status

      const fetchedOrders = await apiClient.getOrders(params)
      
      if (mountedRef.current) {
        setOrders(fetchedOrders)
      }
    } catch (err) {
      const error = err as { detail?: string; message?: string }
      if (mountedRef.current) {
        setError(error.detail || error.message || 'Failed to fetch orders')
        console.error('Error fetching orders:', err)
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false)
      }
    }
  }, [guestId, status])

  const refetch = useCallback(async () => {
    await fetchOrders()
  }, [fetchOrders])

  const createOrder = useCallback(async (orderData: unknown): Promise<Order> => {
    try {
      setError(null)
      const newOrder = await apiClient.createOrder(orderData as Parameters<typeof apiClient.createOrder>[0])
      
      if (mountedRef.current) {
        setOrders(prev => [newOrder, ...prev])
      }
      
      return newOrder
    } catch (err) {
      const error = err as { detail?: string; message?: string }
      const errorMessage = error.detail || error.message || 'Failed to create order'
      if (mountedRef.current) {
        setError(errorMessage)
      }
      console.error('Error creating order:', err)
      throw new Error(errorMessage)
    }
  }, [])

  const updateOrderStatus = useCallback(async (orderId: string, newStatus: OrderStatus): Promise<Order> => {
    try {
      setError(null)
      const updatedOrder = await apiClient.updateOrderStatus(orderId, { status: newStatus })
      
      if (mountedRef.current) {
        setOrders(prev => 
          prev.map(order => 
            order.id === orderId ? updatedOrder : order
          )
        )
      }
      
      return updatedOrder
    } catch (err) {
      const error = err as { detail?: string; message?: string }
      const errorMessage = error.detail || error.message || 'Failed to update order status'
      if (mountedRef.current) {
        setError(errorMessage)
      }
      console.error('Error updating order status:', err)
      throw new Error(errorMessage)
    }
  }, [])

  const getOrderById = useCallback(async (orderId: string): Promise<Order> => {
    try {
      setError(null)
      const order = await apiClient.getOrderById(orderId)
      
      if (mountedRef.current) {
        setOrders(prev => {
          const existingIndex = prev.findIndex(o => o.id === orderId)
          if (existingIndex >= 0) {
            const newOrders = [...prev]
            newOrders[existingIndex] = order
            return newOrders
          } else {
            return [order, ...prev]
          }
        })
      }
      
      return order
    } catch (err) {
      const error = err as { detail?: string; message?: string }
      const errorMessage = error.detail || error.message || 'Failed to fetch order'
      if (mountedRef.current) {
        setError(errorMessage)
      }
      console.error('Error fetching order by ID:', err)
      throw new Error(errorMessage)
    }
  }, [])

  // Initial fetch
  useEffect(() => {
    fetchOrders()
  }, [fetchOrders])

  // Set up polling
  useEffect(() => {
    if (!autoRefresh) return

    intervalRef.current = setInterval(() => {
      fetchOrders()
    }, pollingInterval)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [fetchOrders, pollingInterval, autoRefresh])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      mountedRef.current = false
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [])

  return {
    orders,
    loading,
    error,
    refetch,
    createOrder,
    updateOrderStatus,
    getOrderById,
  }
}
