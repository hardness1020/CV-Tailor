import React from 'react'
import { cn } from '@/utils/cn'

interface DatePickerProps {
  label?: string
  value: string
  onChange: (date: string) => void
  error?: string
  helperText?: string
  validate?: (date: string) => string | true
}

export const DatePicker: React.FC<DatePickerProps> = ({
  label,
  value,
  onChange,
  error,
  helperText,
  validate
}) => {
  const [validationError, setValidationError] = React.useState<string>('')

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value

    if (validate) {
      const result = validate(newValue)
      if (result !== true) {
        setValidationError(result)
      } else {
        setValidationError('')
      }
    }

    onChange(newValue)
  }

  return (
    <div className="space-y-1">
      {label && (
        <label className="block text-sm font-medium text-gray-700">
          {label}
        </label>
      )}
      <input
        type="date"
        value={value}
        onChange={handleChange}
        className={cn(
          'block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-1 sm:text-sm',
          error || validationError
            ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
            : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
        )}
      />
      {(error || validationError) && (
        <p className="text-sm text-red-600">{error || validationError}</p>
      )}
      {helperText && !error && !validationError && (
        <p className="text-sm text-gray-500">{helperText}</p>
      )}
    </div>
  )
}