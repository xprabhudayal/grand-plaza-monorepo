'use client'

import React, { useState, useEffect } from 'react'
import { 
  ChevronDownIcon, 
  ChevronUpIcon,
  ClockIcon,
  StarIcon,
  PlusIcon,
  CheckIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline'
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
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    const fetchMenuData = async () => {
      try {
        setLoading(true)
        setError(null)

        const [categories, menuItems] = await Promise.all([
          apiClient.getCategories({ is_active: true }),
          apiClient.getMenuItems({ is_available: true })
        ])

        const grouped: GroupedMenuItems = {}
        
        categories
          .sort((a, b) => a.display_order - b.display_order)
          .forEach(category => {
            grouped[category.id] = {
              category,
              items: []
            }
          })

        menuItems.forEach(item => {
          if (grouped[item.category_id]) {
            grouped[item.category_id].items.push(item)
          }
        })

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

  const filteredCategories = Object.values(menuData).filter(({ category, items }) => {
    if (!searchTerm) return true
    const searchLower = searchTerm.toLowerCase()
    return category.name.toLowerCase().includes(searchLower) ||
           items.some(item => 
             item.name.toLowerCase().includes(searchLower) ||
             item.description?.toLowerCase().includes(searchLower)
           )
  })

  const getDietaryBadgeColor = (dietary: string) => {
    if (dietary.includes('vegan')) return 'bg-green-100 text-green-800'
    if (dietary.includes('vegetarian')) return 'bg-green-100 text-green-700'
    if (dietary.includes('gluten-free')) return 'bg-blue-100 text-blue-800'
    return 'bg-gray-100 text-gray-700'
  }

  if (loading) {
    return (
      <div className={cn('p-6', className)}>
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="hotel-skeleton h-24 rounded-xl"></div>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={cn('p-6 text-center', className)}>
        <div className="text-red-500 mb-4">
          <ExclamationTriangleIcon className="h-12 w-12 mx-auto mb-2" />
          <p className="font-medium">Failed to load menu</p>
          <p className="text-sm text-gray-600">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className={cn('h-full flex flex-col', className)}>
      {/* Header */}
      <div className="p-6 border-b border-gray-100 bg-gradient-to-r from-slate-50 to-blue-50">
        <h2 className="text-2xl font-bold hotel-heading mb-2">Room Service Menu</h2>
        <p className="hotel-text text-sm mb-4">
          Tap any item to add it to your order during the call
        </p>
        
        {/* Search */}
        <div className="relative">
          <input
            type="text"
            placeholder="Search menu items..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="hotel-input w-full pl-10"
          />
          <div className="absolute left-3 top-1/2 transform -translate-y-1/2">
            <svg className="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
        </div>
      </div>

      {/* Menu Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {filteredCategories.length === 0 ? (
          <div className="text-center py-12">
            <p className="hotel-text">No menu items found</p>
          </div>
        ) : (
          filteredCategories.map(({ category, items }) => {
            const isExpanded = expandedCategories.has(category.id)
            const hasItems = items.length > 0
            const filteredItems = searchTerm 
              ? items.filter(item => 
                  item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                  item.description?.toLowerCase().includes(searchTerm.toLowerCase())
                )
              : items

            return (
              <div key={category.id} className="hotel-card overflow-hidden">
                <button
                  onClick={() => toggleCategory(category.id)}
                  className="w-full px-6 py-4 bg-gradient-to-r from-gray-50 to-blue-50 hover:from-gray-100 hover:to-blue-100 transition-all duration-300 flex items-center justify-between"
                  disabled={!hasItems}
                >
                  <div className="text-left">
                    <h3 className="text-lg font-bold hotel-heading">{category.name}</h3>
                    {category.description && (
                      <p className="hotel-text text-sm mt-1">{category.description}</p>
                    )}
                  </div>
                  {hasItems && (
                    <div className="flex items-center gap-3">
                      <div className="hotel-badge hotel-badge-blue">
                        {filteredItems.length} item{filteredItems.length !== 1 ? 's' : ''}
                      </div>
                      {isExpanded ? (
                        <ChevronUpIcon className="h-5 w-5 text-gray-400" />
                      ) : (
                        <ChevronDownIcon className="h-5 w-5 text-gray-400" />
                      )}
                    </div>
                  )}
                </button>

                {isExpanded && hasItems && (
                  <div className="divide-y divide-gray-50">
                    {filteredItems.map((item) => {
                      const isSelected = selectedItems.has(item.id)
                      
                      return (
                        <div
                          key={item.id}
                          onClick={() => handleItemClick(item)}
                          className={cn(
                            'p-6 hover:bg-gradient-to-r hover:from-blue-50 hover:to-indigo-50 cursor-pointer transition-all duration-300 group',
                            isSelected && 'bg-gradient-to-r from-yellow-50 to-amber-50 border-l-4 border-l-yellow-400',
                            !item.is_available && 'opacity-50 cursor-not-allowed'
                          )}
                        >
                          <div className="flex justify-between items-start">
                            <div className="flex-1">
                              <div className="flex items-start gap-3 mb-3">
                                <div className="flex-1">
                                  <div className="flex items-center gap-3 mb-2">
                                    <h4 className="text-lg font-semibold hotel-heading group-hover:text-blue-600 transition-colors">
                                      {item.name}
                                    </h4>
                                    {isSelected && (
                                      <div className="hotel-badge hotel-badge-gold flex items-center gap-1">
                                        <CheckIcon className="h-3 w-3" />
                                        Added
                                      </div>
                                    )}
                                  </div>
                                  
                                  {item.description && (
                                    <p className="hotel-text text-sm leading-relaxed mb-3">
                                      {item.description}
                                    </p>
                                  )}
                                  
                                  <div className="flex items-center gap-4 text-sm">
                                    <div className="flex items-center gap-1 hotel-subheading">
                                      <ClockIcon className="h-4 w-4" />
                                      {item.preparation_time} min
                                    </div>
                                    
                                    {item.dietary && (
                                      <div className="flex gap-1">
                                        {item.dietary.split(',').map((diet, index) => (
                                          <span
                                            key={index}
                                            className={cn(
                                              'px-2 py-1 rounded-full text-xs font-medium',
                                              getDietaryBadgeColor(diet.trim())
                                            )}
                                          >
                                            {diet.trim()}
                                          </span>
                                        ))}
                                      </div>
                                    )}
                                    
                                    {!item.is_available && (
                                      <span className="hotel-badge hotel-badge-red">
                                        Unavailable
                                      </span>
                                    )}
                                  </div>
                                </div>
                                
                                <div className="text-right">
                                  <div className="text-2xl font-bold hotel-heading mb-2">
                                    {formatCurrency(item.price)}
                                  </div>
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      handleItemClick(item)
                                    }}
                                    className="hotel-button-primary text-sm px-4 py-2 flex items-center gap-2"
                                    disabled={!item.is_available}
                                  >
                                    <PlusIcon className="h-4 w-4" />
                                    Add
                                  </button>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}

                {isExpanded && !hasItems && (
                  <div className="p-6 text-center hotel-text">
                    No items available in this category
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}