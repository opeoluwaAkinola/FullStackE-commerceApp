# FullStackE-commerceApp
Used Python for the back end, React ( Vite) for the fron end, 


Tech Stack
- Backend: Python + FastAPI
- Databases: MongoDB (product catalog), PostgreSQL (transactions/users)
- Containerization: Docker
Microservices Architecture
1. User Management Service
- Responsibilities: Authentication, authorization, user profiles
- Database: PostgreSQL
- Endpoints:
   - POST /auth/register - User registration
   - POST /auth/login - User login
   - GET /users/{id} - Get user profile
   - PUT /users/{id} - Update user profile
2. Product Catalog Service
- Responsibilities: Product information, categories, search
- Database: MongoDB
- Endpoints:
   - GET /products - List products with filtering
   - GET /products/{id} - Get product details
   - POST /products - Create product (admin)
   - PUT /products/{id} - Update product
   - GET /categories - List categories
3. Order Management Service
- Responsibilities: Order creation, order history, order status
- Database: PostgreSQL
- Endpoints:
   - POST /orders - Create order
   - GET /orders/{id} - Get order details
   - GET /users/{id}/orders - Get user orders
   - PUT /orders/{id}/status - Update order status
4. Payment Service
- Responsibilities: Payment processing, refunds
- Database: PostgreSQL
- Endpoints:
   - POST /payments - Process payment
   - GET /payments/{id} - Get payment details
   - POST /payments/{id}/refund - Process refund
5. Inventory Service
- Responsibilities: Stock management, inventory updates
- Database: MongoDB + PostgreSQL (hybrid)
- Endpoints:
   - GET /inventory/{product_id} - Get stock level
   - PUT /inventory/{product_id} - Update stock
   - POST /inventory/reserve - Reserve items for order
6. Notification Service
- Responsibilities: Email/SMS notifications, real-time updates
- Database: PostgreSQL (notification logs)
- Endpoints:
   - POST /notifications - Send notification
   - GET /notifications/{user_id} - Get user notifications
