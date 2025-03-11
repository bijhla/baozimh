# task_manager.py (最终版)
import asyncio
import json
import os
from downloader import download_images_async, get_image_links, close_session
from utils import sanitize_filename, setup_logger

# 获取 logger 实例
logger = setup_logger(__name__)


class TaskManager:
    def __init__(self, gui_update_callback=None):
        self.downloading_tasks = []  # 正在下载 (最多一个)
        self.completed_tasks = []
        self.error_tasks = []
        self.waiting_tasks = []
        # self.cancelled_tasks = [] # 如果需要跟踪被取消的任务，可以启用
        self.gui_update_callback = gui_update_callback
        # self.load_progress()  # 初始加载也移除，按需加载
        self.max_concurrent_downloads = 2  # 严格限制为 2
        self.download_tasks = {}  # 使用字典来存储所有创建的 asyncio.Task


    async def add_task(self, chapter_url, chapter_name, comic_download_folder, total_images, img_links, comic_name):
        """添加任务到等待队列 (不获取链接)"""
        logger.info(f"添加任务到等待队列: 章节 {chapter_name}, URL: {chapter_url}")

        # 检查任务是否已经在 正在下载、等待、完成 列表中
        for task_list in [self.downloading_tasks, self.waiting_tasks, self.completed_tasks]:
            for existing_task in task_list:
                if existing_task["chapter_url"] == chapter_url:
                    logger.info(f"任务已存在: {chapter_name}")
                    return

        safe_chapter_name = sanitize_filename(chapter_name)
        chapter_download_folder = os.path.join(comic_download_folder, safe_chapter_name)

        task = {
            "chapter_url": chapter_url,
            "chapter_name": chapter_name,
            "download_folder": chapter_download_folder,
            "status": "waiting",
            "progress": 0,
            "total_images": 0,  # 初始为 0
            "downloaded_images": 0,
            "total_size": 0,
            "downloaded_size": 0,
            "img_links": [],  # 初始为空
            "comic_name": comic_name, # 添加 comic_name
        }
        self.waiting_tasks.append(task)

        if self.gui_update_callback:
            self.gui_update_callback()

        if not self.downloading_tasks:  # 如果当前没有下载任务
            await self._start_next_task()

    async def _start_next_task(self):
        """启动下一个任务 (获取链接并开始下载)"""
        if self.waiting_tasks and not self.downloading_tasks:
            task = self.waiting_tasks.pop(0)
            task["status"] = "downloading"
            self.downloading_tasks.append(task)

            try:
                img_links = await get_image_links(task["chapter_url"])  # 获取图片链接
                if img_links:
                    task["img_links"] = img_links
                    task["total_images"] = len(img_links)
                    logger.info(f"开始下载章节: {task['chapter_name']}, 共 {task['total_images']} 张图片")

                    if self.gui_update_callback:
                        self.gui_update_callback()
                    
                    # 添加一个小的延迟，确保前一个任务的资源已经释放
                    await asyncio.sleep(0.5)
                    
                    # 使用 asyncio.create_task 启动下载, 并保存 task 对象
                    download_task = asyncio.create_task(self.run_task(task))
                    self.download_tasks[task['chapter_url']] = download_task

                else:
                    task["status"] = "error"
                    self.downloading_tasks.remove(task)
                    self.error_tasks.append(task)
                    logger.error(f"获取章节 {task['chapter_name']} 图片链接失败")
                    if self.gui_update_callback:
                        self.gui_update_callback()
                    await self._start_next_task()  # 尝试启动下一个

            except Exception as e:
                logger.exception(f"获取图片链接或启动任务时发生错误: {e}")
                task["status"] = "error"
                self.downloading_tasks.remove(task)
                self.error_tasks.append(task)
                if self.gui_update_callback:
                    self.gui_update_callback()
                await self._start_next_task()  # 尝试启动下一个

    async def run_task(self, task):
        """运行下载任务"""
        logger.info(f"run_task 开始执行: {task['chapter_name']}")

        def progress_callback(downloaded, total):
            task["downloaded_images"] += downloaded
            task["progress"] = (task["downloaded_images"] / task["total_images"]) * 100
            if self.gui_update_callback:
                self.gui_update_callback()
            # logger.debug(f"任务 {task['chapter_name']} 进度: {task['progress']:.2f}%") # 调试进度也移除

        try:
            # 直接传入 task["img_links"]
            await download_images_async(task["img_links"], task["download_folder"], progress_callback)
            # 只有在下载完全成功的情况下，才将任务状态设置为 "completed"
            if task["status"] == "downloading":
                task["status"] = "completed"
                logger.info(f"任务完成: {task['chapter_name']}")

        except asyncio.CancelledError:
            logger.info(f"任务 {task['chapter_name']} 被取消")
            task["status"] = "cancelled"  # 标记为已取消, 但不放入 error_tasks


        except Exception as e:
            logger.exception(f"下载任务 {task['chapter_name']} 失败: {e}")
            task["status"] = "error"

        finally:
            if task['chapter_url'] in self.download_tasks:
                del self.download_tasks[task['chapter_url']]

            self.downloading_tasks.remove(task)
            if task["status"] == "completed":
                self.completed_tasks.append(task)
            elif task["status"] == "error":
                self.error_tasks.append(task)
            # 如果是被取消的，则不添加到任何列表, 如果需要跟踪，可以添加到 cancelled_tasks

            if self.gui_update_callback:
                self.gui_update_callback()
            # self.save_progress()  # run_task 完成时不保存
            await self._start_next_task()

    async def cancel_task(self, task):
        """取消任务 (改进版)"""
        logger.info(f"取消任务: {task['chapter_name']}")
        # 移除对download_task的cancel
        if task in self.downloading_tasks:
            # task["status"] = "cancelled" # 不需要设置状态
            self.downloading_tasks.remove(task)

        elif task in self.waiting_tasks:
            self.waiting_tasks.remove(task)

        if self.gui_update_callback:
            self.gui_update_callback()

        # 触发 _start_next_task()
        await self._start_next_task()

    def move_task(self, task, direction):
        """调整任务顺序 (仅等待队列)"""
        logger.info(f"移动任务: {task['chapter_name']}, 方向: {direction}")
        if task in self.waiting_tasks:
            index = self.waiting_tasks.index(task)
            if direction == "up" and index > 0:
                self.waiting_tasks[index], self.waiting_tasks[index - 1] = (
                    self.waiting_tasks[index - 1],
                    self.waiting_tasks[index],
                )
            elif direction == "down" and index < len(self.waiting_tasks) - 1:
                self.waiting_tasks[index], self.waiting_tasks[index + 1] = (
                    self.waiting_tasks[index + 1],
                    self.waiting_tasks[index],
                )
            elif direction == "top":
                self.waiting_tasks.remove(task)
                self.waiting_tasks.insert(0, task)
            elif direction == "bottom":
                self.waiting_tasks.remove(task)
                self.waiting_tasks.append(task)

            if self.gui_update_callback:
                self.gui_update_callback()
            # self.save_progress()  # 移动任务时不保存

    def save_progress(self):
        """保存进度"""
        logger.debug("保存进度")
        data = {
            "downloading": self.downloading_tasks,
            "completed": self.completed_tasks,
            "error": self.error_tasks,
            "waiting": self.waiting_tasks,
            # "cancelled": self.cancelled_tasks,  # 如果有 cancelled_tasks
        }
        with open("progress.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def load_progress(self):
        """加载进度"""
        logger.debug("加载进度")
        try:
            with open("progress.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                self.downloading_tasks = data.get("downloading", [])
                self.completed_tasks = data.get("completed", [])
                self.error_tasks = data.get("error", [])
                self.waiting_tasks = data.get("waiting", [])
                # self.cancelled_tasks = data.get("cancelled", []) # 如果有 cancelled_tasks

            for task in self.downloading_tasks:
                task["status"] = "waiting"
                self.downloading_tasks.remove(task)
                self.waiting_tasks.append(task)
            # cancelled_tasks 的任务不需要处理，因为它们已经被取消了

            if not self.downloading_tasks and self.waiting_tasks:
                asyncio.create_task(self._start_next_task())

        except FileNotFoundError:
            logger.info("进度文件不存在")

    async def close(self):
         # 取消所有正在下载的任务
        for task in self.downloading_tasks:
            await self.cancel_task(task) # 现在 cancel_task 只是从列表中移除
        await close_session()
        #self.save_progress() # 在程序关闭的时候保存进度

