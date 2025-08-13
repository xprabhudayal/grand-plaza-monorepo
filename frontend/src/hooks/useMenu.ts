'use client'

import { useState, useEffect, useCallback } from 'react'
import apiClient from '@/lib/apiClient'
import type { MenuItem, Category } from '@/types'

export interface UseMenuOptions {
  categoryId?: string
  isAvailable?: boolean
}

export interface UseMenuReturn {
  menuItems: MenuItem[]
  categories: Category[]
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
  getItemsByCategory: (categoryId: string) => MenuItem[]
}

export default function useMenu(options: UseMenuOptions = {}): UseMenuReturn {
  const { categoryId, isAvailable = true } = options

  const [menuItems, setMenuItems] = useState<MenuItem[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchMenu = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const [itemsResponse, categoriesResponse] = await Promise.all([
        apiClient.getMenuItems({ 
          category_id: categoryId,
          is_available: isAvailable 
        }),
        apiClient.getCategories({ is_active: true })
      ])

      setMenuItems(itemsResponse)
      setCategories(categoriesResponse.sort((a, b) => a.display_order - b.display_order))
    } catch (err) {
      const error = err as { detail?: string; message?: string }
      setError(error.detail || error.message || 'Failed to fetch menu')
      console.error('Error fetching menu:', err)
    } finally {
      setLoading(false)
    }
  }, [categoryId, isAvailable])

  const refetch = useCallback(async () => {
    await fetchMenu()
  }, [fetchMenu])

  const getItemsByCategory = useCallback((categoryId: string): MenuItem[] => {
    return menuItems.filter(item => item.category_id === categoryId)
  }, [menuItems])

  useEffect(() => {
    fetchMenu()
  }, [fetchMenu])

  return {
    menuItems,
    categories,
    loading,
    error,
    refetch,
    getItemsByCategory,
  }
}
