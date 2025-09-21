#!/bin/bash

echo "🚀 Deploying Gatherly to Railway..."

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Please install it first:"
    echo "npm install -g @railway/cli"
    exit 1
fi

# Check if user is logged in
if ! railway status &> /dev/null; then
    echo "🔐 Please login to Railway first:"
    echo "railway login"
    exit 1
fi

echo "📦 Deploying to Railway..."
railway up

echo "✅ Deployment complete!"
echo ""
echo "📋 Next steps:"
echo "1. Set your environment variables in Railway dashboard"
echo "2. Run database migrations: railway run flask db upgrade"
echo "3. Visit your app at the Railway-provided URL"
echo ""
echo "🔧 To set environment variables via CLI:"
echo "railway variables set SECRET_KEY=your-secret-key-here"
echo "railway variables set TWILIO_ACCOUNT_SID=your-twilio-sid"
echo "railway variables set TWILIO_AUTH_TOKEN=your-twilio-token"
