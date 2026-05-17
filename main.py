import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox
from PIL import Image, ImageGrab  # pip install pillow
import os
import sys


class PaintApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("ЛисPaint")
        self.geometry("1000x700")
        self.minsize(800, 600)

        # текущее состояние
        self.current_color = "#000000"
        self.brush_size = 5
        self.current_tool = "brush"  # brush | eraser | line | rect | oval
        self.drawing = False
        self.last_x = None
        self.last_y = None
        self.start_x = None
        self.start_y = None
        self.temp_shape = None
        self.actions_stack = []  # для undo

        self._create_menu()
        self._create_ui()

        # бинды
        self._bind_shortcuts()

    # ---------- UI ----------

    def _create_menu(self):
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Новый", command=self.clear_canvas)
        file_menu.add_command(label="Открыть...", command=self.open_image)
        file_menu.add_command(label="Сохранить как...", command=self.save_image)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.quit)
        menubar.add_cascade(label="Файл", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Отменить", command=self.undo)
        menubar.add_cascade(label="Правка", menu=edit_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="О программе", command=self.show_about)
        menubar.add_cascade(label="Справка", menu=help_menu)

        self.config(menu=menubar)

    def _create_ui(self):
        # верхняя панель инструментов
        toolbar = tk.Frame(self, bd=2, relief=tk.RAISED)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        # кнопки инструментов
        self.tool_var = tk.StringVar(value="brush")

        def add_tool_button(text, tool_name):
            btn = tk.Radiobutton(
                toolbar,
                text=text,
                value=tool_name,
                variable=self.tool_var,
                indicatoron=False,
                width=10,
                command=self._on_tool_change
            )
            btn.pack(side=tk.LEFT, padx=2, pady=2)

        add_tool_button("Кисть", "brush")
        add_tool_button("Ластик", "eraser")
        add_tool_button("Линия", "line")
        add_tool_button("Прямоуг.", "rect")
        add_tool_button("Овал", "oval")

        # выбор цвета
        color_btn = tk.Button(toolbar, text="Цвет", command=self.choose_color)
        color_btn.pack(side=tk.LEFT, padx=5)

        # предпросмотр цвета
        self.color_preview = tk.Label(toolbar, bg=self.current_color, width=3)
        self.color_preview.pack(side=tk.LEFT, padx=2)

        # толщина кисти
        size_label = tk.Label(toolbar, text="Размер:")
        size_label.pack(side=tk.LEFT, padx=(15, 2))

        self.size_scale = tk.Scale(
            toolbar,
            from_=1,
            to=50,
            orient=tk.HORIZONTAL,
            command=self._on_size_change,
            length=150
        )
        self.size_scale.set(self.brush_size)
        self.size_scale.pack(side=tk.LEFT, padx=2)

        # кнопка очистки
        clear_btn = tk.Button(toolbar, text="Очистить", command=self.clear_canvas)
        clear_btn.pack(side=tk.LEFT, padx=10)

        # кнопка Undo
        undo_btn = tk.Button(toolbar, text="Отменить", command=self.undo)
        undo_btn.pack(side=tk.LEFT, padx=2)

        # холст
        self.canvas = tk.Canvas(self, bg="white", cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # бинды мыши
        self.canvas.bind("<Button-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

    def _bind_shortcuts(self):
        self.bind("<Control-s>", lambda e: self.save_image())
        self.bind("<Control-o>", lambda e: self.open_image())
        self.bind("<Control-n>", lambda e: self.clear_canvas())
        self.bind("<Control-z>", lambda e: self.undo())

        self.bind("b", lambda e: self._set_tool("brush"))
        self.bind("e", lambda e: self._set_tool("eraser"))
        self.bind("l", lambda e: self._set_tool("line"))
        self.bind("r", lambda e: self._set_tool("rect"))
        self.bind("o", lambda e: self._set_tool("oval"))

    # ---------- Логика инструментов ----------

    def _on_tool_change(self):
        self.current_tool = self.tool_var.get()

    def _set_tool(self, tool_name):
        self.tool_var.set(tool_name)
        self._on_tool_change()

    def _on_size_change(self, value):
        self.brush_size = int(value)

    def choose_color(self):
        color = colorchooser.askcolor(initialcolor=self.current_color)[1]
        if color:
            self.current_color = color
            self.color_preview.config(bg=color)

    # ---------- Рисование ----------

    def on_mouse_down(self, event):
        self.drawing = True
        self.last_x, self.last_y = event.x, event.y
        self.start_x, self.start_y = event.x, event.y

        if self.current_tool in ("line", "rect", "oval"):
            # создаём временную фигуру
            if self.current_tool == "line":
                self.temp_shape = self.canvas.create_line(
                    self.start_x, self.start_y, event.x, event.y,
                    fill=self._get_draw_color(),
                    width=self.brush_size
                )
            elif self.current_tool == "rect":
                self.temp_shape = self.canvas.create_rectangle(
                    self.start_x, self.start_y, event.x, event.y,
                    outline=self._get_draw_color(),
                    width=self.brush_size
                )
            elif self.current_tool == "oval":
                self.temp_shape = self.canvas.create_oval(
                    self.start_x, self.start_y, event.x, event.y,
                    outline=self._get_draw_color(),
                    width=self.brush_size
                )

    def on_mouse_move(self, event):
        if not self.drawing:
            return

        if self.current_tool in ("brush", "eraser"):
            color = self._get_draw_color()
            line_id = self.canvas.create_line(
                self.last_x, self.last_y, event.x, event.y,
                fill=color,
                width=self.brush_size,
                capstyle=tk.ROUND,
                smooth=True
            )
            self.actions_stack.append(line_id)
            self.last_x, self.last_y = event.x, event.y

        elif self.current_tool in ("line", "rect", "oval"):
            # обновляем временную фигуру
            if self.temp_shape is not None:
                if self.current_tool == "line":
                    self.canvas.coords(self.temp_shape,
                                       self.start_x, self.start_y, event.x, event.y)
                else:
                    self.canvas.coords(self.temp_shape,
                                       self.start_x, self.start_y, event.x, event.y)

    def on_mouse_up(self, event):
        if not self.drawing:
            return
        self.drawing = False

        if self.current_tool in ("line", "rect", "oval"):
            # финализируем фигуру
            if self.temp_shape is not None:
                self.actions_stack.append(self.temp_shape)
                self.temp_shape = None

        self.last_x = self.last_y = None
        self.start_x = self.start_y = None

    def _get_draw_color(self):
        if self.current_tool == "eraser":
            return "#FFFFFF"
        return self.current_color

    # ---------- Операции с холстом ----------

    def clear_canvas(self):
        self.canvas.delete("all")
        self.actions_stack.clear()

    def undo(self):
        if not self.actions_stack:
            return
        last_id = self.actions_stack.pop()
        self.canvas.delete(last_id)

    # ---------- Файлы ----------

    def _get_canvas_bbox_on_screen(self):
        self.update_idletasks()
        x = self.canvas.winfo_rootx()
        y = self.canvas.winfo_rooty()
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        return (x, y, x + w, y + h)

    def save_image(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg;*.jpeg"), ("Все файлы", "*.*")]
        )
        if not file_path:
            return

        try:
            bbox = self._get_canvas_bbox_on_screen()
            img = ImageGrab.grab(bbox)
            img.save(file_path)
            messagebox.showinfo("Сохранение", "Изображение сохранено.")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить изображение:\n{e}")

    def open_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Изображения", "*.png;*.jpg;*.jpeg;*.bmp;*.gif"),
                       ("Все файлы", "*.*")]
        )
        if not file_path:
            return

        try:
            img = Image.open(file_path)
            # подгоняем под размер холста
            self.update_idletasks()
            cw = self.canvas.winfo_width()
            ch = self.canvas.winfo_height()
            if cw > 0 and ch > 0:
                img = img.resize((cw, ch), Image.LANCZOS)

            self.bg_image = tk.PhotoImage(img)
            self.canvas.delete("all")
            self.actions_stack.clear()
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.bg_image)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть изображение:\n{e}")

    # ---------- Служебное ----------

    def show_about(self):
        messagebox.showinfo(
            "О программе",
            "ЛисPaint — простой рисовалка на tkinter.\n"
            "Управление:\n"
            "  B — кисть\n"
            "  E — ластик\n"
            "  L — линия\n"
            "  R — прямоугольник\n"
            "  O — овал\n"
            "  Ctrl+S — сохранить\n"
            "  Ctrl+O — открыть\n"
            "  Ctrl+N — новый\n"
            "  Ctrl+Z — отмена"
        )


def main():
    # фикс для корректного ImageGrab на некоторых системах
    if sys.platform.startswith("win"):
        os.environ["TK_SILENCE_DEPRECATION"] = "1"

    app = PaintApp()
    app.mainloop()


if __name__ == "__main__":
    main()
