import React from 'react'
import { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { ShoppingCart, User, Package, LogOut, Menu, X } from 'lucide-react';
import './Header.css'; // Assuming you have some styles for the header

function Header() {
  const { user, setCurrentView, cartItems, logout } = useApp();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const cartItemCount = cartItems.reduce((total, item) => total + item.quantity, 0);

  return (
    <header className="bg-white shadow-lg border-b">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center">
            <h1 className="text-2xl font-bold text-gray-900 cursor-pointer"
                onClick={() => setCurrentView('home')}>
              MarketPlace
            </h1>
          </div>
          
          <div className="hidden md:flex items-center space-x-6">
            <button 
              className="text-gray-700 hover:text-blue-600 transition-colors"
              onClick={() => setCurrentView('home')}>
              Products
            </button>
            <button 
              className="text-gray-700 hover:text-blue-600 transition-colors relative"
              onClick={() => setCurrentView('cart')}>
              <ShoppingCart className="h-6 w-6" />
              {cartItemCount > 0 && (
                <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
                  {cartItemCount}
                </span>
              )}
            </button>
            {user ? (
              <div className="flex items-center space-x-4">
                <button 
                  className="text-gray-700 hover:text-blue-600 transition-colors"
                  onClick={() => setCurrentView('orders')}>
                  <Package className="h-6 w-6" />
                </button>
                <button 
                  className="text-gray-700 hover:text-blue-600 transition-colors"
                  onClick={() => setCurrentView('profile')}>
                  <User className="h-6 w-6" />
                </button>
                <button 
                  className="text-gray-700 hover:text-red-600 transition-colors"
                  onClick={logout}>
                  <LogOut className="h-6 w-6" />
                </button>
              </div>
            ) : (
              <button 
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
                onClick={() => setCurrentView('login')}>
                Sign In
              </button>
            )}
          </div>
          
          <button 
            className="md:hidden"
            onClick={() => setIsMenuOpen(!isMenuOpen)}>
            {isMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
      </div>
      
      {/* Mobile menu */}
      {isMenuOpen && (
        <div className="md:hidden bg-white border-t">
          <div className="px-2 pt-2 pb-3 space-y-1">
            <button 
              className="block w-full text-left px-3 py-2 text-gray-700 hover:bg-gray-100"
              onClick={() => {setCurrentView('home'); setIsMenuOpen(false);}}>
              Products
            </button>
            <button 
              className="block w-full text-left px-3 py-2 text-gray-700 hover:bg-gray-100"
              onClick={() => {setCurrentView('cart'); setIsMenuOpen(false);}}>
              Cart ({cartItemCount})
            </button>
            {user ? (
              <>
                <button 
                  className="block w-full text-left px-3 py-2 text-gray-700 hover:bg-gray-100"
                  onClick={() => {setCurrentView('orders'); setIsMenuOpen(false);}}>
                  Orders
                </button>
                <button 
                  className="block w-full text-left px-3 py-2 text-gray-700 hover:bg-gray-100"
                  onClick={() => {setCurrentView('profile'); setIsMenuOpen(false);}}>
                  Profile
                </button>
                <button 
                  className="block w-full text-left px-3 py-2 text-red-600 hover:bg-gray-100"
                  onClick={logout}>
                  Logout
                </button>
              </>
            ) : (
              <button 
                className="block w-full text-left px-3 py-2 text-blue-600 hover:bg-gray-100"
                onClick={() => {setCurrentView('login'); setIsMenuOpen(false);}}>
                Sign In
              </button>
            )}
          </div>
        </div>
      )}
    </header>
  );
};

export default Header
