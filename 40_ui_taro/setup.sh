#!/bin/bash

# Tennis Serve Analysis - Setup Script
# This script helps set up the development environment

echo "🎾 Setting up Tennis Serve Analysis Frontend..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18.0.0 or higher."
    echo "   Download from: https://nodejs.org/"
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js version $NODE_VERSION is too old. Please install Node.js 18.0.0 or higher."
    exit 1
fi

echo "✅ Node.js version $(node -v) detected"

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm."
    exit 1
fi

echo "✅ npm version $(npm -v) detected"

# Install dependencies
echo "📦 Installing dependencies..."
npm install

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies. Please check the error messages above."
    exit 1
fi

echo "✅ Dependencies installed successfully"

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p public/clipped-videos
mkdir -p tmp

echo "✅ Directories created"

# Check if port 3030 is available
if lsof -Pi :3030 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port 3030 is already in use. You may need to stop the existing process."
    echo "   Run: lsof -i :3030"
    echo "   Then: kill -9 <PID>"
else
    echo "✅ Port 3030 is available"
fi

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "To start the development server, run:"
echo "  npm run dev"
echo ""
echo "Then open your browser and go to:"
echo "  http://localhost:3030"
echo ""
echo "Happy coding! 🚀"
