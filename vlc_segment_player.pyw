import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import sys
import subprocess

class VLCSegmentPlayer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VLC 视频分段播放器 (增强稳定版)")
        self.geometry("1050x400")

        self.videos = []

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

    def build_time_selector(self, parent, col):
        """在 parent 的 row=0 上创建 时:分:秒 三级下拉选择器，返回 (h_var, m_var, s_var)。
        占用列范围为 [col, col+4]，共 5 列。"""
        h_var = tk.StringVar(value="00")
        m_var = tk.StringVar(value="00")
        s_var = tk.StringVar(value="00")

        hours = [f"{i:02d}" for i in range(24)]
        minsecs = [f"{i:02d}" for i in range(60)]

        ttk.Combobox(parent, textvariable=h_var, width=3, state="readonly", values=hours).grid(row=0, column=col, padx=(2, 0))
        tk.Label(parent, text=":").grid(row=0, column=col + 1)
        ttk.Combobox(parent, textvariable=m_var, width=3, state="readonly", values=minsecs).grid(row=0, column=col + 2)
        tk.Label(parent, text=":").grid(row=0, column=col + 3)
        ttk.Combobox(parent, textvariable=s_var, width=3, state="readonly", values=minsecs).grid(row=0, column=col + 4)

        return h_var, m_var, s_var

    def add_video_entry(self):
        frame = tk.Frame(self.videos_frame, pady=5, borderwidth=1, relief=tk.GROOVE)
        frame.pack(fill=tk.X, padx=5, pady=2, expand=True)
        frame.columnconfigure(1, weight=1)

        file_var = tk.StringVar()
        rate_var = tk.StringVar(value="1.0")

        tk.Button(frame, text="选择文件", command=lambda: self.browse_video(file_var)).grid(row=0, column=0, padx=5)
        tk.Entry(frame, textvariable=file_var).grid(row=0, column=1, padx=5, sticky="ew")

        tk.Label(frame, text="开始:").grid(row=0, column=2, padx=(10, 2))
        start_h, start_m, start_s = self.build_time_selector(frame, col=3)  # 占用列 3-7

        tk.Label(frame, text="结束:").grid(row=0, column=9, padx=(10, 2))
        end_h, end_m, end_s = self.build_time_selector(frame, col=10)  # 占用列 10-14

        tk.Label(frame, text="速度:").grid(row=0, column=16, padx=(10, 2))
        rate_cb = ttk.Combobox(frame, textvariable=rate_var, width=5, state="readonly", values=["0.5", "1.0", "1.25", "1.5", "2.0"])
        rate_cb.grid(row=0, column=17, padx=2)

        tk.Button(frame, text="X", fg="white", bg="#CD5C5C", relief=tk.FLAT, command=lambda: self.remove_video_entry(frame)).grid(row=0, column=18, padx=5)

        self.videos.append({
            "frame": frame,
            "file_var": file_var,
            "start_h": start_h, "start_m": start_m, "start_s": start_s,
            "end_h": end_h, "end_m": end_m, "end_s": end_s,
            "rate_var": rate_var,
        })

    def get_seconds(self, h_var, m_var, s_var):
        """将 时/分/秒 下拉框的值换算成总秒数。下拉框为只读，理论上不会出现非法值。"""
        try:
            h = int(h_var.get())
            m = int(m_var.get())
            s = int(s_var.get())
        except ValueError:
            return 0
        return h * 3600 + m * 60 + s

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

            start = self.get_seconds(v["start_h"], v["start_m"], v["start_s"])
            end = self.get_seconds(v["end_h"], v["end_m"], v["end_s"])

            # 结束时间为 00:00:00 视为"不设置结束时间"（播放到片尾）
            if end > 0 and end <= start:
                errors.append(f"第 {idx + 1} 个视频: 结束时间需大于开始时间，已跳过")
                continue

            args.append(path)
            if start > 0:
                args.append(f":start-time={start}")
            if end > 0:
                args.append(f":stop-time={end}")
            args.append(f":rate={v['rate_var'].get()}")

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
