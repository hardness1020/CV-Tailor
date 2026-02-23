import React, { useState, KeyboardEvent } from 'react'
import { X } from 'lucide-react'
import { cn } from '@/utils/cn'

interface TagInputProps {
  label?: string
  placeholder?: string
  value: string[]
  onChange: (tags: string[]) => void
  suggestions?: string[]
  error?: string
  helperText?: string
  validate?: (tag: string) => string | true
}

export const TagInput: React.FC<TagInputProps> = ({
  label,
  placeholder,
  value,
  onChange,
  suggestions = [],
  error,
  helperText,
  validate
}) => {
  const [inputValue, setInputValue] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [validationError, setValidationError] = useState<string>('')

  const filteredSuggestions = suggestions.filter(
    suggestion =>
      suggestion.toLowerCase().includes(inputValue.toLowerCase()) &&
      !value.includes(suggestion)
  )

  const addTag = (tag: string) => {
    const trimmedTag = tag.trim()
    if (!trimmedTag || value.includes(trimmedTag)) return

    // Validate tag if validator provided
    if (validate) {
      const result = validate(trimmedTag)
      if (result !== true) {
        setValidationError(result)
        return
      }
    }

    setValidationError('')
    onChange([...value, trimmedTag])
    setInputValue('')
    setShowSuggestions(false)
  }

  const removeTag = (index: number) => {
    const newTags = value.filter((_, i) => i !== index)
    onChange(newTags)
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      addTag(inputValue)
    } else if (e.key === 'Backspace' && !inputValue && value.length > 0) {
      removeTag(value.length - 1)
    }
  }

  const handleSuggestionClick = (suggestion: string) => {
    addTag(suggestion)
  }

  return (
    <div className="space-y-1">
      {label && (
        <label className="block text-sm font-medium text-gray-700">
          {label}
        </label>
      )}

      <div className="relative">
        <div className={cn(
          'min-h-[42px] w-full px-3 py-2 border rounded-md focus-within:ring-1 flex flex-wrap items-center gap-1',
          error || validationError
            ? 'border-red-300 focus-within:border-red-500 focus-within:ring-red-500'
            : 'border-gray-300 focus-within:border-blue-500 focus-within:ring-blue-500'
        )}>
          {value.map((tag, index) => (
            <span
              key={index}
              className="inline-flex items-center px-2 py-1 rounded text-sm bg-blue-100 text-blue-800"
            >
              {tag}
              <button
                type="button"
                onClick={() => removeTag(index)}
                className="ml-1 text-blue-600 hover:text-blue-800 focus:outline-none"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}

          <input
            type="text"
            value={inputValue}
            onChange={(e) => {
              setInputValue(e.target.value)
              setShowSuggestions(e.target.value.length > 0)
              setValidationError('')
            }}
            onKeyDown={handleKeyDown}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            placeholder={value.length === 0 ? placeholder : ''}
            className="flex-1 min-w-[120px] border-none outline-none bg-transparent placeholder-gray-400"
          />
        </div>

        {/* Suggestions dropdown */}
        {showSuggestions && filteredSuggestions.length > 0 && (
          <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto">
            {filteredSuggestions.slice(0, 10).map((suggestion, index) => (
              <button
                key={index}
                type="button"
                onClick={() => handleSuggestionClick(suggestion)}
                className="w-full px-3 py-2 text-left hover:bg-gray-100 focus:bg-gray-100 focus:outline-none"
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}
      </div>

      {(error || validationError) && (
        <p className="text-sm text-red-600">{error || validationError}</p>
      )}
      {helperText && !error && !validationError && (
        <p className="text-sm text-gray-500">{helperText}</p>
      )}
    </div>
  )
}