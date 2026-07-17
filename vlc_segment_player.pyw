import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import sys
import subprocess

class VLCSegmentPlayer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VLC 视频分段播放器 ")
        self.geometry("1250x400")

        self.videos = []

        # 校验函数注册：只允许输入数字，且长度不超过 2 位（用于时/分/秒下拉输入框）
        self.vcmd_digits = (self.register(self._validate_digits), "%P")
        # 校验函数注册：允许数字和最多一个小数点（用于速度输入框）
        self.vcmd_rate = (self.register(self._validate_rate), "%P")

        # 1. VLC 路径配置区
        self.vlc_path_frame = tk.Frame(self)
        self.vlc_path_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(self.vlc_path_frame, text="VLC 路径:").pack(side=tk.LEFT)
        self.vlc_path_var = tk.StringVar(value=self.find_default_vlc_path())
        self.vlc_path_entry = tk.Entry(self.vlc_path_frame, textvariable=self.vlc_path_var)
        self.vlc_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tk.Button(self.vlc_path_frame, text="浏览...", command=self.browse_vlc).pack(side=tk.LEFT)

        # 2. 视频列表滚动区域
        self.canvas_frame = tk.Frame(self)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.videos_canvas = tk.Canvas(self.canvas_frame, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.canvas_frame, orient="vertical", command=self.videos_canvas.yview)
        self.videos_frame = tk.Frame(self.videos_canvas)

        self.videos_frame.bind(
            "<Configure>",
            lambda e: self.videos_canvas.configure(scrollregion=self.videos_canvas.bbox("all"))
        )

        self.canvas_window = self.videos_canvas.create_window((0, 0), window=self.videos_frame, anchor="nw")
        self.videos_canvas.configure(yscrollcommand=self.scrollbar.set)
        self.videos_canvas.bind('<Configure>', lambda event: self.videos_canvas.itemconfig(self.canvas_window, width=event.width))

        self.videos_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.bind_mouse_wheel(self.videos_canvas)

        # 3. 底部控制按钮区
        self.buttons_frame = tk.Frame(self)
        self.buttons_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(self.buttons_frame, text="+ 添加视频", command=self.add_video_entry, bg="#1E90FF", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(self.buttons_frame, text="▶ 播放全部", command=self.play_videos, bg="#228B22", fg="white", font=("Arial", 10, "bold")).pack(side=tk.RIGHT, padx=5)

        self.add_video_entry()

    def find_default_vlc_path(self):
        if sys.platform == "win32":
            paths = [r"C:\Program Files\VideoLAN\VLC\vlc.exe", r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"]
            for p in paths:
                if os.path.exists(p): return p
            return "vlc.exe"
        elif sys.platform == "darwin":
            path = "/Applications/VLC.app/Contents/MacOS/VLC"
            return path if os.path.exists(path) else "vlc"
        return "vlc"

    def browse_vlc(self):
        filetypes = [("Executable", "*.exe"), ("All Files", "*.*")] if sys.platform == "win32" else [("All Files", "*")]
        filename = filedialog.askopenfilename(title="选择 VLC 可执行文件", filetypes=filetypes)
        if filename: self.vlc_path_var.set(filename)

    # ---------- 输入校验相关 ----------

    def _validate_digits(self, proposed):
        """限制时/分/秒输入框只能输入 0-2 位数字（允许空字符串，方便用户先清空再输入）。"""
        if proposed == "":
            return True
        if not proposed.isdigit():
            return False
        if len(proposed) > 2:
            return False
        return True

    def _validate_rate(self, proposed):
        """限制速度输入框只能输入数字和最多一个小数点。"""
        if proposed == "":
            return True
        if proposed.count(".") > 1:
            return False
        return all(ch.isdigit() or ch == "." for ch in proposed)

    def _clamp_time_var(self, var, max_val):
        """输入框失去焦点时，将值规整为 0~max_val 范围内的两位数字符串。"""
        raw = var.get().strip()
        try:
            value = int(raw) if raw != "" else 0
        except ValueError:
            value = 0
        value = max(0, min(max_val, value))
        var.set(f"{value:02d}")

    def _clamp_rate_var(self, var):
        """速度输入框失去焦点时，规整为合法的正浮点数（默认 1.0，且不超过 8.0）。"""
        raw = var.get().strip()
        try:
            value = float(raw) if raw != "" else 1.0
        except ValueError:
            value = 1.0
        if value <= 0:
            value = 1.0
        value = min(value, 8.0)
        # 去掉多余的尾随 .0（保留一位小数即可，VLC 接受 1、1.5 等写法）
        var.set(f"{value:g}")

    def build_time_selector(self, parent, col):
        """在 parent 的 row=0 上创建 时:分:秒 三级可编辑下拉选择器（支持手动输入），
        返回 (h_var, m_var, s_var, widgets)，其中 widgets 是三个 Combobox 控件的列表，
        方便外部按需启用/禁用（例如"从头到尾播放"勾选时）。
        占用列范围为 [col, col+5]，共 6 列（每个单位后附带 时/分/秒 文字标签）。"""
        h_var = tk.StringVar(value="00")
        m_var = tk.StringVar(value="00")
        s_var = tk.StringVar(value="00")

        hours = [f"{i:02d}" for i in range(24)]
        minsecs = [f"{i:02d}" for i in range(60)]

        h_cb = ttk.Combobox(parent, textvariable=h_var, width=3, values=hours,
                             validate="key", validatecommand=self.vcmd_digits)
        h_cb.grid(row=0, column=col, padx=(2, 0))
        tk.Label(parent, text="时").grid(row=0, column=col + 1)

        m_cb = ttk.Combobox(parent, textvariable=m_var, width=3, values=minsecs,
                             validate="key", validatecommand=self.vcmd_digits)
        m_cb.grid(row=0, column=col + 2)
        tk.Label(parent, text="分").grid(row=0, column=col + 3)

        s_cb = ttk.Combobox(parent, textvariable=s_var, width=3, values=minsecs,
                             validate="key", validatecommand=self.vcmd_digits)
        s_cb.grid(row=0, column=col + 4)
        tk.Label(parent, text="秒").grid(row=0, column=col + 5)

        h_cb.bind("<FocusOut>", lambda e: self._clamp_time_var(h_var, 23))
        m_cb.bind("<FocusOut>", lambda e: self._clamp_time_var(m_var, 59))
        s_cb.bind("<FocusOut>", lambda e: self._clamp_time_var(s_var, 59))

        return h_var, m_var, s_var, [h_cb, m_cb, s_cb]

    def add_video_entry(self):
        frame = tk.Frame(self.videos_frame, pady=5, borderwidth=1, relief=tk.GROOVE)
        frame.pack(fill=tk.X, padx=5, pady=2, expand=True)
        frame.columnconfigure(1, weight=1)

        file_var = tk.StringVar()
        rate_var = tk.StringVar(value="1.0")
        full_play_var = tk.BooleanVar(value=False)

        tk.Button(frame, text="选择文件", command=lambda: self.browse_video(file_var)).grid(row=0, column=0, padx=5)
        tk.Entry(frame, textvariable=file_var).grid(row=0, column=1, padx=5, sticky="ew")

        # "从头到尾播放" 勾选框：勾选后忽略开始/结束时间，并禁用对应的时间输入框
        full_play_cb = tk.Checkbutton(
            frame, text="完整播放", variable=full_play_var,
            command=lambda: self.toggle_time_widgets(full_play_var, time_widgets)
        )
        full_play_cb.grid(row=0, column=2, padx=(10, 2))

        tk.Label(frame, text="开始:").grid(row=0, column=3, padx=(10, 2))
        start_h, start_m, start_s, start_widgets = self.build_time_selector(frame, col=4)  # 占用列 4-9

        tk.Label(frame, text="结束:").grid(row=0, column=11, padx=(10, 2))
        end_h, end_m, end_s, end_widgets = self.build_time_selector(frame, col=12)  # 占用列 12-17

        time_widgets = start_widgets + end_widgets

        tk.Label(frame, text="速度:").grid(row=0, column=19, padx=(10, 2))
        rate_cb = ttk.Combobox(frame, textvariable=rate_var, width=6,
                                values=["0.5", "1.0", "1.25", "1.5", "2.0"],
                                validate="key", validatecommand=self.vcmd_rate)
        rate_cb.grid(row=0, column=20, padx=2)
        rate_cb.bind("<FocusOut>", lambda e: self._clamp_rate_var(rate_var))

        tk.Button(frame, text="X", fg="white", bg="#CD5C5C", relief=tk.FLAT, command=lambda: self.remove_video_entry(frame)).grid(row=0, column=21, padx=5)

        self.videos.append({
            "frame": frame,
            "file_var": file_var,
            "start_h": start_h, "start_m": start_m, "start_s": start_s,
            "end_h": end_h, "end_m": end_m, "end_s": end_s,
            "rate_var": rate_var,
            "full_play_var": full_play_var,
        })

    def toggle_time_widgets(self, full_play_var, time_widgets):
        """勾选"完整播放"时禁用开始/结束时间输入框（仅作视觉提示，实际是否生效以 full_play_var 为准）；
        取消勾选时恢复可编辑。"""
        state = "disabled" if full_play_var.get() else "normal"
        for w in time_widgets:
            w.configure(state=state)

    def get_seconds(self, h_var, m_var, s_var):
        """将 时/分/秒 输入框的值换算成总秒数。由于允许手动输入，这里做容错处理并夹取到合法范围。"""
        def parse(var, max_val):
            try:
                value = int(var.get().strip() or 0)
            except ValueError:
                value = 0
            return max(0, min(max_val, value))

        h = parse(h_var, 23)
        m = parse(m_var, 59)
        s = parse(s_var, 59)
        return h * 3600 + m * 60 + s

    def get_rate(self, rate_var):
        """将速度输入框的值转换为合法的正浮点数，非法或缺失时回退为 1.0。"""
        try:
            value = float(rate_var.get().strip() or 1.0)
        except ValueError:
            value = 1.0
        if value <= 0:
            value = 1.0
        return value

    def play_videos(self):
        vlc_path = self.vlc_path_var.get()
        if not os.path.exists(vlc_path):
            messagebox.showerror("错误", "VLC 路径不存在")
            return

        args = [vlc_path]
        errors = []  # 收集所有出错/跳过的视频信息，最后统一提示

        for idx, v in enumerate(self.videos):
            path = v["file_var"].get().strip()

            if not path:
                errors.append(f"第 {idx + 1} 个视频: 未选择文件，已跳过")
                continue

            if not os.path.exists(path):
                errors.append(f"第 {idx + 1} 个视频: 文件不存在 ({path})，已跳过")
                continue

            full_play = v["full_play_var"].get()

            if full_play:
                # 勾选了"完整播放"：无视时间输入框，从头播放到片尾
                start = 0
                end = 0
            else:
                start = self.get_seconds(v["start_h"], v["start_m"], v["start_s"])
                end = self.get_seconds(v["end_h"], v["end_m"], v["end_s"])

                # 结束时间为 00:00:00 视为"不设置结束时间"（播放到片尾）
                if end > 0 and end <= start:
                    errors.append(f"第 {idx + 1} 个视频: 结束时间需大于开始时间，已跳过")
                    continue

            rate = self.get_rate(v["rate_var"])

            args.append(path)
            if start > 0:
                args.append(f":start-time={start}")
            if end > 0:
                args.append(f":stop-time={end}")
            args.append(f":rate={rate}")

        if errors:
            messagebox.showwarning("部分视频未播放", "\n".join(errors))

        if len(args) > 1:
            subprocess.Popen(args)
        else:
            messagebox.showerror("错误", "没有可播放的有效视频")

    def browse_video(self, file_var):
        f = filedialog.askopenfilename()
        if f: file_var.set(os.path.normpath(f))

    def remove_video_entry(self, frame):
        if len(self.videos) > 1:
            for v in self.videos:
                if v["frame"] == frame:
                    self.videos.remove(v)
                    frame.destroy()
                    break
        else: messagebox.showwarning("提示", "至少保留一个视频")

    def bind_mouse_wheel(self, widget):
        def _on_mousewheel(event):
            delta = int(-1 * (event.delta / 120)) if sys.platform == "win32" else (1 if event.num == 5 else -1)
            self.videos_canvas.yview_scroll(delta, "units")
        widget.bind("<MouseWheel>", _on_mousewheel)
        widget.bind("<Button-4>", _on_mousewheel)
        widget.bind("<Button-5>", _on_mousewheel)

if __name__ == "__main__":
    app = VLCSegmentPlayer()
    app.mainloop()
