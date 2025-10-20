# 西游洞旅游快报 - Vercel 部署版

## 项目简介
国内旅游资讯聚合网站，聚合人民网、中国旅游新闻网、央广网等权威媒体的旅游资讯。

## 功能特性
- 📰 多来源新闻聚合
- 🔍 智能搜索过滤
- 🌙 暗黑模式支持
- 📱 响应式设计
- 📊 数据导出功能

## 部署说明

### Vercel 部署步骤

#### 方法一：通过 GitHub 部署（推荐）
1. 将代码推送到 GitHub 仓库
2. 访问 [Vercel](https://vercel.com)
3. 点击 "New Project"
4. 导入您的 GitHub 仓库
5. 确保根目录设置为 `mypage/`
6. 点击 "Deploy"

#### 方法二：通过 Vercel CLI
```bash
# 安装 Vercel CLI
npm i -g vercel

# 登录 Vercel
vercel login

# 部署项目
cd mypage
vercel --prod
```

#### 方法三：网页直接上传
1. 访问 [Vercel](https://vercel.com)
2. 点击 "New Project"
3. 选择 "Import Git Repository" 或直接拖拽 mypage 文件夹

## 环境配置

### 环境变量（可选）
在 Vercel 项目设置中配置：
```
PROXY_BASE=https://your-proxy-domain.workers.dev  # 代理设置
ADMIN_KEY=your-secret-key                         # 管理接口密钥
```

## 文件结构
```
mypage/
├── api/
│   └── index.py          # Vercel API 入口
├── app.py                # Flask 主应用
├── vercel.json           # Vercel 配置
├── requirements.txt      # Python 依赖
├── runtime.txt          # Python 版本
├── static/              # 静态资源
├── templates/           # HTML 模板
└── README.md           # 说明文档
```

## 本地开发
```bash
cd mypage
pip install -r requirements.txt
python app.py
# 访问 http://localhost:5000
```

## 故障排除

### 常见问题
1. **404 错误**：检查 Vercel 配置和路由设置
2. **导入错误**：确认 requirements.txt 依赖正确
3. **静态资源无法加载**：验证 static 文件夹配置

### 调试方法
- 查看 Vercel 部署日志
- 访问 `/healthz` 端点测试应用状态
- 检查环境变量配置

## 技术支持
如有问题，请检查：
1. Vercel 部署日志
2. Python 版本兼容性
3. 依赖包版本冲突

部署成功后，您的网站将可通过自定义域名访问。