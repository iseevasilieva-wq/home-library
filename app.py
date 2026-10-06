import os
import sqlite3
import pandas as pd
import streamlit as st

# Настройка страницы
st.set_page_config(
    page_title="Моя Личная Библиотека",
    page_icon="📚",
    layout="centered",
    initial_sidebar_state="expanded",
)

# Папки для файлов и обложек
BOOKS_DIR = "uploaded_books"
COVERS_DIR = "uploaded_covers"
os.makedirs(BOOKS_DIR, exist_ok=True)
os.makedirs(COVERS_DIR, exist_ok=True)


# Подключение к БД
def get_connection():
    return sqlite3.connect("library_v2.db", check_same_thread=False)


# Инициализация и авто-обновление структуры БД
def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            category TEXT,
            location TEXT,
            status TEXT,
            notes TEXT,
            file_path TEXT
        )
    """)

    # Безопасное добавление колонки cover_path, если её ещё нет
    cursor.execute("PRAGMA table_info(books)")
    columns = [col[1] for col in cursor.fetchall()]
    if "cover_path" not in columns:
        cursor.execute("ALTER TABLE books ADD COLUMN cover_path TEXT")

    conn.commit()


init_db()

# Список категорий
CATEGORIES = [
    "Художественная",
    "Детская литература",
    "Искусство",
    "Словари",
    "Фотокниги",
    "Нон-фикшн",
    "Фантастика",
    "Учеба / Бизнес",
    "Другое",
]

# Список статусов
STATUSES = [
    "В очередь",
    "В процессе чтения",
    "Прочитано",
    "Отдано почитать",
    "Аренда",
]

# --- ЗАЩИТА ПАРОЛЕМ ---
PASSWORD = "1234"  # Измени пароль при необходимости

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 Вход в библиотеку")
    user_pass = st.text_input("Введите пароль для доступа:", type="password")
    if st.button("Войти"):
        if user_pass == PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Неверный пароль!")
    st.stop()
# ----------------------

st.title("📚 Личная библиотека")

# Боковое меню
menu = st.sidebar.radio(
    "Навигация",
    ["📖 Каталог книг", "➕ Добавить книгу", "✏️ Редактировать / Удалить"],
)

conn = get_connection()

# ==========================================
# 1. КАТАЛОГ КНИГ
# ==========================================
if menu == "📖 Каталог книг":
    st.header("Каталог книг")

    search_query = st.text_input(
        "🔍 Поиск", placeholder="Название, автор или цитата..."
    )

    category_filter = st.selectbox(
        "Категория",
        ["Все"] + CATEGORIES,
    )

    sort_by = st.selectbox(
        "Сортировать по",
        ["Названию (А-Я)", "Году (сначала новые)", "Году (сначала старые)"],
    )

    df = pd.read_sql_query("SELECT * FROM books", conn)

    if not df.empty:
        if category_filter != "Все":
            df = df[df["category"] == category_filter]

        if search_query:
            df = df[
                df["title"].str.contains(search_query, case=False, na=False)
                | df["author"].str.contains(search_query, case=False, na=False)
                | df["notes"].str.contains(search_query, case=False, na=False)
            ]

        if sort_by == "Названию (А-Я)":
            df = df.sort_values(by="title")
        elif sort_by == "Году (сначала новые)":
            df = df.sort_values(by="year", ascending=False)
        elif sort_by == "Году (сначала старые)":
            df = df.sort_values(by="year", ascending=True)

        st.caption(f"Найдено книг: {len(df)}")

        for idx, row in df.iterrows():
            year_str = f"({row['year']} г.)" if row["year"] else ""
            with st.expander(f"📖 {row['title']} — {row['author']} {year_str}"):
                # Отображение обложки, если она загружена и файл существует
                if (
                    "cover_path" in row
                    and isinstance(row["cover_path"], str)
                    and row["cover_path"]
                    and os.path.exists(row["cover_path"])
                ):
                    st.image(row["cover_path"], width=180)

                st.write(f"**Категория:** {row['category']}")
                st.write(f"**Статус:** {row['status']}")
                st.write(f"**Местонахождение:** {row['location']}")

                if row["notes"]:
                    st.info(f"**Заметки / Цитаты:**\n\n{row['notes']}")

                # Исправленная безопасная проверка пути к файлу книги
                if (
                    isinstance(row["file_path"], str)
                    and row["file_path"]
                    and os.path.exists(row["file_path"])
                ):
                    try:
                        with open(row["file_path"], "rb") as f:
                            st.download_button(
                                label="📥 Скачать электронную книгу",
                                data=f.read(),
                                file_name=os.path.basename(row["file_path"]),
                                mime="application/octet-stream",
                                key=f"dl_{row['id']}",
                            )
                    except Exception:
                        st.warning("Файл книги недоступен.")
    else:
        st.info("В базе пока нет книг.")

# ==========================================
# 2. ДОБАВЛЕНИЕ КНИГИ
# ==========================================
elif menu == "➕ Добавить книгу":
    st.header("Добавить книгу")

    with st.form("add_book_form", clear_on_submit=True):
        title = st.text_input("Название книги*")
        author = st.text_input("Автор*")
        year = st.number_input(
            "Год издания", min_value=0, max_value=2030, value=2024, step=1
        )

        category = st.selectbox("Категория", CATEGORIES)

        location = st.text_input(
            "Местонахождение", placeholder="Например: Шкаф в гостиной, 2 полка"
        )

        status = st.selectbox("Статус", STATUSES)

        # Расширенное поле заметок (height=200)
        notes = st.text_area(
            "Заметки / Цитаты / Комментарии",
            placeholder="Внесите личные мысли, впечатления или цитаты...",
            height=200,
        )

        # Загрузка обложки
        uploaded_cover = st.file_uploader(
            "🖼️ Обложка книги (JPG, PNG, WEBP)",
            type=["jpg", "jpeg", "png", "webp"],
        )

        # Загрузка файла книги
        uploaded_file = st.file_uploader(
            "📄 Электронная книга (PDF, EPUB, FB2)",
            type=["pdf", "epub", "fb2", "txt"],
        )

        submit = st.form_submit_button("Сохранить книгу")

        if submit:
            if title and author:
                file_path = None
                if uploaded_file is not None:
                    file_path = os.path.join(BOOKS_DIR, uploaded_file.name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                cover_path = None
                if uploaded_cover is not None:
                    cover_path = os.path.join(COVERS_DIR, uploaded_cover.name)
                    with open(cover_path, "wb") as f:
                        f.write(uploaded_cover.getbuffer())

                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO books (title, author, year, category, location, status, notes, file_path, cover_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        title,
                        author,
                        int(year),
                        category,
                        location,
                        status,
                        notes,
                        file_path,
                        cover_path,
                    ),
                )
                conn.commit()
                st.success(f"Книга «{title}» успешно добавлена!")
            else:
                st.error("Пожалуйста, заполните Название и Автора.")

# ==========================================
# 3. РЕДАКТИРОВАНИЕ И УДАЛЕНИЕ
# ==========================================
elif menu == "✏️️ Редактировать / Удалить":
    st.header("Управление записями")

    df = pd.read_sql_query("SELECT id, title, author FROM books", conn)

    if not df.empty:
        book_to_edit = st.selectbox(
            "Выберите книгу для редактирования",
            options=df["id"].tolist(),
            format_func=lambda x: f"{df[df['id'] == x]['title'].values[0]} — {df[df['id'] == x]['author'].values[0]}",
        )

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM books WHERE id = ?", (book_to_edit,))
        book_data = cursor.fetchone()

        current_status = (
            book_data[6] if book_data[6] in STATUSES else STATUSES[0]
        )

        new_status = st.selectbox(
            "Статус",
            STATUSES,
            index=STATUSES.index(current_status),
        )
        new_location = st.text_input("Местонахождение", value=book_data[5] or "")
        new_notes = st.text_area(
            "Заметки", value=book_data[7] or "", height=200
        )

        if st.button("💾 Сохранить изменения"):
            cursor.execute(
                "UPDATE books SET status=?, location=?, notes=? WHERE id=?",
                (new_status, new_location, new_notes, book_to_edit),
            )
            conn.commit()
            st.success("Сохранено!")
            st.rerun()

        if st.button("❌ Удалить книгу"):
            cursor.execute("DELETE FROM books WHERE id=?", (book_to_edit,))
            conn.commit()
            st.success("Удалено!")
            st.rerun()
    else:
        st.info("База пуста.")