'use client'

import { useState, useCallback } from 'react'
import type { Cart, CartItem, MenuItem } from '@/types'

export interface UseCartReturn {
  cart: Cart
  addItem: (menuItem: MenuItem, quantity?: number, specialNotes?: string) => void
  removeItem: (menuItemId: string) => void
  updateQuantity: (menuItemId: string, quantity: number) => void
  clearCart: () => void
  getItemCount: () => number
  getTotalPrice: () => number
}

export default function useCart(): UseCartReturn {
  const [cart, setCart] = useState<Cart>({ items: [], total: 0 })

  const addItem = useCallback((menuItem: MenuItem, quantity = 1, specialNotes?: string) => {
    setCart(prev => {
      const existingItemIndex = prev.items.findIndex(
        item => item.menu_item_id === menuItem.id
      )

      let newItems: CartItem[]
      if (existingItemIndex >= 0) {
        // Update existing item
        newItems = prev.items.map((item, index) =>
          index === existingItemIndex
            ? { 
                ...item, 
                quantity: item.quantity + quantity,
                special_notes: specialNotes || item.special_notes
              }
            : item
        )
      } else {
        // Add new item
        const newItem: CartItem = {
          menu_item_id: menuItem.id,
          menu_item: menuItem,
          quantity,
          special_notes: specialNotes
        }
        newItems = [...prev.items, newItem]
      }

      const total = newItems.reduce((sum, item) => 
        sum + (item.quantity * item.menu_item.price), 0
      )

      return { items: newItems, total }
    })
  }, [])

  const removeItem = useCallback((menuItemId: string) => {
    setCart(prev => {
      const newItems = prev.items.filter(item => item.menu_item_id !== menuItemId)
      const total = newItems.reduce((sum, item) => 
        sum + (item.quantity * item.menu_item.price), 0
      )
      return { items: newItems, total }
    })
  }, [])

  const updateQuantity = useCallback((menuItemId: string, quantity: number) => {
    if (quantity <= 0) {
      removeItem(menuItemId)
      return
    }

    setCart(prev => {
      const newItems = prev.items.map(item =>
        item.menu_item_id === menuItemId
          ? { ...item, quantity }
          : item
      )
      const total = newItems.reduce((sum, item) => 
        sum + (item.quantity * item.menu_item.price), 0
      )
      return { items: newItems, total }
    })
  }, [removeItem])

  const clearCart = useCallback(() => {
    setCart({ items: [], total: 0 })
  }, [])

  const getItemCount = useCallback(() => {
    return cart.items.reduce((sum, item) => sum + item.quantity, 0)
  }, [cart.items])

  const getTotalPrice = useCallback(() => {
    return cart.total
  }, [cart.total])

  return {
    cart,
    addItem,
    removeItem,
    updateQuantity,
    clearCart,
    getItemCount,
    getTotalPrice,
  }
}
