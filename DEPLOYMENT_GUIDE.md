# Vercel 部署指南

## 问题修复总结

已修复的Vercel部署错误：

1. **WSGI入口问题**：创建了正确的`api/index.py`作为Vercel的WSGI入口
2. **导入路径问题**：修复了模块导入路径，确保在Vercel环境中能正确导入
3. **路由配置**：更新了`vercel.json`配置文件，指向新的API入口
4. **依赖版本**：更新了`requirements.txt`，使用兼容Vercel的版本

## 部署步骤

### 1. 在Vercel控制台部署

1. 将代码推送到GitHub仓库
2. 在Vercel中导入项目
3. 配置环境变量（可选）：
   - `PROXY_BASE`: 代理服务地址（如果需要）
   - `ADMIN_KEY`: 管理接口密钥

### 2. 环境变量配置

在Vercel项目设置中配置以下环境变量：

```
PYTHON_VERSION=3.9
```

### 3. 验证部署

部署完成后访问：
- 主页面：`https://your-project.vercel.app/`
- 健康检查：`https://your-project.vercel.app/healthz`

## 文件结构说明

```
travel_news_web/
├── api/
│   └── index.py          # Vercel WSGI入口
├── app.py                # 主应用文件
├── vercel.json           # Vercel配置
├── requirements.txt      # Python依赖
├── static/              # 静态文件
├── templates/           # 模板文件
└── DEPLOYMENT_GUIDE.md  # 本文件
```

## 故障排除

如果部署仍然失败，检查：

1. **构建日志**：查看Vercel构建过程中的错误信息
2. **依赖安装**：确保所有依赖都能正确安装
3. **路径配置**：确认`vercel.json`中的路径配置正确
4. **环境变量**：检查环境变量是否正确设置

## 本地测试

```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
python app.py

# 访问 http://localhost:5000
```

部署成功后，您的旅游新闻网站将在Vercel上正常运行。