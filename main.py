# main.py
import PySimpleGUI as sg
from gui import create_main_layout
from task_manager import TaskManager
from utils import windows_asyncio_fix, setup_logger, sanitize_filename
import asyncio
from downloader import (
    search_baozimh, get_chapter_list, close_session,
    get_all_mirrors, add_mirror, set_mirror_source, get_current_mirror, remove_mirror
)
import os


# 获取 logger 实例, 使用模块名 "__main__"
logger = setup_logger(__name__)

windows_asyncio_fix()

# --- 在创建窗口之前设置主题 --- (这很重要)
# 定义颜色 (这些应该和 gui.py 中的一致)
text_color = "white"
bg_color = "#1B1D20"
input_bg_color = "#2B2D30"

sg.theme_background_color(bg_color)
sg.theme_text_color(text_color)
sg.theme_input_background_color(input_bg_color)
sg.theme_input_text_color(text_color)
sg.theme_element_text_color(text_color)

# 创建GUI
layout = create_main_layout()

window = sg.Window("包子漫画下载器", layout, finalize=True, font=("微软雅黑", 12)) # 这里可以设置全局字体和大小

# 设置章节列表为多选模式
window["-CHAPTER_LIST-"].update(select_mode=sg.LISTBOX_SELECT_MODE_MULTIPLE)
# 创建 TaskManager
task_manager = TaskManager(
    gui_update_callback=lambda: window.write_event_value("-UPDATE_LISTS-", "")
)

# 搜索到的漫画结果
search_results = []
selected_comic = None
# 章节列表
chapters = []
selected_chapters = []

def update_task_lists():
    """更新GUI中的任务列表"""
    logger.debug("更新GUI中的任务列表")
    # 使用 downloaded_images 和 total_images 显示进度
    #  显示 "作品名 章节名"
    downloading_data = [
        f"{task['comic_name']} {task['chapter_name']} ({task['downloaded_images']}/{task['total_images']})"
        for task in task_manager.downloading_tasks
    ]
    waiting_data = [f"{task['comic_name']} {task['chapter_name']}" for task in task_manager.waiting_tasks]
    completed_data = [f"{task['comic_name']} {task['chapter_name']}" for task in task_manager.completed_tasks]
    error_data = [f"{task['comic_name']} {task['chapter_name']}" for task in task_manager.error_tasks]

    window["-DOWNLOADING-"].update(values=downloading_data)
    window["-WAITING-"].update(values=waiting_data)
    window["-COMPLETED-"].update(values=completed_data)
    window["-ERROR-"].update(values=error_data)

def show_mirror_selection():
    """显示镜像源选择窗口"""
    mirrors = get_all_mirrors()
    current = get_current_mirror()
    
    layout = [
        [sg.Text("选择镜像源", font=("微软雅黑", 12), background_color=bg_color)],
        [sg.Listbox(
            values=[f"{k}: {v['name']} ({v['base_url']})" for k, v in mirrors.items()],
            size=(50, 10),
            key="-MIRROR_LIST-",
            default_values=[f"{current['name']} ({current['base_url']})"]
        )],
        [sg.Button("确定"), sg.Button("取消")]
    ]
    
    window = sg.Window("选择镜像源", layout, modal=True, background_color=bg_color)
    
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "取消"):
            break
        if event == "确定" and values["-MIRROR_LIST-"]:
            selected = values["-MIRROR_LIST-"][0]
            key = selected.split(":")[0]
            success, msg = set_mirror_source(key)
            if success:
                sg.popup(msg, title="成功")
            else:
                sg.popup(msg, title="错误")
            break
    
    window.close()

def show_add_mirror():
    """显示添加镜像源窗口"""
    layout = [
        [sg.Text("添加新镜像源", font=("微软雅黑", 12))],
        [sg.Text("标识:"), sg.Input(key="-MIRROR_KEY-")],
        [sg.Text("名称:"), sg.Input(key="-MIRROR_NAME-")],
        [sg.Text("网址:"), sg.Input(key="-MIRROR_URL-")],
        [sg.Text("CDN模式:"), sg.Input(key="-MIRROR_CDN-", default_text="baozicdn.com")],
        [sg.Button("添加"), sg.Button("取消")]
    ]
    
    window = sg.Window("添加镜像源", layout, modal=True)
    
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "取消"):
            break
        if event == "添加":
            key = values["-MIRROR_KEY-"].strip()
            name = values["-MIRROR_NAME-"].strip()
            url = values["-MIRROR_URL-"].strip()
            cdn = values["-MIRROR_CDN-"].strip()
            
            if not all([key, name, url]):
                sg.popup("所有字段都必须填写！", title="错误")
                continue
                
            success, msg = add_mirror(key, name, url, cdn)
            sg.popup(msg, title="成功" if success else "错误")
            if success:
                break
    
    window.close()

async def main_loop():  # 将主循环改为异步函数
    # 事件循环
    while True:
        event, values = window.read(timeout=100)

        if event == sg.WIN_CLOSED:
            logger.info("程序退出")
            break

        elif event == "-SELECT_MIRROR-":
            show_mirror_selection()

        elif event == "-ADD_MIRROR-":
            show_add_mirror()

        elif event == "-SEARCH_BTN-":
            keyword = values["-SEARCH-"]
            if keyword:
                # 使用无 UI 版本的 search_baozimh 函数
                search_results = search_baozimh(keyword)
                window["-SEARCH_RESULTS-"].update(
                    [result["title"] for result in search_results]
                )
                window["-STATUS-"].update(f"搜索到 {len(search_results)} 条结果")
            else:
                window["-STATUS-"].update("请输入搜索关键词")

        elif event == "-SEARCH_RESULTS-":
            index = window["-SEARCH_RESULTS-"].get_indexes()
            if index:
                selected_comic = search_results[index[0]]
                window["-COMIC_NAME-"].update(selected_comic["title"], visible=False) # 隐藏
                window["-COMIC_URL-"].update(selected_comic["url"])
                window["-GET_CHAPTERS-"].update(disabled=False)
                window["-COPY_URL-"].update(disabled=False)  # 启用复制按钮
                window["-DOWNLOAD-"].update(disabled=True)
                window["-DOWNLOAD_ALL-"].update(disabled=True)


        elif event == "-GET_CHAPTERS-":
            if selected_comic:
                # 使用无 UI 版本的 get_chapter_list 函数
                chapters = get_chapter_list(selected_comic["url"])
                if chapters:
                    chapter_names = [chapter["name"] for chapter in chapters]
                    window["-CHAPTER_LIST-"].update(chapter_names)
                    window["-DOWNLOAD-"].update(disabled=False)
                    window["-DOWNLOAD_ALL-"].update(disabled=False)
                    window["-STATUS-"].update(f"获取到 {len(chapters)} 个章节")
                else:
                    window["-STATUS-"].update("获取章节失败")
        elif event == "-COPY_URL-":
            url = window["-COMIC_URL-"].get()
            if url:
                sg.clipboard_set(url)  # 复制到剪贴板
                window["-STATUS-"].update("已复制漫画地址到剪贴板")

        elif event == "-CHAPTER_LIST-":
            selected_chapters_indexes = window["-CHAPTER_LIST-"].get_indexes()
            if selected_chapters_indexes:
                selected_chapters = [chapters[i] for i in selected_chapters_indexes]
            else:
                selected_chapters = []

        elif event == "-DOWNLOAD-":  # 下载选中章节
            if selected_chapters and selected_comic: # 确保 selected_comic 不为空
                comic_name = sanitize_filename(selected_comic["title"])
                comic_download_folder = os.path.join("comic", comic_name) # 修改下载路径
                for chapter in selected_chapters:
                    # 检查任务是否已经存在(简化)
                    if not any(existing_task["chapter_url"] == chapter["url"]
                               for task_list in [task_manager.downloading_tasks, task_manager.waiting_tasks,
                                                 task_manager.completed_tasks] # 不检查 error_tasks
                               for existing_task in task_list):

                        # 直接调用 task_manager.add_task，不再获取图片链接
                        await task_manager.add_task(
                            chapter["url"],
                            chapter["name"],
                            comic_download_folder,
                            0,  # total_images 设为 0, 会在 _start_next_task 中更新
                            [],  # img_links 为空列表，会在 _start_next_task 中获取
                            comic_name  # 传入 comic_name
                        )
                    else:
                        logger.info(f"任务已存在，跳过添加: {chapter['name']}")



        elif event == "-DOWNLOAD_ALL-":  # 下载全部章节 (逻辑与 "-DOWNLOAD-" 类似)
            if chapters and selected_comic: # 确保 selected_comic 不为空
                comic_name = sanitize_filename(selected_comic["title"])
                comic_download_folder = os.path.join("comic", comic_name)  # 修改下载路径
                for chapter in chapters:
                    if not any(existing_task["chapter_url"] == chapter["url"]
                               for task_list in [task_manager.downloading_tasks, task_manager.waiting_tasks,
                                                 task_manager.completed_tasks] # 不检查 error_tasks
                               for existing_task in task_list):
                        await task_manager.add_task(
                            chapter["url"],
                            chapter["name"],
                            comic_download_folder,
                            0,  # total_images
                            [],  # img_links
                            comic_name # 传入 comic_name
                        )
                    else:
                        logger.info(f"任务已存在，跳过添加: {chapter['name']}")
        elif event == "-DOWNLOADING-":  # 处理下载列表点击事件
            selected_index = window["-DOWNLOADING-"].get_indexes()
            # 可以在这里做一些事情，例如更新按钮状态
            window["-CANCEL-"].update(disabled=not selected_index)

        elif event == "-WAITING-":  # 处理等待列表点击事件
            selected_index = window["-WAITING-"].get_indexes()
            # 更新移动按钮和取消按钮的状态
            window["-MOVE_UP-"].update(disabled=not selected_index)
            window["-MOVE_DOWN-"].update(disabled=not selected_index)
            window["-MOVE_TOP-"].update(disabled=not selected_index)
            window["-MOVE_BOTTOM-"].update(disabled=not selected_index)
            window["-CANCEL-"].update(disabled=not selected_index and len(window["-DOWNLOADING-"].get_indexes()) == 0)


        elif event == "-CANCEL-":
            # 优先从 downloading_tasks 取消
            selected_index = window["-DOWNLOADING-"].get_indexes()
            if selected_index:
                task_to_cancel = task_manager.downloading_tasks[selected_index[0]]
            else:  # 如果 downloading_tasks 没有选中，再尝试从 waiting_tasks 取消
                selected_index = window["-WAITING-"].get_indexes()
                if selected_index:
                    task_to_cancel = task_manager.waiting_tasks[selected_index[0]]
                else:
                    task_to_cancel = None

            if task_to_cancel:
                await task_manager.cancel_task(task_to_cancel)

        elif event.startswith("-MOVE_"):
            selected_index = window["-WAITING-"].get_indexes()
            if selected_index:
                task_to_move = task_manager.waiting_tasks[selected_index[0]]
                if event == "-MOVE_UP-":
                    task_manager.move_task(task_to_move, "up")
                elif event == "-MOVE_DOWN-":
                    task_manager.move_task(task_to_move, "down")
                elif event == "-MOVE_TOP-":
                    task_manager.move_task(task_to_move, "top")
                elif event == "-MOVE_BOTTOM-":
                    task_manager.move_task(task_to_move, "bottom")

            # 简化按钮状态更新逻辑
            waiting_selected = len(window["-WAITING-"].get_indexes()) > 0
            downloading_selected = len(window["-DOWNLOADING-"].get_indexes()) > 0

            window["-CANCEL-"].update(disabled=not (waiting_selected or downloading_selected))
            window["-MOVE_UP-"].update(disabled=not waiting_selected)
            window["-MOVE_DOWN-"].update(disabled=not waiting_selected)
            window["-MOVE_TOP-"].update(disabled=not waiting_selected)
            window["-MOVE_BOTTOM-"].update(disabled=not waiting_selected)


        elif event == "-UPDATE_LISTS-":
            update_task_lists()

        await asyncio.sleep(0) # 将控制权交给 asyncio 事件循环

    window.close()
    await task_manager.close()  # 在程序退出时保存进度

asyncio.run(main_loop())

