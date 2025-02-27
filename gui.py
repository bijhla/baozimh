# gui.py
import PySimpleGUI as sg

def create_main_layout():
    """创建主窗口的布局"""

    # 定义颜色
    text_color = "white"
    bg_color = "#1B1D20"
    button_bg_color = "#595959"
    input_bg_color = "#2B2D30"

    # 设置全局主题 (PySimpleGUI 4.6 可能需要尝试不同的主题名称)
    sg.theme_background_color(bg_color)
    sg.theme_text_color(text_color)
    sg.theme_button_color((text_color, button_bg_color))
    sg.theme_input_background_color(input_bg_color)
    sg.theme_input_text_color(text_color)
    # sg.theme_element_text_color(text_color)  # 移除这行

    # 左侧布局 (搜索和章节选择)
    left_column = [
        [sg.Text("漫画搜索", font=("微软雅黑", 16), text_color=text_color, background_color=bg_color)],
        [
            sg.Text("漫画名", size=(8, 1), text_color=text_color, background_color=bg_color),
            sg.InputText(key="-SEARCH-", size=(20, 1), background_color=input_bg_color, text_color=text_color),
            sg.Button("搜索", key="-SEARCH_BTN-", button_color=(text_color, button_bg_color)),
        ],
        [sg.Text("搜索结果", font=("微软雅黑", 12), text_color=text_color, background_color=bg_color)],
        [
            sg.Listbox(
                values=[],
                size=(50, 10),
                key="-SEARCH_RESULTS-",
                enable_events=True,
                select_mode=sg.LISTBOX_SELECT_MODE_SINGLE,
                background_color=input_bg_color
            )
        ],
        [
            sg.Text("漫画地址", size=(8, 1),text_color=text_color, background_color=bg_color),
            sg.Text("", size=(30, 1), key="-COMIC_URL-", background_color=input_bg_color),
            sg.Button("复制", key="-COPY_URL-", disabled=True, button_color=(text_color, button_bg_color)),
        ],
        [sg.Text("目录列表", font=("微软雅黑", 12), text_color=text_color, background_color=bg_color)],
        [sg.Button("获取目录", key="-GET_CHAPTERS-", disabled=True, button_color=(text_color, button_bg_color))],

        [
            sg.Listbox(
                values=[],
                size=(50, 12),
                key="-CHAPTER_LIST-",
                enable_events=True,
                select_mode=sg.LISTBOX_SELECT_MODE_MULTIPLE,
                background_color=input_bg_color
            ),
        ],
        [
            sg.Button("下载选中", key="-DOWNLOAD-", disabled=True, button_color=(text_color, button_bg_color)),
            sg.Button("下载全部", key="-DOWNLOAD_ALL-", disabled=True, button_color=(text_color, button_bg_color)),
        ],
        [sg.Text("", key="-COMIC_NAME-", visible=False)], # 隐藏 COMIC_NAME
    ]

    # 右侧布局 (任务列表)
    right_column = [
        [sg.Text("下载列表", font=("微软雅黑", 16), text_color=text_color, background_color=bg_color)],
        [sg.Text("正在下载", font=("微软雅黑", 12), text_color=text_color, background_color=bg_color)],
        [
            sg.Listbox(
                values=[],
                size=(60, 6),
                key="-DOWNLOADING-",
                enable_events=True,
                select_mode=sg.LISTBOX_SELECT_MODE_SINGLE,
                background_color=input_bg_color
            )
        ],
        [sg.Text("等待下载", font=("微软雅黑", 12),text_color=text_color, background_color=bg_color)],
        [
            sg.Listbox(
                values=[],
                size=(60, 6),
                key="-WAITING-",
                enable_events=True,
                select_mode=sg.LISTBOX_SELECT_MODE_SINGLE,
                background_color=input_bg_color

            )
        ],
        [sg.Text("下载完成", font=("微软雅黑", 12),text_color=text_color, background_color=bg_color)],
        [
            sg.Listbox(
                values=[],
                size=(60, 6),
                key="-COMPLETED-",
                enable_events=False,
                select_mode=sg.LISTBOX_SELECT_MODE_SINGLE,
                background_color=input_bg_color

            )
        ],
        [sg.Text("下载出错", font=("微软雅黑", 12),text_color=text_color, background_color=bg_color)],
        [
            sg.Listbox(
                values=[],
                size=(60, 6),
                key="-ERROR-",
                enable_events=False,
                select_mode=sg.LISTBOX_SELECT_MODE_SINGLE,
                background_color=input_bg_color

            )
        ],
        [
            sg.Button("取消", key="-CANCEL-", disabled=True, button_color=(text_color, button_bg_color)),
            sg.Button("上移", key="-MOVE_UP-", disabled=True, button_color=(text_color, button_bg_color)),
            sg.Button("下移", key="-MOVE_DOWN-", disabled=True, button_color=(text_color, button_bg_color)),
            sg.Button("置顶", key="-MOVE_TOP-", disabled=True, button_color=(text_color, button_bg_color)),
            sg.Button("置底", key="-MOVE_BOTTOM-", disabled=True, button_color=(text_color, button_bg_color)),
        ],
    ]

    # 整体布局
    layout = [
        [
            sg.Column(left_column, background_color=bg_color),
            sg.VSeperator(),
            sg.Column(right_column, background_color=bg_color),
        ],
        [sg.Text("", key="-STATUS-", text_color="white", background_color=bg_color)],  # 状态栏
    ]
    return layout
