// API Configuration for all backend services
export const API_CONFIG = {
  // Base URLs for each microservice
  USER_SERVICE: import.meta.env.VITE_USER_SERVICE_URL || 'http://localhost:8000',
  PRODUCT_SERVICE: import.meta.env.VITE_PRODUCT_SERVICE_URL || 'http://localhost:8001',
  ORDER_SERVICE: import.meta.env.VITE_ORDER_SERVICE_URL || 'http://localhost:8002',
  PAYMENT_SERVICE: import.meta.env.VITE_PAYMENT_SERVICE_URL || 'http://localhost:8003',
  CART_SERVICE: import.meta.env.VITE_CART_SERVICE_URL || 'http://localhost:8004',
  INVENTORY_SERVICE: import.meta.env.VITE_INVENTORY_SERVICE_URL || 'http://localhost:8005',
  NOTIFICATION_SERVICE: import.meta.env.VITE_NOTIFICATION_SERVICE_URL || 'http://localhost:8006',
};

// Default API base URL (for backward compatibility)
export const API_BASE_URL = API_CONFIG.USER_SERVICE;

// API endpoints for each service
export const ENDPOINTS = {
  // User Service
  AUTH: {
    LOGIN: '/auth/login',
    REGISTER: '/auth/register',
    PROFILE: '/profile',
  },
  
  // Product Service
  PRODUCTS: {
    LIST: '/products',
    DETAIL: (id) => `/products/${id}`,
    CATEGORIES: '/categories',
  },
  
  // Order Service
  ORDERS: {
    CREATE: '/orders',
    LIST: '/orders',
    DETAIL: (id) => `/orders/${id}`,
    STATUS: (id) => `/orders/${id}/status`,
    USER_ORDERS: (userId) => `/users/${userId}/orders`,
  },
  
  // Payment Service
  PAYMENTS: {
    CREATE: '/payments',
    DETAIL: (id) => `/payments/${id}`,
    METHODS: '/payment-methods',
    USER_METHODS: (userId) => `/users/${userId}/payment-methods`,
  },
  
  // Cart Service
  CART: {
    ITEMS: '/cart/items',
    ADD_ITEM: '/cart/items',
    UPDATE_ITEM: (id) => `/cart/items/${id}`,
    REMOVE_ITEM: (id) => `/cart/items/${id}`,
    CLEAR: '/cart/clear',
  },
  
  // Inventory Service
  INVENTORY: {
    STOCK: (id) => `/products/${id}/stock`,
    UPDATE: (id) => `/products/${id}/inventory`,
  },
  
  // Notification Service
  NOTIFICATIONS: {
    SEND: '/notifications',
    USER_NOTIFICATIONS: (userId) => `/notifications/${userId}`,
  },
}; 