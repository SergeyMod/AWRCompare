"""
Главное окно приложения
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from typing import Optional

from ..parsers import AWRParser, PgProfileParser, BaseReportParser
from ..comparison import ComparisonEngine
from ..report_generator import ReportGenerator


class MainWindow:
    """Главное окно приложения для сравнения отчетов"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AWR/pg_profile Сравнение отчетов")
        self.root.geometry("1000x700")
        
        # Парсеры отчетов
        self.base_parser: Optional[BaseReportParser] = None
        self.target_parser: Optional[BaseReportParser] = None
        
        # Движок сравнения и генератор отчетов
        self.comparison_engine = ComparisonEngine()
        self.report_generator = ReportGenerator()
        
        # Результаты сравнения
        self.comparison_results = None
        
        self._create_widgets()
        
    def _create_widgets(self):
        """Создание виджетов интерфейса"""
        # Заголовок
        title_frame = ttk.Frame(self.root, padding="10")
        title_frame.pack(fill=tk.X)
        
        title_label = ttk.Label(
            title_frame,
            text="Сравнение отчетов AWR и pg_profile",
            font=("Arial", 16, "bold")
        )
        title_label.pack()
        
        # Фрейм для загрузки файлов
        files_frame = ttk.LabelFrame(self.root, text="Загрузка отчетов", padding="10")
        files_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Базовый отчет
        base_frame = ttk.Frame(files_frame)
        base_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(base_frame, text="Базовый отчет:", width=15).pack(side=tk.LEFT)
        self.base_file_var = tk.StringVar()
        ttk.Entry(base_frame, textvariable=self.base_file_var, width=60).pack(side=tk.LEFT, padx=5)
        ttk.Button(base_frame, text="Обзор...", command=self._select_base_file).pack(side=tk.LEFT)
        
        # Целевой отчет
        target_frame = ttk.Frame(files_frame)
        target_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(target_frame, text="Целевой отчет:", width=15).pack(side=tk.LEFT)
        self.target_file_var = tk.StringVar()
        ttk.Entry(target_frame, textvariable=self.target_file_var, width=60).pack(side=tk.LEFT, padx=5)
        ttk.Button(target_frame, text="Обзор...", command=self._select_target_file).pack(side=tk.LEFT)
        
        # Кнопка загрузки
        ttk.Button(files_frame, text="Загрузить отчеты", command=self._load_reports).pack(pady=5)
        
        # Информация об отчетах
        info_frame = ttk.LabelFrame(self.root, text="Информация об отчетах", padding="10")
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.info_text = scrolledtext.ScrolledText(info_frame, height=6, wrap=tk.WORD)
        self.info_text.pack(fill=tk.BOTH, expand=True)
        
        # Настройки сравнения
        settings_frame = ttk.LabelFrame(self.root, text="Настройки сравнения", padding="10")
        settings_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Выбор таблиц для сравнения
        tables_frame = ttk.Frame(settings_frame)
        tables_frame.pack(fill=tk.X)
        
        ttk.Label(tables_frame, text="Таблицы для сравнения:").pack(side=tk.LEFT)
        self.tables_listbox = tk.Listbox(tables_frame, selectmode=tk.MULTIPLE, height=4)
        self.tables_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        scrollbar = ttk.Scrollbar(tables_frame, orient=tk.VERTICAL, command=self.tables_listbox.yview)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.tables_listbox.config(yscrollcommand=scrollbar.set)
        
        # Кнопки управления
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X)
        
        ttk.Button(control_frame, text="Сравнить", command=self._compare_reports).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Экспорт в HTML", command=lambda: self._export_report('html')).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Экспорт в CSV", command=lambda: self._export_report('csv')).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Экспорт в JSON", command=lambda: self._export_report('json')).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Очистить", command=self._clear_all).pack(side=tk.RIGHT, padx=5)
        
        # Результаты сравнения
        results_frame = ttk.LabelFrame(self.root, text="Результаты сравнения", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.results_text = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD, font=("Courier", 9))
        self.results_text.pack(fill=tk.BOTH, expand=True)
        
        # Статус бар
        self.status_var = tk.StringVar(value="Готов к работе")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
    def _select_base_file(self):
        """Выбор базового файла отчета"""
        filename = filedialog.askopenfilename(
            title="Выберите базовый отчет",
            filetypes=[
                ("Все поддерживаемые", "*.html *.txt"),
                ("HTML файлы", "*.html"),
                ("Текстовые файлы", "*.txt"),
                ("Все файлы", "*.*")
            ]
        )
        if filename:
            self.base_file_var.set(filename)
            
    def _select_target_file(self):
        """Выбор целевого файла отчета"""
        filename = filedialog.askopenfilename(
            title="Выберите целевой отчет",
            filetypes=[
                ("Все поддерживаемые", "*.html *.txt"),
                ("HTML файлы", "*.html"),
                ("Текстовые файлы", "*.txt"),
                ("Все файлы", "*.*")
            ]
        )
        if filename:
            self.target_file_var.set(filename)
            
    def _load_reports(self):
        """Загрузка и парсинг отчетов"""
        base_file = self.base_file_var.get()
        target_file = self.target_file_var.get()
        
        if not base_file or not target_file:
            messagebox.showerror("Ошибка", "Выберите оба файла отчетов")
            return
        
        try:
            self.status_var.set("Загрузка отчетов...")
            self.root.update()
            
            # Определение типа и парсинг базового отчета
            self.base_parser = self._create_parser(base_file)
            if not self.base_parser.parse():
                raise Exception("Не удалось распарсить базовый отчет")
            
            # Определение типа и парсинг целевого отчета
            self.target_parser = self._create_parser(target_file)
            if not self.target_parser.parse():
                raise Exception("Не удалось распарсить целевой отчет")
            
            # Отображение информации об отчетах
            self._display_reports_info()
            
            # Заполнение списка доступных таблиц
            self._populate_tables_list()
            
            self.status_var.set("Отчеты успешно загружены")
            messagebox.showinfo("Успех", "Отчеты успешно загружены и распарсены")
            
        except Exception as e:
            self.status_var.set("Ошибка загрузки")
            messagebox.showerror("Ошибка", f"Ошибка при загрузке отчетов:\n{str(e)}")
            
    def _create_parser(self, file_path: str) -> BaseReportParser:
        """Создание парсера на основе содержимого файла"""
        # Чтение начала файла для определения типа
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(5000)  # Читаем первые 5000 символов
        
        # Определение типа отчета
        if 'AWR' in content or 'Automatic Workload Repository' in content:
            return AWRParser(file_path)
        elif 'pg_profile' in content or 'PostgreSQL' in content:
            return PgProfileParser(file_path)
        else:
            # По умолчанию пробуем AWR
            return AWRParser(file_path)
            
    def _display_reports_info(self):
        """Отображение информации об отчетах"""
        self.info_text.delete(1.0, tk.END)
        
        info = []
        info.append("БАЗОВЫЙ ОТЧЕТ:")
        info.append(f"  Тип: {self.base_parser.metadata.report_type}")
        info.append(f"  БД: {self.base_parser.metadata.database_name}")
        info.append(f"  Экземпляр: {self.base_parser.metadata.instance_name}")
        info.append(f"  Версия: {self.base_parser.metadata.version}")
        info.append(f"  Доступно таблиц: {len(self.base_parser.get_available_tables())}")
        info.append("")
        
        info.append("ЦЕЛЕВОЙ ОТЧЕТ:")
        info.append(f"  Тип: {self.target_parser.metadata.report_type}")
        info.append(f"  БД: {self.target_parser.metadata.database_name}")
        info.append(f"  Экземпляр: {self.target_parser.metadata.instance_name}")
        info.append(f"  Версия: {self.target_parser.metadata.version}")
        info.append(f"  Доступно таблиц: {len(self.target_parser.get_available_tables())}")
        
        self.info_text.insert(1.0, "\n".join(info))
        
    def _populate_tables_list(self):
        """Заполнение списка доступных таблиц"""
        self.tables_listbox.delete(0, tk.END)
        
        # Получение общих таблиц
        base_tables = set(self.base_parser.get_available_tables())
        target_tables = set(self.target_parser.get_available_tables())
        common_tables = base_tables & target_tables
        
        # Добавление в список
        for i, table in enumerate(sorted(common_tables)):
            self.tables_listbox.insert(tk.END, table)
            # Выбираем первые несколько таблиц по умолчанию
            if i < 3:
                self.tables_listbox.selection_set(i)
                
    def _compare_reports(self):
        """Выполнение сравнения отчетов"""
        if not self.base_parser or not self.target_parser:
            messagebox.showerror("Ошибка", "Сначала загрузите отчеты")
            return
        
        # Получение выбранных таблиц
        selected_indices = self.tables_listbox.curselection()
        if not selected_indices:
            messagebox.showerror("Ошибка", "Выберите хотя бы одну таблицу для сравнения")
            return
        
        selected_tables = [self.tables_listbox.get(i) for i in selected_indices]
        
        try:
            self.status_var.set("Выполнение сравнения...")
            self.root.update()
            
            # Выполнение сравнения
            self.comparison_results = self.comparison_engine.compare_reports(
                self.base_parser,
                self.target_parser,
                selected_tables
            )
            
            # Генерация текстового отчета
            report_text = self.report_generator.generate_report(
                self.comparison_results,
                output_format='text'
            )
            
            # Отображение результатов
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(1.0, report_text)
            
            self.status_var.set("Сравнение завершено")
            
        except Exception as e:
            self.status_var.set("Ошибка сравнения")
            messagebox.showerror("Ошибка", f"Ошибка при сравнении:\n{str(e)}")
            
    def _export_report(self, format_type: str):
        """Экспорт отчета в файл"""
        if not self.comparison_results:
            messagebox.showerror("Ошибка", "Сначала выполните сравнение")
            return
        
        # Выбор файла для сохранения
        filetypes = {
            'html': [("HTML файлы", "*.html")],
            'csv': [("CSV файлы", "*.csv")],
            'json': [("JSON файлы", "*.json")]
        }
        
        filename = filedialog.asksaveasfilename(
            title=f"Сохранить отчет как {format_type.upper()}",
            defaultextension=f".{format_type}",
            filetypes=filetypes.get(format_type, [("Все файлы", "*.*")])
        )
        
        if filename:
            try:
                self.status_var.set(f"Экспорт в {format_type.upper()}...")
                self.root.update()
                
                self.report_generator.generate_report(
                    self.comparison_results,
                    output_format=format_type,
                    output_path=filename
                )
                
                self.status_var.set(f"Отчет сохранен: {filename}")
                messagebox.showinfo("Успех", f"Отчет успешно сохранен:\n{filename}")
                
            except Exception as e:
                self.status_var.set("Ошибка экспорта")
                messagebox.showerror("Ошибка", f"Ошибка при экспорте:\n{str(e)}")
                
    def _clear_all(self):
        """Очистка всех данных"""
        self.base_file_var.set("")
        self.target_file_var.set("")
        self.info_text.delete(1.0, tk.END)
        self.results_text.delete(1.0, tk.END)
        self.tables_listbox.delete(0, tk.END)
        
        self.base_parser = None
        self.target_parser = None
        self.comparison_results = None
        
        self.status_var.set("Готов к работе")


def run_gui():
    """Запуск GUI приложения"""
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()
