# downloader.py (最终版, 配合 task_manager.py)
import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
import os
import re
from utils import sanitize_filename, setup_logger, MAX_CONCURRENT_DOWNLOADS
import aiofiles
import random

# 获取 logger 实例
logger = setup_logger(__name__)

# 限制并发下载数量
# semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)  # 不需要了

# 全局 aiohttp ClientSession (模块级别)
session = None

async def get_session():
    global session
    if session is None or session.closed:
        logger.info("创建新的全局 session")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        session = aiohttp.ClientSession(headers=headers, connector=aiohttp.TCPConnector(limit=1)) #限制连接数为1
    return session

async def close_session():
    global session
    if session and not session.closed:
        await session.close()

async def fetch(url, headers):  # 简化 fetch，不再需要传入 session
    """异步获取网页内容 (辅助函数)"""
    logger.debug(f"Fetching URL: {url}")
    session = await get_session() # 获取全局 session
    async with session.get(url, headers=headers) as response:
        response.raise_for_status()
        return await response.read()

async def download_image(img_link, download_folder, i, headers, progress_callback=None, retry=3):
    """异步下载单张图片"""
    file_name = os.path.join(download_folder, f"image_{i + 1}.jpg")

    if os.path.exists(file_name):
        logger.info(f"图片已存在，跳过下载: {file_name}")
        if progress_callback:
            progress_callback(1, 1)
        return

    for attempt in range(retry):
        try:
            session = await get_session()
            async with session.get(img_link, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as response:
                response.raise_for_status()
                img_data = await response.read()
                
                async with aiofiles.open(file_name, 'wb') as handler:
                    await handler.write(img_data)
                
                logger.info(f"已下载: {file_name}")
                if progress_callback:
                    progress_callback(1, 1)  # 成功下载一张
                return  # 下载成功, 结束重试

        except (aiohttp.ClientError, aiohttp.http_exceptions.TransferEncodingError, ConnectionResetError, asyncio.TimeoutError) as e:
            logger.warning(f"下载图片 {img_link} 失败 (尝试 {attempt + 1}/{retry}): {e}")
            if attempt < retry - 1:
                await asyncio.sleep(random.uniform(1, 3))  # 随机延迟 1-3 秒
            else:
                logger.error(f"下载图片失败: {img_link}, 错误: {e}", exc_info=True)
                if progress_callback:
                    progress_callback(0, 1)  # 下载失败

        except asyncio.CancelledError:
            logger.info(f"图片下载被取消: {img_link}")
            # 删除未下载完成的文件
            if os.path.exists(file_name):
                os.remove(file_name)
            if progress_callback:
                progress_callback(0, 1)
            return

        except Exception as e:
            logger.error(f"下载图片时发生未知错误: {img_link}, 错误: {e}", exc_info=True)
            if progress_callback:
                progress_callback(0, 1)
            return

async def download_images_async(img_links, download_folder, progress_callback=None):
    """异步下载图片 (修改版, 接收 img_links)"""
    logger.info(f"开始下载到文件夹: {download_folder}")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    # 直接使用传入的 img_links 创建下载任务
    tasks = [
       asyncio.create_task(download_image(img_link, download_folder, i, headers, progress_callback))
       for i, img_link in enumerate(img_links)
    ]
    # 不再有外层的 asyncio.wait, 直接等待内层任务
    await asyncio.gather(*tasks, return_exceptions=True) # 使用 gather 并且 return_exceptions=True
    logger.info(f"下载完成 (或发生错误/取消): {download_folder}")


# --- 以下是原 no_ui_version.py 中的函数 --- (这些函数保持不变) ---
def search_baozimh(keyword):
    """在 baozimh.com 上搜索漫画并返回结果 (同步函数)"""
    logger.info(f"搜索漫画: {keyword}")
    search_url = "https://www.baozimh.com/search"
    params = {"q": keyword}

    try:
        response = requests.get(search_url, params=params)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        comic_items = soup.find_all("a", class_="comics-card__poster")

        results = []
        for item in comic_items:
            title = item["title"] if item.has_attr("title") else "标题未找到"
            comic_url = "https://www.baozimh.com" + item["href"] if item.has_attr("href") else None

            if title and comic_url:
                results.append({"title": title, "url": comic_url})
                logger.debug(f"找到漫画: {title}, URL: {comic_url}")

        logger.info(f"搜索到 {len(results)} 个结果")
        return results

    except requests.exceptions.RequestException as e:
        logger.error(f"请求出错: {e}")
        return []
    except Exception as e:
        logger.error(f"解析出错: {e}")
        return []


def get_chapter_list(comic_url):
    """从漫画详情页获取章节列表 (同步函数)"""
    logger.info(f"获取章节列表: {comic_url}")
    try:
        response = requests.get(comic_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        chapters = []

        chapter_items1 = soup.find("div", id="chapter-items")
        if chapter_items1:
            chapter_items1 = chapter_items1.find_all("a", class_="comics-chapters__item")
            for item in chapter_items1:
                chapter_url = "https://www.baozimh.com" + item["href"]
                chapter_name = item.find("span").text.strip()
                chapters.append({"name": chapter_name, "url": chapter_url})
                logger.debug(f"找到章节: {chapter_name}, URL: {chapter_url}")

        chapter_items2 = soup.find("div", id="chapters_other_list")
        if chapter_items2:
            chapter_items2 = chapter_items2.find_all("a", class_="comics-chapters__item")
            for item in chapter_items2:
                chapter_url = "https://www.baozimh.com" + item["href"]
                span = item.find("span")
                if span:
                    chapter_name = span.text.strip()
                else:
                    chapter_name = "章节名称未找到"
                chapters.append({"name": chapter_name, "url": chapter_url})
                logger.debug(f"找到章节: {chapter_name}, URL: {chapter_url}")

        logger.info(f"获取到 {len(chapters)} 个章节")
        return chapters

    except requests.exceptions.RequestException as e:
        logger.error(f"获取章节列表失败: {e}")
        return []
    except Exception as e:
        logger.error(f"解析章节列表失败: {e}")
        return []

async def get_image_links(chapter_url):
    """从章节 URL 获取图片链接列表 (异步函数)"""
    logger.info(f"获取图片链接: {chapter_url}")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    try:
        response_text = await fetch(chapter_url, headers)
        soup = BeautifulSoup(response_text.decode('utf-8', 'ignore'), 'html.parser')

        img_tags = soup.find_all('amp-img')
        img_links = []
        for img_tag in img_tags:
            src = img_tag.get('src')
            if src and "baozicdn.com/scomic" in src:
                img_links.append(src)
            else:
                data_src = img_tag.get('data-src')
                if data_src and "baozicdn.com/scomic" in data_src:
                    img_links.append(data_src)

        img_links = list(set(img_links))  # 去重
        logger.info(f"找到 {len(img_links)} 张图片")
        return img_links

    except Exception as e:
        logger.error(f"获取图片链接失败: {e}", exc_info=True)
        return []

