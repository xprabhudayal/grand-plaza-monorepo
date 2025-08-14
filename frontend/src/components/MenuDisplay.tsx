'use client'

import React, { useState, useEffect } from 'react'
import { getMenuCategories, getMenuItems } from '@/lib/apiService'
import { MenuItem } from '@/types'

interface MenuDisplayProps {
  onItemSelect: (item: MenuItem) => void
  selectedItems: Set<string>
  className?: string
}

export default function MenuDisplay({ 
  onItemSelect, 
  selectedItems,
  className = ''
}: MenuDisplayProps) {
  const [categories, setCategories] = useState<any[]>([])
  const [menuItems, setMenuItems] = useState<Record<string, MenuItem[]>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeCategory, setActiveCategory] = useState<string>('')

  useEffect(() => {
    fetchMenuData()
  }, [])

  const fetchMenuData = async () => {
    try {
      setLoading(true)
      
      // Fetch categories
      const categoriesData = await getMenuCategories()
      
      // Set categories and default to first one
      setCategories(categoriesData)
      if (categoriesData.length > 0) {
        setActiveCategory(categoriesData[0].id)
      }
      
      // Fetch menu items
      const itemsData = await getMenuItems()
      
      // Group items by category
      const groupedItems: Record<string, MenuItem[]> = {}
      itemsData.forEach((item: MenuItem) => {
        if (!groupedItems[item.category_id]) {
          groupedItems[item.category_id] = []
        }
        groupedItems[item.category_id].push(item)
      })
      
      setMenuItems(groupedItems)
      setError(null)
    } catch (err) {
      console.error('Error fetching menu data:', err)
      setError('Failed to load menu data')
    } finally {
      setLoading(false)
    }
  }

  const handleCategoryChange = (categoryId: string) => {
    setActiveCategory(categoryId)
  }

  if (loading) {
    return (
      <div className={`flex items-center justify-center h-full ${className}`}>
        <div className="loading loading-spinner loading-lg"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`flex items-center justify-center h-full ${className}`}>
        <div className="text-center">
          <p className="text-error">{error}</p>
          <button 
            className="btn btn-primary mt-4"
            onClick={fetchMenuData}
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Category Tabs */};
      <div className="tabs tabs-boxed mb-4">
        {categories.map((category) => (
          <button
            key={category.id}
            className={`tab ${activeCategory === category.id ? 'tab-active' : ''}`}
            onClick={() => handleCategoryChange(category.id)}
          >
            {category.name}
          </button>
        ))}
      </div>

      {/* Menu Items */}
      <div className="flex-1 overflow-y-auto">
        {menuItems[activeCategory] ? (
          <div className="space-y-4">
            {menuItems[activeCategory].map((item) => (
              <div 
                key={item.id}
                className="card bg-base-100 shadow-md hover:shadow-lg transition-shadow"
              >
                <div className="card-body p-4">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <h3 className="font-bold text-lg">{item.name}</h3>
                      {item.description && (
                        <p className="text-sm text-gray-600 mt-1">{item.description}</p>
                      )}
                      {item.dietary && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {item.dietary.split(',').map((diet, idx) => (
                            <span key={idx} className="badge badge-xs badge-outline">
                              {diet.trim()}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="text-right ml-2">
                      <div className="font-bold text-lg">${item.price.toFixed(2)}</div>
                      <button
                        className={`btn btn-sm mt-2 ${
                          selectedItems.has(item.id) 
                            ? 'btn-success' 
                            : 'btn-primary'
                        }`}
                        onClick={() => onItemSelect(item)}
                      >
                        {selectedItems.has(item.id) ? 'Added' : 'Add'}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <p>No items available in this category</p>
          </div>
        )}
      </div>
    </div>
  )
}