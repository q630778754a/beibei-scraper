"""
灵宝爬虫服务 - Render 部署版
基于 Scrapling 实现真正的反爬能力（绕过 Cloudflare Turnstile）

提供 HTTP API：
  GET  /          - 首页
  GET  /health    - 健康检查
  POST /scrape    - 爬取指定URL（StealthyFetcher 绕过反爬）
  POST /search    - 搜索关键词（Bing/Google）
  POST /extract   - 智能提取（自动判断文章/商品）
"""

import os
import json
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn

# 日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("lingbao-scraper")

app = FastAPI(
    title="灵宝爬虫服务",
    description="基于 Scrapling 的反爬爬虫服务，为灵宝智能体提供网页数据采集能力",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === 请求模型 ===
class ScrapeRequest(BaseModel):
    url: str
    extract_type: Optional[str] = "auto"  # auto / article / product
    wait: Optional[int] = 3  # 等待页面加载秒数
    stealth: Optional[bool] = True  # 是否使用隐身模式

class SearchRequest(BaseModel):
    keyword: str
    limit: Optional[int] = 5
    engine: Optional[str] = "bing"  # bing / google

class ExtractRequest(BaseModel):
    url: str
    fields: Optional[List[str]] = None  # 要提取的字段

# === 健康检查 ===
@app.get("/")
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "lingbao-scraper",
        "version": "1.0.0",
        "platform": "render",
        "scrapling": "available"
    }

# === 爬取网页 ===
@app.post("/scrape")
async def scrape(req: ScrapeRequest):
    """爬取指定URL，返回标题、正文、价格、图片等"""
    logger.info(f"[scrape] URL: {req.url}, stealth: {req.stealth}")

    try:
        result = await _scrape_with_scrapling(req.url, req.extract_type, req.wait, req.stealth)
        return result
    except Exception as e:
        logger.error(f"[scrape] 失败: {e}")
        # 回退到简单 fetch
        try:
            result = await _scrape_simple(req.url)
            result["fallback"] = True
            return result
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"爬取失败: {str(e)}; 回退也失败: {str(e2)}")

# === 搜索 ===
@app.post("/search")
async def search(req: SearchRequest):
    """搜索引擎爬取"""
    logger.info(f"[search] keyword: {req.keyword}, engine: {req.engine}")

    try:
        results = await _search_engine(req.keyword, req.limit, req.engine)
        return {
            "success": True,
            "keyword": req.keyword,
            "engine": req.engine,
            "count": len(results),
            "results": results
        }
    except Exception as e:
        logger.error(f"[search] 失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

# === 智能提取 ===
@app.post("/extract")
async def extract(req: ExtractRequest):
    """智能提取网页字段"""
    logger.info(f"[extract] URL: {req.url}, fields: {req.fields}")

    try:
        result = await _scrape_with_scrapling(req.url, "auto", 3, True)
        extracted = {"url": req.url, "success": True}

        if req.fields:
            for field in req.fields:
                if field == "title":
                    extracted["title"] = result.get("title", "")
                elif field == "content":
                    extracted["content"] = result.get("content", "")
                elif field == "price":
                    extracted["price"] = result.get("price")
                elif field == "images":
                    extracted["images"] = result.get("images", [])
        else:
            extracted.update(result)

        return extracted
    except Exception as e:
        logger.error(f"[extract] 失败: {e}")
        raise HTTPException(status_code=500, detail=f"提取失败: {str(e)}")


# === Scrapling 爬取实现 ===
async def _scrape_with_scrapling(url, extract_type, wait, stealth):
    """使用 Scrapling 的 StealthyFetcher 爬取（绕过反爬）"""
    try:
        # 动态导入（避免启动时失败）
        try:
            from scrapling.fetchers import StealthyFetcher, DynamicFetcher
            from scrapling.parser import Adaptor
            SCRAPLING_AVAILABLE = True
        except ImportError:
            logger.warning("Scrapling 未安装，使用回退模式")
            SCRAPLING_AVAILABLE = False

        if not SCRAPLING_AVAILABLE:
            return await _scrape_simple(url)

        # 使用 StealthyFetcher 绕过反爬
        if stealth:
            page = StealthyFetcher.fetch(
                url,
                headless=True,
                network_idle=True,
                wait=wait
            )
        else:
            from scrapling.fetchers import Fetcher
            page = Fetcher.get(url)

        # 提取数据
        result = {
            "success": True,
            "url": url,
            "title": "",
            "content": "",
            "price": None,
            "images": [],
            "extract_type": extract_type,
            "crawled_at": _now()
        }

        # 标题
        try:
            title_el = page.css_first('title')
            if title_el:
                result["title"] = title_el.text.strip()
        except Exception:
            pass

        try:
            h1 = page.css_first('h1')
            if h1 and not result["title"]:
                result["title"] = h1.text.strip()
        except Exception:
            pass

        # 正文
        try:
            # 尝试多种正文选择器
            for selector in ['article', '.content', '.article-content', '.detail', 'main', '.post-content']:
                el = page.css_first(selector)
                if el:
                    result["content"] = el.text.strip()[:5000]
                    break

            if not result["content"]:
                # 用所有 p 标签拼接
                paragraphs = page.css('p')
                texts = []
                for p in paragraphs[:20]:
                    t = p.text.strip()
                    if len(t) > 20:
                        texts.append(t)
                result["content"] = "\n".join(texts)[:5000]
        except Exception:
            pass

        # 价格（商品页）
        if extract_type in ["auto", "product"]:
            try:
                for selector in ['.price', '[class*="price"]', '[data-price]', '.J-price', '#price']:
                    el = page.css_first(selector)
                    if el:
                        import re
                        m = re.search(r'[\d.]+', el.text)
                        if m:
                            p = float(m.group())
                            if 0 < p < 100000:
                                result["price"] = p
                                break
            except Exception:
                pass

        # 图片
        try:
            imgs = page.css('img')[:5]
            for img in imgs:
                src = img.attrib.get('src') or img.attrib.get('data-src') or ''
                if src and src.startswith('http'):
                    result["images"].append(src)
        except Exception:
            pass

        # 截断
        result["title"] = result["title"][:200]
        result["content"] = result["content"][:3000]

        if not result["title"] and not result["content"]:
            return {"success": False, "error": "无法提取内容", "url": url}

        return result

    except Exception as e:
        logger.error(f"Scrapling 爬取失败: {e}")
        raise


async def _scrape_simple(url):
    """简单 fetch 回退（无反爬能力）"""
    import urllib.request
    import re

    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'zh-CN,zh;q=0.9'
    })

    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode('utf-8', errors='ignore')

    # 简单正则提取
    title = ""
    m = re.search(r'<title[^>]*>(.*?)</title>', html, re.S | re.I)
    if m:
        title = m.group(1).strip()

    # 提取 p 标签文本
    paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.S | re.I)
    content = "\n".join(re.sub(r'<[^>]+>', '', p).strip() for p in paragraphs if len(p) > 50)[:3000]

    return {
        "success": bool(title or content),
        "url": url,
        "title": title[:200],
        "content": content,
        "price": None,
        "images": [],
        "extract_type": "simple",
        "crawled_at": _now()
    }


async def _search_engine(keyword, limit, engine):
    """搜索引擎爬取"""
    if engine == "google":
        search_url = f"https://www.google.com/search?q={keyword}&num={limit}"
    else:
        search_url = f"https://www.bing.com/search?q={keyword}&count={limit}"

    try:
        from scrapling.fetchers import StealthyFetcher
        page = StealthyFetcher.fetch(search_url, headless=True, network_idle=True, wait=2)

        results = []
        # Bing 选择器
        items = page.css('.b_algo')
        for item in items[:limit]:
            try:
                title_el = item.css_first('h2 a')
                snippet_el = item.css_first('.b_caption p')

                if title_el:
                    results.append({
                        "title": title_el.text.strip(),
                        "url": title_el.attrib.get('href', ''),
                        "snippet": snippet_el.text.strip() if snippet_el else ""
                    })
            except Exception:
                continue

        return results
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        # 回退到简单模式
        return await _search_simple(keyword, limit, search_url)


async def _search_simple(keyword, limit, search_url):
    """简单搜索回退"""
    import urllib.request
    import re

    req = urllib.request.Request(search_url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html',
        'Accept-Language': 'zh-CN,zh;q=0.9'
    })

    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode('utf-8', errors='ignore')

    # 简单正则提取
    results = []
    links = re.findall(r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', html, re.S | re.I)
    for url, text in links[:limit]:
        clean_text = re.sub(r'<[^>]+>', '', text).strip()
        if clean_text and 'bing.com' not in url and 'microsoft.com' not in url:
            results.append({"title": clean_text[:100], "url": url, "snippet": ""})

    return results[:limit]


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


# === 启动 ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
