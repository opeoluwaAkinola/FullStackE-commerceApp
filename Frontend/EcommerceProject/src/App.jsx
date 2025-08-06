import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import { AppContext } from './context/AppContext'
import Header from './components/header/Header'
import ProductList from './components/productList/ProductList'
import LoginForm from './components/loginForm/LoginForm'
import Cart from './components/cart/Cart'
import Orders from './components/orders/Orders'
import Profile from './components/profile/Profile'
import apiClient from './api/apiClient'
import { useAuth } from './hooks/useAuth'
import { useApp } from './context/AppContext'
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom'
import './App.css'

const App = () => {
  const [user, setUser] = useState(null);
  const [currentView, setCurrentView] = useState('home');
  const [cartItems, setCartItems] = useState([]);

  const addToCart = (product) => {
    setCartItems(prev => {
      const existing = prev.find(item => item.id === product.id);
      if (existing) {
        return prev.map(item =>
          item.id === product.id 
            ? { ...item, quantity: item.quantity + 1 }
            : item
        );
      }
      return [...prev, { ...product, quantity: 1 }];
    });
  };

  const updateCartItem = (id, quantity) => {
    if (quantity === 0) {
      setCartItems(prev => prev.filter(item => item.id !== id));
    } else {
      setCartItems(prev => prev.map(item =>
        item.id === id ? { ...item, quantity } : item
      ));
    }
  };

  const removeFromCart = (id) => {
    setCartItems(prev => prev.filter(item => item.id !== id));
  };

  const logout = () => {
    setUser(null);
    setCartItems([]);
    setCurrentView('home');
  };

  const renderView = () => {
    if (!user && (currentView === 'profile' || currentView === 'orders')) {
      return <LoginForm />;
    }

    switch (currentView) {
      case 'login':
        return <LoginForm />;
      case 'cart':
        return <Cart />;
      case 'orders':
        return <Orders />;
      case 'profile':
        return <Profile />;
      default:
        return <ProductList />;
    }
  };

  return (
    <AppContext.Provider value={{
      user,
      setUser,
      currentView,
      setCurrentView,
      cartItems,
      addToCart,
      updateCartItem,
      removeFromCart,
      logout
    }}>
      <div className="min-h-screen bg-gray-50">
        <Header />
        {renderView()}
      </div>
    </AppContext.Provider>
  );
};

export default App;
