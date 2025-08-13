'use client'

import React, { useState, useMemo } from 'react'
import { 
  MagnifyingGlassIcon,
  FunnelIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  EyeIcon,
  ChartBarIcon,
  ClockIcon,
  CheckCircleIcon,
  TruckIcon
} from '@heroicons/react/24/outline'
import { cn, formatCurrency, formatDateTime, getStatusColor } from '@/lib/utils'
import useOrders from '@/hooks/useOrders'
import type { Order, OrderStatus } from '@/types'

interface AdminDashboardProps {
  className?: string
}

type SortField = 'created_at' | 'total_amount' | 'status' | 'guest_id'
type SortDirection = 'asc' | 'desc'

const ORDER_STATUSES: OrderStatus[] = ['PENDING', 'CONFIRMED', 'PREPARING', 'READY', 'DELIVERED', 'CANCELLED']

export default function AdminDashboard({ className }: AdminDashboardProps) {
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<OrderStatus | 'ALL'>('ALL')
  const [sortField, setSortField] = useState<SortField>('created_at')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null)
  const [showFilters, setShowFilters] = useState(false)

  const { orders, loading, error, updateOrderStatus } = useOrders({
    pollingInterval: 15000,
    autoRefresh: true
  })

  // Filter and sort orders
  const filteredAndSortedOrders = useMemo(() => {
    let filtered = orders

    if (searchTerm) {
      const searchLower = searchTerm.toLowerCase()
      filtered = filtered.filter(order => 
        order.id.toLowerCase().includes(searchLower) ||
        order.guest_id.toLowerCase().includes(searchLower) ||
        order.order_items.some(item => 
          item.menu_item_id.toLowerCase().includes(searchLower)
        )
      )
    }

    if (statusFilter !== 'ALL') {
      filtered = filtered.filter(order => order.status === statusFilter)
    }

    filtered.sort((a, b) => {
      let aValue: string | number = a[sortField]
      let bValue: string | number = b[sortField]

      if (sortField === 'created_at') {
        aValue = new Date(aValue).getTime()
        bValue = new Date(bValue).getTime()
      }

      if (sortDirection === 'asc') {
        return aValue > bValue ? 1 : -1
      } else {
        return aValue < bValue ? 1 : -1
      }
    })

    return filtered
  }, [orders, searchTerm, statusFilter, sortField, sortDirection])

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  const handleStatusUpdate = async (orderId: string, newStatus: OrderStatus) => {
    try {
      await updateOrderStatus(orderId, newStatus)
      
      if (selectedOrder && selectedOrder.id === orderId) {
        setSelectedOrder(prev => prev ? { ...prev, status: newStatus } : null)
      }
    } catch (error) {
      console.error('Failed to update order status:', error)
    }
  }

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return null
    return sortDirection === 'asc' ? 
      <ArrowUpIcon className="h-4 w-4" /> : 
      <ArrowDownIcon className="h-4 w-4" />
  }

  const getOrderSummary = () => {
    const statusCounts = ORDER_STATUSES.reduce((acc, status) => {
      acc[status] = orders.filter(order => order.status === status).length
      return acc
    }, {} as Record<OrderStatus, number>)

    const totalRevenue = orders
      .filter(order => order.status === 'DELIVERED')
      .reduce((sum, order) => sum + order.total_amount, 0)

    return { statusCounts, totalRevenue }
  }

  const { statusCounts, totalRevenue } = getOrderSummary()

  if (loading && orders.length === 0) {
    return (
      <div className={cn('p-8', className)}>
        <div className="space-y-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="hotel-skeleton h-20 rounded-xl"></div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className={cn('space-y-8', className)}>
      {/* Enhanced Header Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="hotel-card p-6 bg-gradient-to-br from-blue-50 to-indigo-100">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium hotel-subheading">Total Orders</h3>
              <p className="text-3xl font-bold hotel-heading mt-2">{orders.length}</p>
            </div>
            <div className="w-12 h-12 bg-blue-500 rounded-xl flex items-center justify-center">
              <ChartBarIcon className="h-6 w-6 text-white" />
            </div>
          </div>
        </div>

        <div className="hotel-card p-6 bg-gradient-to-br from-yellow-50 to-amber-100">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium hotel-subheading">Active Orders</h3>
              <p className="text-3xl font-bold text-yellow-600 mt-2">
                {statusCounts.PENDING + statusCounts.CONFIRMED + statusCounts.PREPARING + statusCounts.READY}
              </p>
            </div>
            <div className="w-12 h-12 bg-yellow-500 rounded-xl flex items-center justify-center">
              <ClockIcon className="h-6 w-6 text-white" />
            </div>
          </div>
        </div>

        <div className="hotel-card p-6 bg-gradient-to-br from-green-50 to-emerald-100">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium hotel-subheading">Delivered Today</h3>
              <p className="text-3xl font-bold text-green-600 mt-2">{statusCounts.DELIVERED}</p>
            </div>
            <div className="w-12 h-12 bg-green-500 rounded-xl flex items-center justify-center">
              <TruckIcon className="h-6 w-6 text-white" />
            </div>
          </div>
        </div>

        <div className="hotel-card p-6 bg-gradient-to-br from-purple-50 to-violet-100">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium hotel-subheading">Revenue Today</h3>
              <p className="text-3xl font-bold text-purple-600 mt-2">{formatCurrency(totalRevenue)}</p>
            </div>
            <div className="w-12 h-12 bg-purple-500 rounded-xl flex items-center justify-center">
              <CheckCircleIcon className="h-6 w-6 text-white" />
            </div>
          </div>
        </div>
      </div>

      {/* Enhanced Filters */}
      <div className="hotel-card p-6">
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <MagnifyingGlassIcon className="h-5 w-5 absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search orders, guests, or items..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="hotel-input w-full pl-12"
              />
            </div>
          </div>
          
          <div className="flex gap-3">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as OrderStatus | 'ALL')}
              className="hotel-select min-w-[150px]"
            >
              <option value="ALL">All Statuses</option>
              {ORDER_STATUSES.map(status => (
                <option key={status} value={status}>
                  {status.charAt(0) + status.slice(1).toLowerCase()}
                </option>
              ))}
            </select>
            
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={cn(
                'hotel-button-secondary flex items-center gap-2',
                showFilters && 'bg-gray-100'
              )}
            >
              <FunnelIcon className="h-4 w-4" />
              Filters
            </button>
          </div>
        </div>

        {showFilters && (
          <div className="mt-6 pt-6 border-t border-gray-100">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium hotel-subheading mb-2">Sort by</label>
                <select
                  value={sortField}
                  onChange={(e) => setSortField(e.target.value as SortField)}
                  className="hotel-select w-full"
                >
                  <option value="created_at">Order Time</option>
                  <option value="total_amount">Total Amount</option>
                  <option value="status">Status</option>
                  <option value="guest_id">Guest ID</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium hotel-subheading mb-2">Direction</label>
                <select
                  value={sortDirection}
                  onChange={(e) => setSortDirection(e.target.value as SortDirection)}
                  className="hotel-select w-full"
                >
                  <option value="desc">Newest First</option>
                  <option value="asc">Oldest First</option>
                </select>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Error state */}
      {error && (
        <div className="hotel-card p-6 bg-red-50 border border-red-200">
          <p className="text-red-600 font-medium">{error}</p>
        </div>
      )}

      {/* Enhanced Orders Table */}
      <div className="hotel-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gradient-to-r from-slate-50 to-blue-50">
              <tr>
                <th 
                  onClick={() => handleSort('created_at')}
                  className="px-6 py-4 text-left text-sm font-semibold hotel-heading cursor-pointer hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    Order Time
                    <SortIcon field="created_at" />
                  </div>
                </th>
                <th className="px-6 py-4 text-left text-sm font-semibold hotel-heading">
                  Order ID
                </th>
                <th 
                  onClick={() => handleSort('guest_id')}
                  className="px-6 py-4 text-left text-sm font-semibold hotel-heading cursor-pointer hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    Guest
                    <SortIcon field="guest_id" />
                  </div>
                </th>
                <th className="px-6 py-4 text-left text-sm font-semibold hotel-heading">
                  Items
                </th>
                <th 
                  onClick={() => handleSort('total_amount')}
                  className="px-6 py-4 text-left text-sm font-semibold hotel-heading cursor-pointer hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    Total
                    <SortIcon field="total_amount" />
                  </div>
                </th>
                <th className="px-6 py-4 text-left text-sm font-semibold hotel-heading">
                  Status
                </th>
                <th className="px-6 py-4 text-left text-sm font-semibold hotel-heading">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredAndSortedOrders.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-16 text-center">
                    <div className="max-w-sm mx-auto">
                      <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <ChartBarIcon className="h-8 w-8 text-gray-400" />
                      </div>
                      <h3 className="text-lg font-semibold hotel-heading mb-2">
                        {orders.length === 0 ? 'No orders yet' : 'No orders match your filters'}
                      </h3>
                      <p className="hotel-text">
                        {orders.length === 0 
                          ? 'Orders will appear here once guests start placing them.'
                          : 'Try adjusting your search or filter criteria.'
                        }
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredAndSortedOrders.map((order) => (
                  <tr key={order.id} className="hover:bg-gradient-to-r hover:from-blue-50 hover:to-indigo-50 transition-all">
                    <td className="px-6 py-4 text-sm hotel-text">
                      {formatDateTime(order.created_at)}
                    </td>
                    <td className="px-6 py-4">
                      <span className="font-mono text-sm font-semibold hotel-heading">
                        #{order.id.slice(-8).toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="font-mono text-sm hotel-text">
                        {order.guest_id.slice(-8).toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm hotel-text">
                      {order.order_items.length} item{order.order_items.length !== 1 ? 's' : ''}
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-lg font-bold hotel-heading">
                        {formatCurrency(order.total_amount)}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <select
                        value={order.status}
                        onChange={(e) => handleStatusUpdate(order.id, e.target.value as OrderStatus)}
                        className={cn(
                          'hotel-badge text-sm font-semibold border-0 cursor-pointer',
                          `status-${order.status.toLowerCase()}`
                        )}
                      >
                        {ORDER_STATUSES.map(status => (
                          <option key={status} value={status}>
                            {status.charAt(0) + status.slice(1).toLowerCase()}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-6 py-4">
                      <button
                        onClick={() => setSelectedOrder(order)}
                        className="hotel-button-secondary p-2"
                        title="View details"
                      >
                        <EyeIcon className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Enhanced Order Details Modal */}
      {selectedOrder && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="hotel-card max-w-3xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-8 border-b border-gray-100 bg-gradient-to-r from-slate-50 to-blue-50">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-2xl font-bold hotel-heading">
                    Order #{selectedOrder.id.slice(-8).toUpperCase()}
                  </h3>
                  <p className="hotel-subheading mt-1">Order Details & Management</p>
                </div>
                <button
                  onClick={() => setSelectedOrder(null)}
                  className="hotel-button-secondary p-3 text-xl"
                >
                  ×
                </button>
              </div>
            </div>
            
            <div className="p-8 space-y-8">
              {/* Order Info Grid */}
              <div className="grid grid-cols-2 gap-6">
                <div className="hotel-card p-4">
                  <label className="block text-sm font-medium hotel-subheading mb-1">Guest ID</label>
                  <p className="font-mono font-semibold hotel-heading">{selectedOrder.guest_id}</p>
                </div>
                <div className="hotel-card p-4">
                  <label className="block text-sm font-medium hotel-subheading mb-1">Status</label>
                  <div className={cn('hotel-badge inline-flex', `status-${selectedOrder.status.toLowerCase()}`)}>
                    {selectedOrder.status}
                  </div>
                </div>
                <div className="hotel-card p-4">
                  <label className="block text-sm font-medium hotel-subheading mb-1">Order Time</label>
                  <p className="font-semibold hotel-heading">{formatDateTime(selectedOrder.created_at)}</p>
                </div>
                <div className="hotel-card p-4">
                  <label className="block text-sm font-medium hotel-subheading mb-1">Total Amount</label>
                  <p className="text-xl font-bold hotel-heading">{formatCurrency(selectedOrder.total_amount)}</p>
                </div>
              </div>

              {/* Order Items */}
              <div>
                <h4 className="text-lg font-bold hotel-heading mb-4">Order Items</h4>
                <div className="space-y-3">
                  {selectedOrder.order_items.map((item) => (
                    <div key={item.id} className="hotel-card p-4 bg-gradient-to-r from-gray-50 to-blue-50">
                      <div className="flex justify-between items-center">
                        <div>
                          <p className="font-semibold hotel-heading">Item #{item.menu_item_id}</p>
                          {item.special_notes && (
                            <p className="text-sm hotel-text italic mt-1">Note: {item.special_notes}</p>
                          )}
                        </div>
                        <div className="text-right">
                          <p className="font-semibold hotel-heading">
                            {item.quantity} × {formatCurrency(item.unit_price)}
                          </p>
                          <p className="text-lg font-bold hotel-heading">{formatCurrency(item.total_price)}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Special Requests */}
              {selectedOrder.special_requests && (
                <div className="hotel-card p-6 bg-gradient-to-r from-yellow-50 to-amber-50">
                  <h4 className="text-lg font-bold hotel-heading mb-3">Special Requests</h4>
                  <p className="hotel-text italic text-lg">"{selectedOrder.special_requests}"</p>
                </div>
              )}

              {/* Delivery Information */}
              {(selectedOrder.estimated_delivery_time || selectedOrder.delivery_notes) && (
                <div className="hotel-card p-6 bg-gradient-to-r from-green-50 to-emerald-50">
                  <h4 className="text-lg font-bold hotel-heading mb-4">Delivery Information</h4>
                  <div className="space-y-3">
                    {selectedOrder.estimated_delivery_time && (
                      <div className="flex justify-between">
                        <span className="font-medium hotel-subheading">Estimated delivery:</span>
                        <span className="hotel-text">{formatDateTime(selectedOrder.estimated_delivery_time)}</span>
                      </div>
                    )}
                    {selectedOrder.actual_delivery_time && (
                      <div className="flex justify-between">
                        <span className="font-medium hotel-subheading">Delivered at:</span>
                        <span className="hotel-text">{formatDateTime(selectedOrder.actual_delivery_time)}</span>
                      </div>
                    )}
                    {selectedOrder.delivery_notes && (
                      <div>
                        <span className="font-medium hotel-subheading">Delivery notes:</span>
                        <p className="hotel-text mt-1">{selectedOrder.delivery_notes}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}