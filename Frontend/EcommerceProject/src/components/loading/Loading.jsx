import React from 'react'
import { useApp } from '../../context/AppContext';
import './Loading.css'; // Assuming you have some styles for the loading component
function Loading({ message = 'Loading...' }) {
    return (
        <div className="flex items-center justify-center py-12">
    <div className="text-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
      <p className="text-gray-600">{message}</p>
    </div>
  </div>
    )
};

export default Loading
