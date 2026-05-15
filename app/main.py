import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import psycopg2
from psycopg2 import sql

# === НАСТРОЙКИ ПОДКЛЮЧЕНИЯ ===
DB_NAME = "railwaystation"
DB_USER = "postgres"
DB_PASSWORD = "admin"
DB_HOST = "localhost"
DB_PORT = "5432"

def get_connection():
    try:
        return psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
            host=DB_HOST, port=DB_PORT
        )
    except Exception as e:
        messagebox.showerror("Ошибка подключения", f"Не удалось подключиться к БД:\n{e}")
        return None

# Метаданные таблиц
TABLES = {
    "train_types": {"pk": "train_type_id", "cols": ["train_type_id", "type_name"]},
    "positions":   {"pk": "position_id",   "cols": ["position_id", "position_name"]},
    "crews":       {"pk": "crew_id",       "cols": ["crew_id", "crew_name"]},
    "stations": {"pk": "station_id", "cols": ["station_id", "name", "inn", "address", "staff_count"]},
    "trains":      {"pk": "train_id",      "cols": ["train_id", "station_id", "train_type_id", "name"]},
    "staff":       {"pk": "inn",           "cols": ["inn", "station_id", "full_name", "position_id", "crew_id"]},
    "routes": {"pk": "route_id",
           "cols": ["route_id", "owner_station_id", "train_id",
                    "departure_station_id", "arrival_station_id",
                    "departure_time", "arrival_time", "crew_id"]},
    "route_data":  {"pk": "route_id, stop_number",
                    "cols": ["route_id", "stop_number", "station_id", "arrival_time", "departure_time"]}
}

# ==================== УНИВЕРСАЛЬНАЯ ВКЛАДКА ДЛЯ ТАБЛИЦ ====================
class GenericTableTab(ttk.Frame):
    def __init__(self, parent, table_name):
        super().__init__(parent)
        self.table_name = table_name
        self.meta = TABLES[table_name]

        # --- Верхняя панель управления (фильтр, сортировка) ---
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(top_frame, text="Колонка:").pack(side=tk.LEFT, padx=2)
        self.filter_col = ttk.Combobox(top_frame, values=self.meta["cols"],
                                       state="readonly", width=15)
        if self.meta["cols"]:
            self.filter_col.current(0)
        self.filter_col.pack(side=tk.LEFT, padx=2)

        ttk.Label(top_frame, text="Значение (поиск):").pack(side=tk.LEFT, padx=2)
        self.filter_val = ttk.Entry(top_frame, width=15)
        self.filter_val.pack(side=tk.LEFT, padx=2)

        ttk.Button(top_frame, text="Поиск", command=self.load_data).pack(side=tk.LEFT, padx=5)

        ttk.Label(top_frame, text="Сортировка:").pack(side=tk.LEFT, padx=2)
        self.sort_col = ttk.Combobox(top_frame, values=self.meta["cols"],
                                     state="readonly", width=15)
        if self.meta["cols"]:
            self.sort_col.current(0)
        self.sort_col.pack(side=tk.LEFT, padx=2)

        self.sort_order = tk.StringVar(value="ASC")
        ttk.Radiobutton(top_frame, text="По возр.", variable=self.sort_order,
                        value="ASC").pack(side=tk.LEFT)
        ttk.Radiobutton(top_frame, text="По убыв.", variable=self.sort_order,
                        value="DESC").pack(side=tk.LEFT)
        ttk.Button(top_frame, text="Сортировать", command=self.load_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Сброс", command=self.reset_filters).pack(side=tk.LEFT, padx=5)

        # --- Таблица (Treeview) ---
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.tree = ttk.Treeview(tree_frame, columns=self.meta["cols"], show="headings")
        for col in self.meta["cols"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # --- Нижняя панель (CRUD) ---
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(btn_frame, text="Добавить", command=self.add_record).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Изменить", command=self.edit_record).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Удалить", command=self.delete_record).pack(side=tk.LEFT, padx=5)

        self.load_data()

    def reset_filters(self):
        self.filter_val.delete(0, tk.END)
        self.load_data()

    def load_data(self):
        """Загрузка данных с учётом фильтра и сортировки."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        conn = get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            query = sql.SQL("SELECT * FROM {}").format(sql.Identifier(self.table_name))
            params = []

            # Фильтр (ILIKE по текстовому представлению)
            if self.filter_val.get() and self.filter_col.get():
                query += sql.SQL(" WHERE CAST({} AS TEXT) ILIKE %s").format(
                    sql.Identifier(self.filter_col.get())
                )
                params.append(f"%{self.filter_val.get()}%")

            # Сортировка
            if self.sort_col.get():
                query += sql.SQL(" ORDER BY {} {}").format(
                    sql.Identifier(self.sort_col.get()),
                    sql.SQL(self.sort_order.get())
                )

            cursor.execute(query, tuple(params))
            for row in cursor.fetchall():
                self.tree.insert("", tk.END, values=row)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
        finally:
            conn.close()

    def get_selected_values(self):
        """Возвращает значения выделенной строки."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите запись!")
            return None
        return self.tree.item(selected[0])['values']

    def delete_record(self):
        values = self.get_selected_values()
        if values is None:
            return
        if not messagebox.askyesno("Подтверждение", "Удалить запись?"):
            return

        conn = get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            pk_cols = [c.strip() for c in self.meta["pk"].split(",")]
            pk_values = [str(v) for v in values[:len(pk_cols)]]

            where_clause = sql.SQL(" AND ").join(
                sql.SQL("{} = %s").format(sql.Identifier(col)) for col in pk_cols
            )
            query = sql.SQL("DELETE FROM {} WHERE ").format(
                sql.Identifier(self.table_name)
            ) + where_clause

            cursor.execute(query, tuple(pk_values))
            conn.commit()
            self.load_data()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Ошибка", str(e))
        finally:
            conn.close()

    def add_record(self):
        self._open_form("Добавить", None)

    def edit_record(self):
        values = self.get_selected_values()
        if values is None:
            return
        self._open_form("Изменить", values)

    def _open_form(self, title, values):
        top = tk.Toplevel(self)
        top.title(title)
        entries = {}

        for i, col in enumerate(self.meta["cols"]):
            ttk.Label(top, text=col).grid(row=i, column=0, padx=5, pady=5, sticky="e")
            ent = ttk.Entry(top, width=30)
            if values:
                ent.insert(0, str(values[i]))
                # Поля первичного ключа только для чтения при редактировании
                if col in [c.strip() for c in self.meta["pk"].split(",")]:
                    ent.configure(state="readonly")
            ent.grid(row=i, column=1, padx=5, pady=5)
            entries[col] = ent

        def save():
            conn = get_connection()
            if not conn:
                return
            try:
                cursor = conn.cursor()
                data = {k: v.get() for k, v in entries.items() if v.get() != ""}
                if not data:
                    return

                if title == "Добавить":
                    cols = sql.SQL(", ").join(map(sql.Identifier, data.keys()))
                    vals = sql.SQL(", ").join(sql.Placeholder() * len(data))
                    query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                        sql.Identifier(self.table_name), cols, vals
                    )
                    cursor.execute(query, tuple(data.values()))
                else:
                    pk_cols = [c.strip() for c in self.meta["pk"].split(",")]
                    old_pk = [str(v) for v in values[:len(pk_cols)]]

                    # Обновляемые поля (все, кроме PK)
                    set_items = [(k, v) for k, v in data.items() if k not in pk_cols]
                    set_clause = sql.SQL(", ").join(
                        sql.SQL("{} = %s").format(sql.Identifier(k)) for k, _ in set_items
                    )
                    where_clause = sql.SQL(" AND ").join(
                        sql.SQL("{} = %s").format(sql.Identifier(col)) for col in pk_cols
                    )
                    query = sql.SQL("UPDATE {} SET ").format(
                        sql.Identifier(self.table_name)
                    ) + set_clause + sql.SQL(" WHERE ") + where_clause

                    params = [v for _, v in set_items] + list(old_pk)
                    cursor.execute(query, tuple(params))

                conn.commit()
                self.load_data()
                top.destroy()
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Ошибка БД", str(e))
            finally:
                conn.close()

        ttk.Button(top, text="Сохранить", command=save).grid(
            row=len(self.meta["cols"]), columnspan=2, pady=10
        )

# ==================== ФОРМА 1:М (Вокзал → Поезда) ====================
class Form1MTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.trains = []

        left_frame = ttk.LabelFrame(self, text="1. Данные вокзала (1)")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(left_frame, text="Название вокзала:").pack(pady=2)
        self.st_name = ttk.Entry(left_frame)
        self.st_name.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(left_frame, text="ИНН:").pack(pady=2)
        self.st_inn = ttk.Entry(left_frame)
        self.st_inn.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(left_frame, text="Адрес:").pack(pady=2)
        self.st_address = ttk.Entry(left_frame)
        self.st_address.pack(fill=tk.X, padx=5, pady=2)

        right_frame = ttk.LabelFrame(self, text="2. Поезда этого вокзала (M)")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.train_list = tk.Listbox(right_frame, height=10)
        self.train_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="Добавить поезд в список",
                   command=self.add_train_temp).pack(side=tk.LEFT, padx=5)

        ttk.Button(self, text="СОВЕРШИТЬ ТРАНЗАКЦИЮ (Сохранить в БД)",
                   command=self.save_transaction).pack(side=tk.BOTTOM, pady=20)

    def add_train_temp(self):
        t_type = simpledialog.askinteger("Ввод", "ID типа поезда (train_type_id):")
        if not t_type:
            return
        t_name = simpledialog.askstring("Ввод", "Название поезда:")
        if not t_name:
            return
        self.trains.append({"type_id": t_type, "name": t_name})
        self.train_list.insert(tk.END, f"Тип: {t_type} | Название: {t_name}")

    def save_transaction(self):
        if not self.st_name.get() or not self.trains:
            messagebox.showwarning("Внимание", "Заполните вокзал и добавьте хотя бы 1 поезд.")
            return
        conn = get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO stations (name, inn, address) VALUES (%s, %s, %s) RETURNING station_id",
                (self.st_name.get(), self.st_inn.get(), self.st_address.get())
            )
            station_id = cursor.fetchone()[0]

            for t in self.trains:
                cursor.execute(
                    "INSERT INTO trains (station_id, train_type_id, name) VALUES (%s, %s, %s)",
                    (station_id, t["type_id"], t["name"])
                )
            conn.commit()
            messagebox.showinfo("Успех", "Вокзал и поезда успешно добавлены!")
            self.trains.clear()
            self.train_list.delete(0, tk.END)
            self.st_name.delete(0, tk.END)
            self.st_inn.delete(0, tk.END)
            self.st_address.delete(0, tk.END)
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Ошибка транзакции", str(e))
        finally:
            conn.close()

# ==================== ВКЛАДКА ОТЧЁТОВ ====================
class ReportsTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        controls = ttk.Frame(self)
        controls.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(controls, text="Фильтр по названию вокзала:").pack(side=tk.LEFT)
        self.filter_entry = ttk.Entry(controls)
        self.filter_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(controls, text="Сортировка:").pack(side=tk.LEFT)
        self.sort_order = ttk.Combobox(controls, values=["ASC", "DESC"],
                                       state="readonly", width=5)
        self.sort_order.current(1)
        self.sort_order.pack(side=tk.LEFT, padx=5)

        ttk.Button(controls, text="Отчёт 1: Кол-во поездов на вокзалах",
                   command=self.report_1).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls, text="Отчёт 2: Персонал по должностям",
                   command=self.report_2).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls, text="Отчёт 3: Статистика маршрутов",
                   command=self.report_3).pack(side=tk.LEFT, padx=5)

        self.tree = ttk.Treeview(self, show="headings")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def execute_report(self, base_query, columns):
        """Выполняет запрос с фильтром и сортировкой, выводит результат в Treeview."""
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = columns
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)

        conn = get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            filter_val = f"%{self.filter_entry.get()}%"
            sort_dir = self.sort_order.get()

            # Безопасное формирование запроса с ORDER BY (допустимые значения: ASC, DESC)
            query = sql.SQL(base_query).format(sort=sql.SQL(sort_dir))
            cursor.execute(query, (filter_val,))
            for row in cursor.fetchall():
                self.tree.insert("", tk.END, values=row)
        except Exception as e:
            messagebox.showerror("Ошибка отчёта", str(e))
        finally:
            conn.close()

    def report_1(self):
        q = """
            SELECT s.name AS "Вокзал", COUNT(t.train_id) AS "Всего поездов"
            FROM stations s
            LEFT JOIN trains t ON s.station_id = t.station_id
            WHERE s.name ILIKE %s
            GROUP BY s.name
            ORDER BY COUNT(t.train_id) {sort}
        """
        self.execute_report(q, ["Вокзал", "Всего поездов"])

    def report_2(self):
        q = """
            SELECT s.name AS "Вокзал", p.position_name AS "Должность",
                   COUNT(st.inn) AS "Кол-во сотрудников"
            FROM stations s
            JOIN staff st ON s.station_id = st.station_id
            JOIN positions p ON st.position_id = p.position_id
            WHERE s.name ILIKE %s
            GROUP BY s.name, p.position_name
            ORDER BY COUNT(st.inn) {sort}
        """
        self.execute_report(q, ["Вокзал", "Должность", "Кол-во сотрудников"])

    def report_3(self):
        q = """
            SELECT s.name AS "Станция отправления",
                   COUNT(r.route_id) AS "Кол-во маршрутов"
            FROM routes r
            JOIN stations s ON r.departure_station_id = s.station_id
            WHERE s.name ILIKE %s
            GROUP BY s.name
            ORDER BY COUNT(r.route_id) {sort}
        """
        self.execute_report(q, ["Станция отправления", "Кол-во маршрутов"])

# ==================== ГЛАВНОЕ ОКНО ====================
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Курсовая работа: Автоматизация Вокзала")
    root.geometry("1000x600")

    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True)

    for table_name in TABLES.keys():
        tab = GenericTableTab(notebook, table_name)
        notebook.add(tab, text=f"Таблица: {table_name}")

    notebook.add(Form1MTab(notebook), text="Форма 1:М (Вокзал+Поезда)")
    notebook.add(ReportsTab(notebook), text="Отчёты")

    root.mainloop()