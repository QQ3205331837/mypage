#!/bin/bash

# Vercel 部署脚本
# 适用于 news_web/mypage 项目

echo "🚀 开始部署到 Vercel..."

# 检查是否安装了 Vercel CLI
if ! command -v vercel &> /dev/null; then
    echo "📦 安装 Vercel CLI..."
    npm install -g vercel
fi

# 检查是否已登录
if ! vercel whoami &> /dev/null; then
    echo "🔐 请先登录 Vercel..."
    vercel login
fi

# 部署到生产环境
echo "📤 部署到生产环境..."
vercel --prod

echo "✅ 部署完成！"
echo "🌐 您的网站将在几分钟内可用"