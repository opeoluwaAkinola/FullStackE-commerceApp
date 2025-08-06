import { API_CONFIG, ENDPOINTS } from './config';


class ApiClient {
  constructor() {
    this.token = localStorage.getItem('token');
  }

  // Generic request method
  async request(serviceUrl, endpoint, options = {}) {
    const url = `${serviceUrl}${endpoint}`;
    
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    // Add authorization header if token exists
    if (this.token) {
      config.headers.Authorization = `Bearer ${this.token}`;
    }

    try {
      const response = await fetch(url, config);
      
      // Handle non-JSON responses
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        throw new Error(`Server returned ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || `HTTP error! status: ${response.status}`);
      }

      return data;
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Authentication methods
  async login(username, password) {
    const response = await this.request(API_CONFIG.USER_SERVICE, ENDPOINTS.AUTH.LOGIN, {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    
    if (response.access_token) {
      this.token = response.access_token;
      localStorage.setItem('token', this.token);
    }
    
    return response;
  }

  async register(userData) {
    const response = await this.request(API_CONFIG.USER_SERVICE, ENDPOINTS.AUTH.REGISTER, {
      method: 'POST',
      body: JSON.stringify(userData),
    });
    return response;
  }

  async getCurrentUser() {
    return await this.request(API_CONFIG.USER_SERVICE, ENDPOINTS.AUTH.PROFILE);
  }

  logout() {
    this.token = null;
    localStorage.removeItem('token');
  }

  // User Management Service
  async getUserProfile(userId) {
    return await this.request(API_CONFIG.USER_SERVICE, `/users/${userId}`);
  }

  async updateUserProfile(userId, userData) {
    return await this.request(API_CONFIG.USER_SERVICE, `/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(userData),
    });
  }

  // Product Catalog Service
  async getProducts(params = {}) {
    const queryParams = new URLSearchParams(params);
    return await this.request(API_CONFIG.PRODUCT_SERVICE, `${ENDPOINTS.PRODUCTS.LIST}?${queryParams}`);
  }

  async getProduct(productId) {
    return await this.request(API_CONFIG.PRODUCT_SERVICE, ENDPOINTS.PRODUCTS.DETAIL(productId));
  }

  async getCategories() {
    return await this.request(API_CONFIG.PRODUCT_SERVICE, ENDPOINTS.PRODUCTS.CATEGORIES);
  }

  // Order Management Service
  async createOrder(orderData) {
    return await this.request(API_CONFIG.ORDER_SERVICE, ENDPOINTS.ORDERS.CREATE, {
      method: 'POST',
      body: JSON.stringify(orderData),
    });
  }

  async getOrder(orderId) {
    return await this.request(API_CONFIG.ORDER_SERVICE, ENDPOINTS.ORDERS.DETAIL(orderId));
  }

  async getUserOrders(userId) {
    return await this.request(API_CONFIG.ORDER_SERVICE, ENDPOINTS.ORDERS.USER_ORDERS(userId));
  }

  async updateOrderStatus(orderId, status) {
    return await this.request(API_CONFIG.ORDER_SERVICE, ENDPOINTS.ORDERS.STATUS(orderId), {
      method: 'PUT',
      body: JSON.stringify({ status }),
    });
  }

  // Payment Service
  async processPayment(paymentData) {
    return await this.request(API_CONFIG.PAYMENT_SERVICE, ENDPOINTS.PAYMENTS.CREATE, {
      method: 'POST',
      body: JSON.stringify(paymentData),
    });
  }

  async getPayment(paymentId) {
    return await this.request(API_CONFIG.PAYMENT_SERVICE, ENDPOINTS.PAYMENTS.DETAIL(paymentId));
  }

  async getPaymentMethods(userId) {
    return await this.request(API_CONFIG.PAYMENT_SERVICE, ENDPOINTS.PAYMENTS.USER_METHODS(userId));
  }

  async addPaymentMethod(paymentMethodData) {
    return await this.request(API_CONFIG.PAYMENT_SERVICE, ENDPOINTS.PAYMENTS.METHODS, {
      method: 'POST',
      body: JSON.stringify(paymentMethodData),
    });
  }

  // Cart Service
  async getCartItems() {
    return await this.request(API_CONFIG.CART_SERVICE, ENDPOINTS.CART.ITEMS);
  }

  async addToCart(itemData) {
    return await this.request(API_CONFIG.CART_SERVICE, ENDPOINTS.CART.ADD_ITEM, {
      method: 'POST',
      body: JSON.stringify(itemData),
    });
  }

  async updateCartItem(itemId, quantity) {
    return await this.request(API_CONFIG.CART_SERVICE, ENDPOINTS.CART.UPDATE_ITEM(itemId), {
      method: 'PUT',
      body: JSON.stringify({ quantity }),
    });
  }

  async removeFromCart(itemId) {
    return await this.request(API_CONFIG.CART_SERVICE, ENDPOINTS.CART.REMOVE_ITEM(itemId), {
      method: 'DELETE',
    });
  }

  async clearCart() {
    return await this.request(API_CONFIG.CART_SERVICE, ENDPOINTS.CART.CLEAR, {
      method: 'DELETE',
    });
  }

  // Inventory Service
  async getInventory(productId) {
    return await this.request(API_CONFIG.INVENTORY_SERVICE, ENDPOINTS.INVENTORY.STOCK(productId));
  }

  async updateInventory(productId, inventoryData) {
    return await this.request(API_CONFIG.INVENTORY_SERVICE, ENDPOINTS.INVENTORY.UPDATE(productId), {
      method: 'PATCH',
      body: JSON.stringify(inventoryData),
    });
  }

  // Notification Service
  async sendNotification(notificationData) {
    return await this.request(API_CONFIG.NOTIFICATION_SERVICE, ENDPOINTS.NOTIFICATIONS.SEND, {
      method: 'POST',
      body: JSON.stringify(notificationData),
    });
  }

  async getUserNotifications(userId) {
    return await this.request(API_CONFIG.NOTIFICATION_SERVICE, ENDPOINTS.NOTIFICATIONS.USER_NOTIFICATIONS(userId));
  }
};

export default ApiClient;
