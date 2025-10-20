#!/bin/bash

# Vercel 部署脚本
# 用于自动化部署流程

echo "🚀 开始部署旅游资讯网站到 Vercel..."

# 检查 Vercel CLI 是否安装
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI 未安装，请先安装: npm i -g vercel"
    exit 1
fi

# 检查当前目录
if [ ! -f "app.py" ]; then
    echo "❌ 请在项目根目录运行此脚本"
    exit 1
fi

# 检查依赖文件
if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt 文件不存在"
    exit 1
fi

if [ ! -f "vercel.json" ]; then
    echo "❌ vercel.json 文件不存在"
    exit 1
fi

echo "✅ 项目文件检查完成"

# 部署到 Vercel
echo "📦 开始部署..."
vercel --prod

if [ $? -eq 0 ]; then
    echo "🎉 部署成功！"
    echo "🌐 网站地址: https://news.xiyoudongjingqu.icu/"
else
    echo "❌ 部署失败，请检查错误信息"
    exit 1
fi

# 显示部署后检查清单
echo ""
echo "🔍 部署后检查清单:"
echo "1. ✅ 检查网站是否可以正常访问"
echo "2. ✅ 测试静态资源加载（图片、CSS）"
echo "3. ✅ 测试搜索功能"
echo "4. ✅ 测试暗黑模式切换"
echo "5. ✅ 检查移动端响应式布局"
echo "6. ✅ 验证 API 接口正常工作"
echo "7. ✅ 检查错误日志（Vercel 控制台）"

echo ""
echo "📚 更多信息请查看 README.md"