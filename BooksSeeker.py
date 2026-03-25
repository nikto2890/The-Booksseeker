import os
import re
import json
from collections import Counter
from difflib import SequenceMatcher
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading

class SmartTextSearcherGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Умный поиск по текстовым файлам")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
        self.searcher = SmartTextSearcher()
        self.last_results = []
        self.current_file = ""
        
        self.use_synonyms = tk.BooleanVar(value=True)
        self.use_morphology = tk.BooleanVar(value=True)
        self.use_fuzzy = tk.BooleanVar(value=True)
        self.search_in_words = tk.BooleanVar(value=True)
        self.fuzzy_threshold = tk.IntVar(value=70)
        self.context_paragraphs = tk.IntVar(value=2)
        
        self.create_top_panel()
        self.create_center_panel()
        self.create_bottom_panel()
        self.create_status_bar()
        
    def create_top_panel(self):
        # Создаем Canvas и Scrollbar
        self.main_canvas = tk.Canvas(self.root)
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.main_canvas.yview)
        self.scrollable_frame = ttk.Frame(self.main_canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        )
        
        self.main_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.main_canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.main_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        top_frame = ttk.LabelFrame(self.scrollable_frame, text="Управление", padding="15")
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        title_label = ttk.Label(top_frame, text="УМНЫЙ ПОИСК ПО ТЕКСТОВЫМ ФАЙЛАМ", 
                                font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 15))
        
        file_frame = ttk.Frame(top_frame)
        file_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(file_frame, text="Файл:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 10))
        self.file_path_var = tk.StringVar(value="Файл не загружен")
        file_label = ttk.Label(file_frame, textvariable=self.file_path_var, 
                              font=('Arial', 9), foreground='gray', relief=tk.SUNKEN, padding=5)
        file_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        load_btn = ttk.Button(file_frame, text="📂 Загрузить файл", 
                              command=self.load_file, width=20)
        load_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        search_frame = ttk.Frame(top_frame)
        search_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(search_frame, text="Поисковый запрос:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        self.query_entry = ttk.Entry(search_frame, font=('Arial', 11))
        self.query_entry.pack(fill=tk.X, pady=(0, 10))
        self.query_entry.bind('<Return>', lambda e: self.perform_search())
        
        settings_label = ttk.Label(search_frame, text="Настройки поиска:", font=('Arial', 10, 'bold'))
        settings_label.pack(anchor=tk.W, pady=(5, 5))
        
        row1 = ttk.Frame(search_frame)
        row1.pack(fill=tk.X, pady=2)
        
        cb1 = ttk.Checkbutton(row1, text="🔍 Использовать синонимы", variable=self.use_synonyms)
        cb1.pack(side=tk.LEFT, padx=(0, 20))
        
        cb2 = ttk.Checkbutton(row1, text="📖 Учитывать падежи", variable=self.use_morphology)
        cb2.pack(side=tk.LEFT)
        
        row2 = ttk.Frame(search_frame)
        row2.pack(fill=tk.X, pady=2)
        
        cb3 = ttk.Checkbutton(row2, text="🔎 Нечеткий поиск (похожие слова, минимум 3 буквы)", 
                             variable=self.use_fuzzy)
        cb3.pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(row2, text="Порог схожести:").pack(side=tk.LEFT)
        fuzzy_spin = ttk.Spinbox(row2, from_=50, to=100, width=5, 
                                 textvariable=self.fuzzy_threshold)
        fuzzy_spin.pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(row2, text="%").pack(side=tk.LEFT, padx=(5, 0))
        
        row3 = ttk.Frame(search_frame)
        row3.pack(fill=tk.X, pady=2)
        
        cb4 = ttk.Checkbutton(row3, text="🔤 Искать внутри слов (например 'ю' найдет 'верблюда')", 
                             variable=self.search_in_words)
        cb4.pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(row3, text="Контекст:").pack(side=tk.LEFT)
        ttk.Spinbox(row3, from_=1, to=10, width=5, 
                   textvariable=self.context_paragraphs).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(row3, text="параграфов").pack(side=tk.LEFT, padx=(5, 0))
        
        self.search_btn = ttk.Button(search_frame, text="🔎 НАЙТИ", 
                                     command=self.perform_search)
        self.search_btn.pack(pady=(15, 0))
        
    def create_center_panel(self):
        center_frame = ttk.LabelFrame(self.scrollable_frame, text="Результаты", padding="10")
        center_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        paned = ttk.PanedWindow(center_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        ttk.Label(left_frame, text="📋 Список найденных фрагментов", 
                 font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        
        list_container = ttk.Frame(left_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        list_scrollbar = ttk.Scrollbar(list_container)
        list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.results_listbox = tk.Listbox(list_container, height=15, font=('Arial', 10),
                                          yscrollcommand=list_scrollbar.set)
        self.results_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scrollbar.config(command=self.results_listbox.yview)
        self.results_listbox.bind('<<ListboxSelect>>', self.on_result_select)
        
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)
        
        ttk.Label(right_frame, text="📄 Контекст (найденные слова выделены цветом)", 
                 font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        
        self.context_text = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, 
                                                      font=('Courier', 10))
        self.context_text.pack(fill=tk.BOTH, expand=True)
        
        self.context_text.tag_configure('found', background='lightgreen', 
                                       foreground='black', font=('Courier', 10, 'bold'))
        
    def create_bottom_panel(self):
        bottom_frame = ttk.LabelFrame(self.scrollable_frame, text="Действия", padding="10")
        bottom_frame.pack(fill=tk.X, padx=10, pady=10)
        
        row1 = ttk.Frame(bottom_frame)
        row1.pack(pady=5)
        
        self.clear_btn = ttk.Button(row1, text="🗑 ОЧИСТИТЬ РЕЗУЛЬТАТЫ", 
                                    command=self.clear_results,
                                    width=25)
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        self.stats_btn = ttk.Button(row1, text="📊 СТАТИСТИКА ФАЙЛА", 
                                    command=self.show_stats,
                                    width=25)
        self.stats_btn.pack(side=tk.LEFT, padx=5)
        
        self.extended_btn = ttk.Button(row1, text="📖 РАСШИРЕННЫЙ КОНТЕКСТ", 
                                       command=self.show_extended_context,
                                       width=25)
        self.extended_btn.pack(side=tk.LEFT, padx=5)
        
        row2 = ttk.Frame(bottom_frame)
        row2.pack(pady=5)
        
        self.export_btn = ttk.Button(row2, text="📎 ЭКСПОРТ В HTML", 
                                     command=self.export_to_html,
                                     width=25)
        self.export_btn.pack(side=tk.LEFT, padx=5)
        
        self.help_btn = ttk.Button(row2, text="❓ ПОМОЩЬ", 
                                   command=self.show_help,
                                   width=25)
        self.help_btn.pack(side=tk.LEFT, padx=5)
        
        self.exit_btn = ttk.Button(row2, text="🚪 ВЫХОД", 
                                   command=self.root.quit,
                                   width=25)
        self.exit_btn.pack(side=tk.LEFT, padx=5)
        
        info_frame = ttk.Frame(bottom_frame)
        info_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(info_frame, text="Информация:", font=('Arial', 9, 'bold')).pack(side=tk.LEFT, padx=(0, 5))
        self.info_var = tk.StringVar(value="Готов к работе. Загрузите файл для начала поиска.")
        info_label = ttk.Label(info_frame, textvariable=self.info_var, 
                               font=('Arial', 9), foreground='blue')
        info_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
    def create_status_bar(self):
        self.status_bar = ttk.Label(self.scrollable_frame, text="Готов", relief=tk.SUNKEN, anchor=tk.W, padding=5)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))
        
    def load_file(self):
        file_path = filedialog.askopenfilename(
            title="Выберите текстовый файл",
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
        )
        
        if file_path:
            success, message = self.searcher.load_file(file_path)
            if success:
                self.current_file = file_path
                self.file_path_var.set(os.path.basename(file_path))
                self.update_status(f"Файл загружен: {os.path.basename(file_path)}")
                
                stats, _ = self.searcher.get_stats()
                if isinstance(stats, dict):
                    self.info_var.set(f"📄 {os.path.basename(file_path)} | Слов: {stats.get('Слов', 0)}")
            else:
                messagebox.showerror("Ошибка", message)
                
    def perform_search(self):
        if not hasattr(self, 'results_listbox'):
            return
            
        if not self.searcher.content:
            messagebox.showwarning("Предупреждение", "Сначала загрузите файл!")
            return
            
        query = self.query_entry.get().strip()
        if not query:
            messagebox.showwarning("Предупреждение", "Введите поисковый запрос!")
            return
            
        self.results_listbox.delete(0, tk.END)
        self.context_text.delete(1.0, tk.END)
        
        def search_thread():
            try:
                self.update_status("Поиск...")
                self.info_var.set("🔍 Идет поиск...")
                
                results, found_words, search_terms = self.searcher.smart_search(
                    query, 
                    use_synonyms=self.use_synonyms.get(),
                    use_morphology=self.use_morphology.get(),
                    context_paragraphs=self.context_paragraphs.get(),
                    use_fuzzy=self.use_fuzzy.get(),
                    fuzzy_threshold=self.fuzzy_threshold.get(),
                    search_in_words=self.search_in_words.get()
                )
                
                self.root.after(0, self.display_results, results, found_words, search_terms, query)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
        
        threading.Thread(target=search_thread, daemon=True).start()
        
    def display_results(self, results, found_words, search_terms, query):
        if not hasattr(self, 'results_listbox'):
            return
            
        self.last_results = results
        
        if results:
            for i, res in enumerate(results, 1):
                preview = res['context'][:80].replace('\n', ' ') + "..."
                self.results_listbox.insert(tk.END, f"{i:3d}. [{res['word']}] {preview}")
            
            self.info_var.set(f"✅ Найдено {len(results)} совпадений по запросу: '{query}'")
            self.update_status(f"Найдено {len(results)} совпадений")
        else:
            self.results_listbox.insert(tk.END, "Ничего не найдено")
            self.info_var.set(f"❌ По запросу '{query}' ничего не найдено")
            
    def on_result_select(self, event):
        selection = self.results_listbox.curselection()
        if selection and self.last_results:
            index = selection[0]
            if index < len(self.last_results):
                result = self.last_results[index]
                
                self.context_text.delete(1.0, tk.END)
                clean_context = result['context'].replace('**', '')
                self.context_text.insert(1.0, clean_context)
                self.highlight_words_in_context(result['context'])
                
    def highlight_words_in_context(self, context_with_markers):
        pattern = r'\*\*([^*]+)\*\*'
        matches = re.findall(pattern, context_with_markers)
        
        for word in matches:
            start = 1.0
            while True:
                start = self.context_text.search(re.escape(word), start, tk.END)
                if not start:
                    break
                end = f"{start}+{len(word)}c"
                self.context_text.tag_add('found', start, end)
                start = end
            
    def show_extended_context(self):
        selection = self.results_listbox.curselection()
        if not selection:
            messagebox.showinfo("Информация", "Выберите результат из списка")
            return
            
        index = selection[0]
        if index >= len(self.last_results):
            return
            
        result = self.last_results[index]
        
        extended_window = tk.Toplevel(self.root)
        extended_window.title(f"Расширенный контекст - результат {index + 1}")
        extended_window.geometry("1000x700")
        
        text_widget = scrolledtext.ScrolledText(extended_window, wrap=tk.WORD, 
                                                font=('Courier', 10))
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        extended_context = self.searcher.show_detailed_context(result, 3)
        clean_context = extended_context.replace('**', '')
        text_widget.insert(1.0, clean_context)
        
        text_widget.tag_configure('highlight', background='yellow')
        pattern = r'\*\*([^*]+)\*\*'
        matches = re.findall(pattern, extended_context)
        
        for word in matches:
            start = 1.0
            while True:
                start = text_widget.search(re.escape(word), start, tk.END)
                if not start:
                    break
                end = f"{start}+{len(word)}c"
                text_widget.tag_add('highlight', start, end)
                start = end
            
    def show_stats(self):
        if not self.searcher.content:
            messagebox.showwarning("Предупреждение", "Сначала загрузите файл!")
            return
            
        stats, top_words = self.searcher.get_stats()
        
        if isinstance(stats, str):
            messagebox.showinfo("Информация", stats)
            return
        
        stats_window = tk.Toplevel(self.root)
        stats_window.title("Статистика файла")
        stats_window.geometry("600x500")
        
        text_widget = scrolledtext.ScrolledText(stats_window, wrap=tk.WORD, 
                                                font=('Arial', 10))
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget.insert(tk.END, "📊 СТАТИСТИКА ФАЙЛА\n", 'header')
        text_widget.insert(tk.END, "="*50 + "\n\n")
        
        for key, value in stats.items():
            text_widget.insert(tk.END, f"{key}: {value}\n")
        
        if top_words:
            text_widget.insert(tk.END, "\n\n📈 ТОП-10 САМЫХ ЧАСТЫХ СЛОВ:\n", 'header')
            text_widget.insert(tk.END, "="*50 + "\n")
            for i, (word, count) in enumerate(top_words, 1):
                text_widget.insert(tk.END, f"{i:2d}. {word}: {count}\n")
        
        text_widget.tag_configure('header', font=('Arial', 12, 'bold'), foreground='blue')
        
    def export_to_html(self):
        if not self.last_results:
            messagebox.showinfo("Информация", "Нет результатов для экспорта")
            return
            
        file_path = filedialog.asksaveasfilename(
            title="Экспорт в HTML",
            defaultextension=".html",
            filetypes=[("HTML файлы", "*.html"), ("Все файлы", "*.*")]
        )
        
        if file_path:
            try:
                html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Результаты поиска</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }}
        h1 {{ color: #333; border-bottom: 3px solid #4CAF50; }}
        .result {{ margin-bottom: 30px; border-left: 4px solid #4CAF50; padding-left: 15px; }}
        .result h3 {{ color: #4CAF50; margin-bottom: 5px; }}
        .word {{ background: #ffeb3b; padding: 2px 5px; border-radius: 3px; font-weight: bold; }}
        .context {{ background: #f9f9f9; padding: 10px; border-radius: 5px; font-family: monospace; }}
        hr {{ margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📋 Результаты поиска</h1>
        <p><strong>Найдено фрагментов:</strong> {len(self.last_results)}</p>
        <hr>
"""
                
                for i, res in enumerate(self.last_results, 1):
                    context_html = res['context']
                    pattern = r'\*\*([^*]+)\*\*'
                    
                    def replace_match(match):
                        return f'<span class="word">{match.group(1)}</span>'
                    
                    context_html = re.sub(pattern, replace_match, context_html)
                    context_html = context_html.replace('\n', '<br>')
                    
                    html_content += f"""
        <div class="result">
            <h3>Результат {i}</h3>
            <p><strong>Найдено слово:</strong> <span class="word">{res['word']}</span></p>
            <div class="context">{context_html}</div>
        </div>
        <hr>
"""
                
                html_content += """
    </div>
</body>
</html>"""
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                messagebox.showinfo("Успех", f"Результаты экспортированы в HTML:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось экспортировать файл:\n{str(e)}")
                
    def clear_results(self):
        if hasattr(self, 'results_listbox') and hasattr(self, 'context_text'):
            self.results_listbox.delete(0, tk.END)
            self.context_text.delete(1.0, tk.END)
        self.last_results = []
        self.info_var.set("🗑 Результаты очищены")
        
    def show_help(self):
        help_text = """📖 СПРАВКА ПО ПРОГРАММЕ

🔍 ПОИСК:
- Введите слово или букву
- Нажмите кнопку "НАЙТИ" или Enter

⚙️ НАСТРОЙКИ:
- "Искать внутри слов" - ВКЛЮЧИТЕ для поиска букв внутри слов
  Например: поиск "ю" найдет "верблюда"
- "Нечеткий поиск" - работает только для слов из 3+ букв
- "Порог схожести" - 70% оптимально

📋 РАБОТА С РЕЗУЛЬТАТАМИ:
- Кликните на результат для просмотра контекста
- "Расширенный контекст" - показывает больше текста
- "Экспорт в HTML" - сохраняет результаты в веб-страницу

💡 ПРИМЕРЫ:
- Поиск "ю" с включенным "Искать внутри слов" → найдет "верблюда"
- Поиск "верблюда" → найдет только слова с корнем "верблюд"
- Поиск "п" → найдет все слова с буквой "п" """
        
        messagebox.showinfo("Помощь", help_text)
        
    def update_status(self, message):
        if hasattr(self, 'status_bar'):
            self.status_bar.config(text=message)
            self.root.update_idletasks()


class SmartTextSearcher:
    def __init__(self):
        self.content = ""
        self.file_path = ""
        self.encoding = "utf-8"
        self.synonyms_dict = self.load_synonyms()
        self.morph_available = False
        
        try:
            import pymorphy2
            self.morph = pymorphy2.MorphAnalyzer()
            self.morph_available = True
        except ImportError:
            pass
    
    def load_synonyms(self):
        return {
            'большой': ['крупный', 'огромный', 'гигантский', 'громадный'],
            'маленький': ['крошечный', 'мелкий', 'небольшой', 'миниатюрный'],
            'хороший': ['отличный', 'прекрасный', 'замечательный', 'великолепный'],
            'плохой': ['ужасный', 'отвратительный', 'скверный', 'нехороший'],
            'красивый': ['прекрасный', 'великолепный', 'очаровательный', 'привлекательный'],
            'умный': ['сообразительный', 'толковый', 'разумный', 'интеллектуальный'],
            'быстрый': ['скорый', 'стремительный', 'проворный', 'шустрый'],
            'медленный': ['неторопливый', 'неспешный', 'черепаший'],
            'радость': ['счастье', 'веселье', 'восторг', 'ликование'],
            'грусть': ['печаль', 'тоска', 'уныние', 'скорбь'],
            'говорить': ['сказать', 'произносить', 'вещать', 'изрекать', 'молвить'],
            'смотреть': ['глядеть', 'взирать', 'лицезреть', 'пялиться'],
            'думать': ['мыслить', 'размышлять', 'рассуждать', 'соображать'],
            'работа': ['труд', 'дело', 'занятие', 'деятельность'],
            'дом': ['здание', 'жилище', 'обитель', 'кров'],
        }
    
    def get_all_word_forms(self, word):
        if not self.morph_available:
            return [word.lower()]
        
        try:
            parsed = self.morph.parse(word)[0]
            normal_form = parsed.normal_form
            all_forms = set()
            all_forms.add(normal_form.lower())
            all_forms.add(word.lower())
            
            if 'NOUN' in parsed.tag:
                cases = ['nomn', 'gent', 'datv', 'accs', 'ablt', 'loct']
                for case in cases:
                    for number in ['sing', 'plur']:
                        try:
                            form = parsed.inflect({case, number})
                            if form:
                                all_forms.add(form.word.lower())
                        except:
                            pass
            
            elif 'ADJF' in parsed.tag or 'ADJS' in parsed.tag:
                cases = ['nomn', 'gent', 'datv', 'accs', 'ablt', 'loct']
                genders = ['masc', 'femn', 'neut']
                numbers = ['sing', 'plur']
                
                for case in cases:
                    for number in numbers:
                        if number == 'sing':
                            for gender in genders:
                                try:
                                    form = parsed.inflect({case, number, gender})
                                    if form:
                                        all_forms.add(form.word.lower())
                                except:
                                    pass
                        else:
                            try:
                                form = parsed.inflect({case, number})
                                if form:
                                    all_forms.add(form.word.lower())
                            except:
                                    pass
            
            elif 'VERB' in parsed.tag:
                tenses = ['pres', 'past', 'futr']
                persons = ['1per', '2per', '3per']
                numbers = ['sing', 'plur']
                genders = ['masc', 'femn', 'neut']
                
                for tense in tenses:
                    for number in numbers:
                        if tense == 'past':
                            for gender in genders:
                                try:
                                    form = parsed.inflect({tense, number, gender})
                                    if form:
                                        all_forms.add(form.word.lower())
                                except:
                                    pass
                        else:
                            for person in persons:
                                try:
                                    form = parsed.inflect({tense, number, person})
                                    if form:
                                        all_forms.add(form.word.lower())
                                except:
                                    pass
            
            return list(all_forms)
        except:
            return [word.lower()]
    
    def get_synonyms_with_forms(self, word):
        synonyms = self.get_synonyms(word)
        all_forms = set()
        all_forms.update(self.get_all_word_forms(word))
        
        for syn in synonyms:
            all_forms.update(self.get_all_word_forms(syn))
        
        return list(all_forms)
    
    def get_synonyms(self, word):
        word_lower = word.lower()
        synonyms = set()
        
        if word_lower in self.synonyms_dict:
            synonyms.update(self.synonyms_dict[word_lower])
        
        for key, values in self.synonyms_dict.items():
            if word_lower in [v.lower() for v in values]:
                synonyms.add(key)
                synonyms.update(values)
        
        return list(synonyms)
    
    def calculate_similarity(self, word1, word2):
        return SequenceMatcher(None, word1.lower(), word2.lower()).ratio() * 100
    
    def find_similar_words(self, query_word, text_words, threshold=70):
        similar = set()
        query_word_lower = query_word.lower()
        
        if len(query_word_lower) < 3:
            return []
        
        for word in text_words:
            if len(word) < 3:
                continue
            similarity = self.calculate_similarity(query_word_lower, word)
            if similarity >= threshold:
                similar.add(word)
        
        return list(similar)
    
    def load_file(self, file_path):
        encodings = ['utf-8', 'cp1251', 'windows-1251', 'koi8-r', 'latin-1']
        
        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc) as file:
                    self.content = file.read()
                self.file_path = file_path
                self.encoding = enc
                return True, f"Файл загружен (кодировка: {enc})"
            except UnicodeDecodeError:
                continue
            except FileNotFoundError:
                return False, "Файл не найден"
        
        return False, "Не удалось прочитать файл"
    
    def extract_surrounding_text(self, position, paragraph_count=2):
        paragraphs = re.split(r'\n\s*\n', self.content)
        
        char_count = 0
        target_para_idx = -1
        
        for i, para in enumerate(paragraphs):
            para_start = char_count
            para_end = char_count + len(para)
            if para_start <= position <= para_end:
                target_para_idx = i
                break
            char_count += len(para) + 2
        
        if target_para_idx == -1:
            return "Не удалось определить контекст"
        
        start_idx = max(0, target_para_idx - paragraph_count)
        end_idx = min(len(paragraphs), target_para_idx + paragraph_count + 1)
        
        surrounding = []
        for i in range(start_idx, end_idx):
            surrounding.append(paragraphs[i])
        
        return "\n\n".join(surrounding)
    
    def smart_search(self, query, use_synonyms=True, use_morphology=True, context_paragraphs=2, use_fuzzy=False, fuzzy_threshold=70, search_in_words=False):
        if not self.content:
            return None, "Сначала загрузите файл"
        
        search_terms = set()
        query_words = re.findall(r'\b\w+\b', query.lower())
        
        if search_in_words and len(query) > 0:
            search_terms.add(query.lower())
        
        for word in query_words:
            if use_morphology and self.morph_available and len(word) > 1:
                word_forms = self.get_all_word_forms(word)
                search_terms.update(word_forms)
                
                if use_synonyms:
                    syn_forms = self.get_synonyms_with_forms(word)
                    search_terms.update(syn_forms)
            else:
                search_terms.add(word.lower())
                if use_synonyms and len(word) > 1:
                    search_terms.update(self.get_synonyms(word))
        
        if use_fuzzy:
            all_words_in_text = set(re.findall(r'\b\w+\b', self.content.lower()))
            fuzzy_matches = set()
            
            for query_word in query_words:
                similar = self.find_similar_words(query_word, all_words_in_text, fuzzy_threshold)
                fuzzy_matches.update(similar)
            
            search_terms.update(fuzzy_matches)
        
        highlight_terms = set()
        for word in query_words:
            highlight_terms.add(word.lower())
            if use_synonyms and len(word) > 1:
                highlight_terms.update(self.get_synonyms(word))
        
        if search_in_words and len(query) > 0:
            highlight_terms.add(query.lower())
        
        search_terms = list(search_terms)
        highlight_terms = list(highlight_terms)
        
        if not search_terms:
            return [], set(), []
        
        results = []
        found_words = set()
        
        if search_in_words:
            for term in search_terms:
                pattern = re.escape(term)
                for match in re.finditer(pattern, self.content, re.IGNORECASE):
                    start, end = match.span()
                    found_word = self.content[start:end]
                    found_words.add(found_word.lower())
                    
                    context = self.extract_surrounding_text(start, context_paragraphs)
                    
                    for hterm in highlight_terms:
                        hpattern = re.escape(hterm)
                        context = re.sub(
                            hpattern,
                            lambda m: f'**{m.group(0)}**',
                            context,
                            flags=re.IGNORECASE
                        )
                    
                    result = {
                        'word': found_word,
                        'position': start,
                        'context': context,
                        'paragraphs': context_paragraphs * 2 + 1
                    }
                    results.append(result)
        else:
            pattern = r'\b(' + '|'.join(re.escape(term) for term in search_terms) + r')\b'
            regex = re.compile(pattern, re.IGNORECASE)
            
            for match in regex.finditer(self.content):
                start, end = match.span()
                found_word = self.content[start:end]
                found_words.add(found_word.lower())
                
                context = self.extract_surrounding_text(start, context_paragraphs)
                
                for term in highlight_terms:
                    term_pattern = r'\b' + re.escape(term) + r'\b'
                    context = re.sub(
                        term_pattern,
                        lambda m: f'**{m.group(0)}**',
                        context,
                        flags=re.IGNORECASE
                    )
                
                result = {
                    'word': found_word,
                    'position': start,
                    'context': context,
                    'paragraphs': context_paragraphs * 2 + 1
                }
                results.append(result)
        
        unique_results = []
        seen_contexts = set()
        
        for res in results:
            if res['context'] not in seen_contexts:
                seen_contexts.add(res['context'])
                unique_results.append(res)
        
        return unique_results, found_words, search_terms
    
    def show_detailed_context(self, result, additional_paragraphs=2):
        if not self.content:
            return "Нет контекста"
        
        extended_context = self.extract_surrounding_text(
            result['position'], 
            result['paragraphs'] + additional_paragraphs
        )
        
        return extended_context
    
    def get_stats(self):
        if not self.content:
            return "Сначала загрузите файл"
        
        words = re.findall(r'\b\w+\b', self.content.lower())
        sentences = re.split(r'[.!?]+', self.content)
        paragraphs = re.split(r'\n\s*\n', self.content)
        
        stats = {
            "Символов": len(self.content),
            "Слов": len(words),
            "Уникальных слов": len(set(words)),
            "Предложений": len([s for s in sentences if s.strip()]),
            "Параграфов": len([p for p in paragraphs if p.strip()]),
        }
        
        if words:
            stats["Средняя длина слова"] = round(sum(len(w) for w in words) / len(words), 1)
        if sentences:
            stats["Средняя длина предложения"] = round(len(words) / len([s for s in sentences if s.strip()]), 1)
        
        word_counts = Counter(words)
        top_words = word_counts.most_common(10)
        
        return stats, top_words


def main():
    root = tk.Tk()
    app = SmartTextSearcherGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()