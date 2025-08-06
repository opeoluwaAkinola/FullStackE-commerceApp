import React from 'react'
import { useApp } from '../../context/AppContext';
import { ShoppingCart, Plus, Minus } from 'lucide-react';
import './Cart.css'; // Assuming you have some styles for the cart component


function Cart() {
    const { cartItems, updateCartItem, removeFromCart, setCurrentView } = useApp();

  const total = cartItems.reduce((sum, item) => sum + item.price * item.quantity, 0);

  if (cartItems.length === 0) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center py-12">
          <ShoppingCart className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Your cart is empty</h2>
          <p className="text-gray-600 mb-6">Add some products to get started!</p>
          <button 
            onClick={() => setCurrentView('home')}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors">
            Continue Shopping
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h2 className="text-3xl font-bold text-gray-900 mb-8">Shopping Cart</h2>
      
      <div className="space-y-4">
        {cartItems.map(item => (
          <div key={item.id} className="bg-white rounded-lg shadow-md p-6 flex items-center">
            <img 
              src={item.image} 
              alt={item.name}
              className="w-16 h-16 object-cover rounded-lg mr-4"
            />
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-gray-900">{item.name}</h3>
              <p className="text-gray-600">${item.price}</p>
            </div>
            <div className="flex items-center space-x-3">
              <button 
                onClick={() => updateCartItem(item.id, Math.max(0, item.quantity - 1))}
                className="p-1 hover:bg-gray-100 rounded">
                <Minus className="h-4 w-4" />
              </button>
              <span className="w-8 text-center">{item.quantity}</span>
              <button 
                onClick={() => updateCartItem(item.id, item.quantity + 1)}
                className="p-1 hover:bg-gray-100 rounded">
                <Plus className="h-4 w-4" />
              </button>
              <button 
                onClick={() => removeFromCart(item.id)}
                className="ml-4 text-red-600 hover:text-red-800">
                Remove
              </button>
            </div>
          </div>
        ))}
      </div>
      
      <div className="mt-8 bg-white rounded-lg shadow-md p-6">
        <div className="flex justify-between items-center text-xl font-bold mb-4">
          <span>Total: ${total.toFixed(2)}</span>
        </div>
        <button 
          onClick={() => setCurrentView('checkout')}
          className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition-colors">
          Proceed to Checkout
        </button>
      </div>
    </div>
    );
}

export default Cart;
