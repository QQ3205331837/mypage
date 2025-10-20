# Vercel 部署指南

## 部署步骤

1. **准备项目文件**
   - 确保所有文件都在 `news_web/mypage` 目录下
   - 项目结构应该包含：
     - `app.py` - 主应用文件
     - `requirements.txt` - Python依赖
     - `vercel.json` - Vercel配置
     - `package.json` - Node.js配置（可选）
     - `static/` - 静态资源文件夹
     - `templates/` - HTML模板文件夹
     - `api/` - API路由文件夹

2. **Vercel 部署方式**

### 方式一：通过 Vercel CLI
```bash
# 安装 Vercel CLI
npm i -g vercel

# 登录 Vercel
vercel login

# 在项目目录部署
cd news_web/mypage
vercel
```

### 方式二：通过 GitHub 集成
1. 将代码推送到 GitHub 仓库
2. 在 Vercel 控制台连接 GitHub 账户
3. 导入项目并自动部署

### 方式三：通过 Vercel 网页界面
1. 访问 [vercel.com](https://vercel.com)
2. 点击 "New Project"
3. 选择 GitHub 仓库或直接上传项目文件

## 环境变量配置

在 Vercel 项目设置中配置以下环境变量（可选）：

```env
# 代理设置（如果需要）
PROXY_BASE=https://your-proxy-domain.workers.dev

# 管理员密钥（用于调试接口）
ADMIN_KEY=your-secret-key

# Flask 配置
FLASK_ENV=production
```

## 部署注意事项

1. **静态文件处理**：Vercel 会自动处理 `static/` 文件夹中的静态资源
2. **Python 版本**：确保 `runtime.txt` 指定正确的 Python 版本
3. **依赖管理**：所有依赖必须在 `requirements.txt` 中列出
4. **路径问题**：所有文件路径使用相对路径，避免绝对路径

## 故障排除

### 常见问题

1. **导入错误**：检查 `requirements.txt` 中的依赖版本
2. **静态资源404**：确保 `vercel.json` 中的路由配置正确
3. **超时问题**：Vercel 函数默认10秒超时，可在配置中调整

### 调试方法

1. 检查 Vercel 部署日志
2. 使用 `/healthz` 端点测试应用状态
3. 查看 `/metrics` 端点获取性能数据（需要 ADMIN_KEY）

## 性能优化建议

1. **缓存策略**：合理设置 HTTP 缓存头
2. **CDN 利用**：Vercel 自动提供全球 CDN
3. **函数优化**：减少冷启动时间，优化依赖大小

## 监控和维护

1. **日志监控**：通过 Vercel 控制台查看实时日志
2. **性能监控**：使用 Vercel Analytics 监控网站性能
3. **自动部署**：配置 GitHub 自动部署，确保代码更新及时发布