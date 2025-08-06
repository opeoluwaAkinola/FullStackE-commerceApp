import React from 'react'
import { useApp } from '../../context/AppContext';
import './Error.css'; // Assuming you have some styles for the error component

function Error({ message, onRetry }) {
    return (
        <div className="text-center py-12">
    <div className="text-red-600 mb-4">
      <svg className="h-12 w-12 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.888-.833-2.598 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
      </svg>
    </div>
    <h3 className="text-lg font-semibold text-gray-900 mb-2">Error</h3>
    <p className="text-gray-600 mb-4">{message}</p>
    {onRetry && (
      <button 
        onClick={onRetry}
        className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
        Try Again
      </button>
    )}
  </div>
    )
}

export default Error
