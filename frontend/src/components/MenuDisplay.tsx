'use client'

import React, { useState, useEffect } from 'react'
import { ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline'
import { cn, formatCurrency } from '@/lib/utils'
import apiClient from '@/lib/apiClient'
import type { MenuItem, Category } from '@/types'

interface MenuDisplayProps {
  className?: string
  onItemSelect?: (item: MenuItem) => void
  selectedItems?: Set<string>
}

interface GroupedMenuItems {
  [categoryId: string]: {
    category: Category
    items: MenuItem[]
  }
}

export default function MenuDisplay({ 
  className,
  onItemSelect,
  selectedItems = new Set()
}: MenuDisplayProps) {
  const [menuData, setMenuData] = useState<GroupedMenuItems>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set())

  useEffect(() => {
    const fetchMenuData = async () => {
      try {
        setLoading(true)
        setError(null)

        // Fetch categories and menu items in parallel
        const [categories, menuItems] = await Promise.all([
          apiClient.getCategories({ is_active: true }),
          apiClient.getMenuItems({ is_available: true })
        ])

        // Group menu items by category
        const grouped: GroupedMenuItems = {}
        
        // Initialize with categories
        categories
          .sort((a, b) => a.display_order - b.display_order)
          .forEach(category => {
            grouped[category.id] = {
              category,
              items: []
            }
          })

        // Add menu items to their respective categories
        menuItems.forEach(item => {
          if (grouped[item.category_id]) {
            grouped[item.category_id].items.push(item)
          }
        })

        // Sort items within each category by name
        Object.values(grouped).forEach(group => {
          group.items.sort((a, b) => a.name.localeCompare(b.name))
        })

        setMenuData(grouped)
        
        // Expand first category by default
        const firstCategoryId = categories[0]?.id
        if (firstCategoryId) {
          setExpandedCategories(new Set([firstCategoryId]))
        }
      } catch (err) {
        const error = err as { detail?: string; message?: string }
        setError(error.detail || error.message || 'Failed to load menu')
        console.error('Error fetching menu data:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchMenuData()
  }, [])

  const toggleCategory = (categoryId: string) => {
    setExpandedCategories(prev => {
      const newSet = new Set(prev)
      if (newSet.has(categoryId)) {
        newSet.delete(categoryId)
      } else {
        newSet.add(categoryId)
      }
      return newSet
    })
  }

  const handleItemClick = (item: MenuItem) => {
    onItemSelect?.(item)
  }

  if (loading) {
    return (
      <div className={cn('space-y-4', className)}>
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-2 text-sm text-gray-600">Loading menu...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={cn('space-y-4', className)}>
        <div className="text-center py-8">
          <p className="text-red-600 text-sm">{error}</p>
        </div>
      </div>
    )
  }

  const categories = Object.values(menuData)

  if (categories.length === 0) {
    return (
      <div className={cn('space-y-4', className)}>
        <div className="text-center py-8">
          <p className="text-gray-600 text-sm">No menu items available</p>
        </div>
      </div>
    )
  }

  return (
    <div className={cn('space-y-4', className)}>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Room Service Menu</h2>
        <p className="text-gray-600 text-sm">Tap any item to add it to your order during the call</p>
      </div>

      {categories.map(({ category, items }) => {
        const isExpanded = expandedCategories.has(category.id)
        const hasItems = items.length > 0

        return (
          <div key={category.id} className="border border-gray-200 rounded-lg overflow-hidden">
            <button
              onClick={() => toggleCategory(category.id)}
              className="w-full px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors duration-200 flex items-center justify-between"
              disabled={!hasItems}
            >
              <div className="text-left">
                <h3 className="font-semibold text-gray-900">{category.name}</h3>
                {category.description && (
                  <p className="text-sm text-gray-600 mt-1">{category.description}</p>
                )}
              </div>
              {hasItems && (
                <div className="flex items-center">
                  <span className="text-xs text-gray-500 mr-2">
                    {items.length} item{items.length !== 1 ? 's' : ''}
                  </span>
                  {isExpanded ? (
                    <ChevronUpIcon className="h-5 w-5 text-gray-400" />
                  ) : (
                    <ChevronDownIcon className="h-5 w-5 text-gray-400" />
                  )}
                </div>
              )}
            </button>

            {isExpanded && hasItems && (
              <div className="divide-y divide-gray-100">
                {items.map((item) => {
                  const isSelected = selectedItems.has(item.id)
                  
                  return (
                    <div
                      key={item.id}
                      onClick={() => handleItemClick(item)}
                      className={cn(
                        'p-4 hover:bg-gray-50 cursor-pointer transition-colors duration-200',
                        isSelected && 'bg-blue-50 border-l-4 border-l-blue-500',
                        !item.is_available && 'opacity-50 cursor-not-allowed'
                      )}
                    >
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <h4 className="font-medium text-gray-900">{item.name}</h4>
                            {item.dietary && (
                              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                {item.dietary}
                              </span>
                            )}
                          </div>
                          {item.description && (
                            <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                              {item.description}
                            </p>
                          )}
                          <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                            <span>Prep time: {item.preparation_time} min</span>
                            {!item.is_available && (
                              <span className="text-red-500 font-medium">Currently unavailable</span>
                            )}
                          </div>
                        </div>
                        <div className="ml-4 text-right">
                          <p className="font-semibold text-gray-900">
                            {formatCurrency(item.price)}
                          </p>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}

            {isExpanded && !hasItems && (
              <div className="p-4 text-center text-gray-500 text-sm">
                No items available in this category
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
