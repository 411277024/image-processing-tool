import tkinter as tk
from tkinter import filedialog, messagebox, Scale, HORIZONTAL, Canvas, colorchooser
from PIL import Image, ImageOps, ImageTk, ImageFilter, ImageDraw
import numpy as np


class ImageEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("全能影像處理工具 (濾鏡 + 局部美顏 + 畫筆)")
        self.root.geometry("1100x700")

        # --- 變數初始化 ---
        self.original_img = None  # 原始的 PIL Image
        self.processed_img = None  # 處理後的 PIL Image (用於顯示和儲存)
        self.display_size = (500, 500)  # 預覽圖大小
        self.scale_factor = 1.0  # 縮放比例 (原圖尺寸 / 顯示尺寸)
        self.offset_x = 0
        self.offset_y = 0

        # 滑鼠操作變數
        self.last_x = None
        self.last_y = None
        self.rect_start = None
        self.rect_id = None

        # UI 變數
        self.file_path = tk.StringVar()
        self.mode_var = tk.StringVar(value="Original")
        self.threshold_var = tk.IntVar(value=127)
        self.k_color_var = tk.IntVar(value=8)
        self.filter_size_var = tk.IntVar(value=5)

        # 畫筆變數
        self.brush_color = "#000000"
        self.brush_size_var = tk.IntVar(value=5)

        # --- 介面佈局 ---
        self._setup_ui()

    def _setup_ui(self):
        # 1. 頂部工具列
        top_frame = tk.Frame(self.root, pady=10)
        top_frame.pack(side="top", fill="x")

        btn_open = tk.Button(top_frame, text="📂 開啟圖片", command=self.select_file, bg="#ddd", width=15)
        btn_open.pack(side="left", padx=20)

        btn_reset = tk.Button(top_frame, text="↩️ 重置圖片", command=self.reset_image, width=15)
        btn_reset.pack(side="left", padx=5)

        btn_save = tk.Button(top_frame, text="💾 儲存結果", command=self.save_image, bg="#ddd", width=15)
        btn_save.pack(side="left", padx=10)

        # 2. 主要區域
        main_container = tk.Frame(self.root)
        main_container.pack(fill="both", expand=True, padx=10, pady=5)

        # --- 左側：功能控制板 ---
        control_frame = tk.LabelFrame(main_container, text="功能選擇", width=250, padx=10, pady=10)
        control_frame.pack(side="left", fill="y")

        modes = [
            ("原始圖片", "Original"),
            ("🖌️ 自由畫筆 (繪圖)", "Brush"),  # 新增的功能
            ("✨ 局部美顏 (框選)", "Median"),
            ("--- 濾鏡特效 ---", "SEPARATOR"),
            ("灰階模式", "Grayscale"),
            ("黑白二值化", "BlackWhite"),
            ("色彩調色盤", "Palette"),
            ("銳化處理", "Sharpen"),
        ]

        for text, mode in modes:
            if mode == "SEPARATOR":
                tk.Frame(control_frame, height=2, bd=1, relief="sunken").pack(fill="x", pady=5)
                tk.Label(control_frame, text=text, fg="gray").pack(anchor="center")
            else:
                rb = tk.Radiobutton(control_frame, text=text, variable=self.mode_var,
                                    value=mode, command=self.apply_processing, anchor="w")
                rb.pack(fill="x", pady=2)

        tk.Frame(control_frame, height=2, bd=1, relief="sunken").pack(fill="x", pady=10)

        # 參數調整區 (動態顯示)
        self.param_frame = tk.Frame(control_frame)
        self.param_frame.pack(fill="x")

        # 說明文字
        self.lbl_info = tk.Label(control_frame, text="", fg="blue", wraplength=200, justify="left")
        self.lbl_info.pack(side="bottom", pady=20)

        # --- 右側：圖片顯示區 ---
        display_frame = tk.Frame(main_container)
        display_frame.pack(side="right", fill="both", expand=True)

        # 左圖 (原圖 Label)
        frame_org = tk.Frame(display_frame)
        frame_org.pack(side="left", expand=True)
        tk.Label(frame_org, text="[原始圖片]").pack()
        self.lbl_org = tk.Label(frame_org, bg="gray")
        self.lbl_org.pack(pady=5)

        # 右圖 (結果 Canvas)
        frame_res = tk.Frame(display_frame)
        frame_res.pack(side="right", expand=True)
        tk.Label(frame_res, text="[處理結果 - 可在此操作]").pack()

        self.canvas = Canvas(frame_res, bg="gray", width=self.display_size[0], height=self.display_size[1],
                             cursor="cross")
        self.canvas.pack(pady=5)

        # 綁定滑鼠事件 (整合了畫筆和局部美顏)
        self.canvas.bind("<Button-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)

    def update_param_ui(self):
        """根據選擇的模式，更新下方的參數調整器"""
        for widget in self.param_frame.winfo_children():
            widget.destroy()

        mode = self.mode_var.get()
        self.lbl_info.config(text="")  # 清空提示

        if mode == "Brush":
            # 畫筆控制項
            tk.Label(self.param_frame, text="畫筆設定:", font=("Arial", 10, "bold")).pack(anchor="w", pady=5)

            btn_color = tk.Button(self.param_frame, text="🎨 選擇顏色", command=self.choose_color)
            btn_color.pack(fill="x", pady=2)
            self.color_preview = tk.Label(self.param_frame, text="目前顏色", bg=self.brush_color, fg="white")
            self.color_preview.pack(fill="x", pady=2)

            tk.Label(self.param_frame, text="畫筆大小:").pack(anchor="w")
            Scale(self.param_frame, from_=1, to=30, orient=HORIZONTAL, variable=self.brush_size_var).pack(fill="x")
            self.lbl_info.config(text="【畫筆模式】\n直接在右圖拖曳滑鼠進行繪圖。")

        elif mode == "Median":
            tk.Label(self.param_frame, text="美顏/模糊強度:").pack(anchor="w")
            Scale(self.param_frame, from_=3, to=25, resolution=2, orient=HORIZONTAL,
                  variable=self.filter_size_var).pack(fill="x")
            self.lbl_info.config(text="【局部美顏】\n框選想要模糊/美顏的區域，放開滑鼠後生效。")

        elif mode == "BlackWhite":
            tk.Label(self.param_frame, text="閾值調整 (Threshold):").pack(anchor="w")
            Scale(self.param_frame, from_=0, to=255, orient=HORIZONTAL, variable=self.threshold_var,
                  command=lambda x: self.apply_processing()).pack(fill="x")
            tk.Button(self.param_frame, text="自動計算 (Otsu)", command=self.auto_otsu).pack(fill="x", pady=5)

        elif mode == "Palette":
            tk.Label(self.param_frame, text="顏色數量 (K):").pack(anchor="w")
            Scale(self.param_frame, from_=2, to=32, orient=HORIZONTAL, variable=self.k_color_var,
                  command=lambda x: self.apply_processing()).pack(fill="x")

    def choose_color(self):
        color = colorchooser.askcolor(color=self.brush_color, title="選擇畫筆顏色")
        if color[1]:
            self.brush_color = color[1]
            if hasattr(self, 'color_preview'):
                self.color_preview.config(bg=self.brush_color)

    def select_file(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg;*.jpeg;*.png;*.bmp")])
        if path:
            self.file_path.set(path)
            self.original_img = Image.open(path).convert("RGB")
            self.processed_img = self.original_img.copy()

            self.show_image_on_label(self.lbl_org, self.original_img)
            self.mode_var.set("Original")
            self.apply_processing()

    def reset_image(self):
        if self.original_img:
            self.processed_img = self.original_img.copy()
            self.mode_var.set("Original")
            self.apply_processing()
            messagebox.showinfo("重置", "圖片已還原")

    def auto_otsu(self):
        if not self.original_img: return
        gray = ImageOps.grayscale(self.original_img)
        np_img = np.array(gray)
        threshold_value = int(np.mean(np_img))
        self.threshold_var.set(threshold_value)
        self.apply_processing()

    def apply_processing(self, event=None):
        if not self.original_img: return

        self.update_param_ui()
        mode = self.mode_var.get()

        # 如果是「畫筆」或「局部美顏」，我們不重置圖片，而是在現有圖片上繼續操作
        if mode in ["Median", "Brush"]:
            self.show_image_on_canvas(self.processed_img)
            return

        # 其他全圖濾鏡模式，每次都從原圖重新計算
        img = self.original_img.copy()

        if mode == "Original":
            self.processed_img = img
        elif mode == "Grayscale":
            self.processed_img = ImageOps.grayscale(img).convert("RGB")
        elif mode == "BlackWhite":
            gray = ImageOps.grayscale(img)
            thresh = self.threshold_var.get()
            self.processed_img = gray.point(lambda p: 255 if p > thresh else 0).convert("RGB")
        elif mode == "Palette":
            k = self.k_color_var.get()
            self.processed_img = img.quantize(colors=k, method=Image.MEDIANCUT).convert("RGB")
        elif mode == "Sharpen":
            self.processed_img = img.filter(ImageFilter.SHARPEN)

        self.show_image_on_canvas(self.processed_img)

    def show_image_on_label(self, label, pil_image):
        display_img = pil_image.copy()
        display_img.thumbnail(self.display_size)
        tk_img = ImageTk.PhotoImage(display_img)
        label.config(image=tk_img)
        label.image = tk_img

    def show_image_on_canvas(self, pil_image):
        w, h = pil_image.size
        ratio = min(self.display_size[0] / w, self.display_size[1] / h)
        new_w = int(w * ratio)
        new_h = int(h * ratio)

        self.scale_factor = ratio
        self.offset_x = (self.display_size[0] - new_w) // 2
        self.offset_y = (self.display_size[1] - new_h) // 2

        resized_img = pil_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.tk_canvas_img = ImageTk.PhotoImage(resized_img)

        self.canvas.delete("all")
        self.canvas.create_image(self.display_size[0] // 2, self.display_size[1] // 2, image=self.tk_canvas_img,
                                 anchor="center")

    def get_real_coords(self, canvas_x, canvas_y):
        """將 Canvas 座標轉換回圖片真實座標"""
        real_x = int((canvas_x - self.offset_x) / self.scale_factor)
        real_y = int((canvas_y - self.offset_y) / self.scale_factor)
        return real_x, real_y

    # ==========================
    # 滑鼠事件 (畫筆 + 框選)
    # ==========================
    def on_mouse_down(self, event):
        mode = self.mode_var.get()
        if mode == "Median":
            self.rect_start = (event.x, event.y)
        elif mode == "Brush":
            self.last_x, self.last_y = self.get_real_coords(event.x, event.y)

    def on_mouse_drag(self, event):
        mode = self.mode_var.get()

        if mode == "Median" and self.rect_start:
            # 畫出紅色框框 (視覺效果)
            if self.rect_id: self.canvas.delete(self.rect_id)
            self.rect_id = self.canvas.create_rectangle(
                self.rect_start[0], self.rect_start[1], event.x, event.y,
                outline="red", width=2
            )

        elif mode == "Brush" and self.last_x is not None:
            # 畫筆邏輯
            current_x, current_y = self.get_real_coords(event.x, event.y)

            # 1. 在 PIL 圖片上繪製 (儲存數據)
            draw = ImageDraw.Draw(self.processed_img)
            draw.line([self.last_x, self.last_y, current_x, current_y],
                      fill=self.brush_color, width=self.brush_size_var.get(), joint="curve")

            # 2. 在 Canvas 上繪製 (即時顯示，避免卡頓)
            # 注意：這裡要在 Canvas 座標系上畫
            # 簡單起見，我們直接重繪整張圖有點慢，所以我們用 Canvas Line 模擬
            # 更好的做法是只畫線，等到放開滑鼠再刷新圖片
            self.canvas.create_line(event.x, event.y,
                                    (self.last_x * self.scale_factor + self.offset_x),
                                    (self.last_y * self.scale_factor + self.offset_y),
                                    fill=self.brush_color, width=self.brush_size_var.get() * self.scale_factor,
                                    capstyle=tk.ROUND)

            self.last_x, self.last_y = current_x, current_y

    def on_mouse_release(self, event):
        mode = self.mode_var.get()

        if mode == "Median" and self.rect_start:
            x0, y0 = self.rect_start
            x1, y1 = event.x, event.y

            # 清除框框
            if self.rect_id:
                self.canvas.delete(self.rect_id)
                self.rect_id = None
                self.rect_start = None

            # 座標換算
            real_x0, real_y0 = self.get_real_coords(x0, y0)
            real_x1, real_y1 = self.get_real_coords(x1, y1)

            # 整理座標
            sx, ex = sorted([real_x0, real_x1])
            sy, ey = sorted([real_y0, real_y1])

            # 邊界檢查
            sx = max(0, sx);
            sy = max(0, sy)
            ex = min(self.processed_img.width, ex);
            ey = min(self.processed_img.height, ey)

            if (ex - sx) < 5 or (ey - sy) < 5: return

            try:
                box = (sx, sy, ex, ey)
                region = self.processed_img.crop(box)
                size = self.filter_size_var.get()
                filtered_region = region.filter(ImageFilter.MedianFilter(size))
                self.processed_img.paste(filtered_region, box)
                self.show_image_on_canvas(self.processed_img)
            except Exception as e:
                print(f"Error: {e}")

        elif mode == "Brush":
            # 畫筆結束時，刷新一下 Canvas 確保圖片顯示是最新的 (因為 Drag 時我們用了 Canvas Line 模擬)
            self.show_image_on_canvas(self.processed_img)
            self.last_x = None
            self.last_y = None

    def save_image(self):
        if self.processed_img:
            path = filedialog.asksaveasfilename(defaultextension=".jpg",
                                                filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png")])
            if path:
                self.processed_img.save(path)
                messagebox.showinfo("成功", "圖片已儲存！")
        else:
            messagebox.showwarning("錯誤", "沒有可儲存的圖片")


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageEditorApp(root)
    root.mainloop()