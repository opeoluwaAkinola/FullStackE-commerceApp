# Use Node.js 18 with Debian for better compatibility
FROM node:latest

# Set working directory
WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./


# Install dependencies with explicit platform handling
RUN npm install --production=false

# Copy source code
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Start the development server
CMD ["npm", "run", "dev"]