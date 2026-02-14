#!/bin/bash
# Quick deployment script for Koyeb

echo "🚀 Polymarket Bot - Koyeb Deployment Helper"
echo "============================================"
echo ""

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "📁 Initializing Git repository..."
    git init
    git branch -M main
else
    echo "✅ Git repository already initialized"
fi

# Add files
echo "📦 Adding files to Git..."
git add .

# Show status
echo ""
echo "📊 Git Status:"
git status --short

# Commit
echo ""
read -p "Enter commit message (or press Enter for default): " commit_msg
if [ -z "$commit_msg" ]; then
    commit_msg="Prepare for Koyeb deployment"
fi

git commit -m "$commit_msg"

echo ""
echo "============================================"
echo "✅ Code is ready for deployment!"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Create GitHub repository (if not done):"
echo "   • Go to https://github.com/new"
echo "   • Name: polymarket-bot"
echo "   • Make it private (recommended)"
echo ""
echo "2. Push to GitHub:"
echo "   git remote add origin https://github.com/YOUR_USERNAME/polymarket-bot.git"
echo "   git push -u origin main"
echo ""
echo "3. Deploy on Koyeb:"
echo "   • Visit https://app.koyeb.com"
echo "   • Click 'Create App'"
echo "   • Select GitHub and choose your repository"
echo "   • Add environment variables (see .env.koyeb.template)"
echo "   • Deploy!"
echo ""
echo "📖 Full Guide: See koyeb_deployment_guide.md"
echo "============================================"
