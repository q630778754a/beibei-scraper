# 灵宝爬虫服务 (beibei-scraper)

基于 [Scrapling](https://github.com/D4Vinci/Scrapling) 的反爬爬虫服务，为灵宝智能体提供网页数据采集能力。

## 能力

- ✅ **StealthyFetcher** - 绕过 Cloudflare Turnstile 等反爬机制
- ✅ **Playwright 浏览器** - 真实浏览器渲染，支持 JS 动态页面
- ✅ **自适应解析** - 网站结构变化后自动重定位元素
- ✅ **商品/文章提取** - 自动判断类型，提取标题/正文/价格/图片
- ✅ **搜索引擎爬取** - Bing/Google 搜索结果采集
- ✅ **HTTP API** - 供后端调用，CORS 支持

## API 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 首页/健康检查 |
| GET | `/health` | 健康检查 |
| POST | `/scrape` | 爬取指定URL |
| POST | `/search` | 搜索关键词 |
| POST | `/extract` | 智能提取字段 |

### 使用示例

```bash
# 爬取网页
curl -X POST https://beibei-scraper.onrender.com/scrape \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","extract_type":"auto","stealth":true}'

# 搜索
curl -X POST https://beibei-scraper.onrender.com/search \
  -H "Content-Type: application/json" \
  -d '{"keyword":"蓝牙耳机","limit":5,"engine":"bing"}'
```

## 部署到 Render

### 方式1：一键部署（推荐）

点击下方链接，登录 Render 后一键部署：

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/q630778754a/beibei-scraper)

### 方式2：手动部署

1. 登录 [Render](https://render.com)
2. 点击 **New** → **Web Service**
3. 连接 GitHub 账号，选择仓库 `q630778754a/beibei-scraper`
4. 配置：
   - **Name**: `beibei-scraper`
   - **Runtime**: Docker（自动检测 Dockerfile）
   - **Region**: Singapore（离中国近）
   - **Plan**: Free（免费750小时/月）
   - **Health Check Path**: `/health`
5. 添加环境变量：
   - `PORT` = `10000`
6. 点击 **Create Web Service**

### 部署后

部署成功后，Render 会分配一个地址：`https://beibei-scraper.onrender.com`

后端会自动调用这个地址（已配置为默认值）。如果需要修改，在后端 Vercel 项目设置环境变量：
```
SCRAPER_RENDER_URL=https://your-service.onrender.com
```

## 技术栈

- **FastAPI** - Python Web 框架
- **Scrapling** - 自适应爬虫框架
- **Playwright** - 浏览器自动化（Chromium）
- **Camoufox** - 反指纹检测
- **Docker** - 容器化部署

## 免费额度说明

Render 免费套餐：
- 750 小时/月
- 服务15分钟无请求会休眠
- 首次请求需冷启动（约30-50秒）
- 建议用 Render 的 Cron Job 定时 ping `/health` 保持唤醒

如需更高性能，升级到 Starter 套餐（$7/月，无休眠）。
