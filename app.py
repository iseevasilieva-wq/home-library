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

# Папка для электронных книг
BOOKS_DIR = "uploaded_books"
os.makedirs(BOOKS_DIR, exist_ok=True)


# Подключение к БД
def get_connection():
    return sqlite3.connect("library_v2.db", check_same_thread=False)


# Инициализация таблицы
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
    conn.commit()


init_db()

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
        [
            "Все",
            "Художественная",
            "Нон-фикшн",
            "Детектив",
            "Фантастика",
            "Психология",
            "Учеба / Бизнес",
            "Другое",
        ],
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
                st.write(f"**Категория:** {row['category']}")
                st.write(f"**Статус:** {row['status']}")
                st.write(f"**Местонахождение:** {row['location']}")

                if row["notes"]:
                    st.info(f"**Заметки / Цитаты:**\n\n{row['notes']}")

                if row["file_path"] and os.path.exists(row["file_path"]):
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

        category = st.selectbox(
            "Категория",
            [
                "Художественная",
                "Нон-фикшн",
                "Детектив",
                "Фантастика",
                "Психология",
                "Учеба / Бизнес",
                "Другое",
            ],
        )

        location = st.text_input(
            "Местонахождение", placeholder="Например: Шкаф в гостиной, 2 полка"
        )

        status = st.selectbox(
            "Статус",
            ["Дома на полке", "В процессе чтения", "Прочитано", "Отдано почитать"],
        )

        notes = st.text_area(
            "Заметки / Цитаты / Комментарии",
            placeholder="Внесите личные мысли или цитаты...",
        )

        uploaded_file = st.file_uploader(
            "Электронная книга (PDF, EPUB, FB2)",
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

                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO books (title, author, year, category, location, status, notes, file_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
                    ),
                )
                conn.commit()
                st.success(f"Книга «{title}» успешно добавлена!")
            else:
                st.error("Пожалуйста, заполните Название и Автора.")

# ==========================================
# 3. РЕДАКТИРОВАНИЕ И УДАЛЕНИЕ
# ==========================================
elif menu == "✏️ Редактировать / Удалить":
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

        new_status = st.selectbox(
            "Статус",
            ["Дома на полке", "В процессе чтения", "Прочитано", "Отдано почитать"],
            index=[
                "Дома на полке",
                "В процессе чтения",
                "Прочитано",
                "Отдано почитать",
            ].index(book_data[6])
            if book_data[6]
            in [
                "Дома на полке",
                "В процессе чтения",
                "Прочитано",
                "Отдано почитать",
            ]
            else 0,
        )
        new_location = st.text_input("Местонахождение", value=book_data[5] or "")
        new_notes = st.text_area("Заметки", value=book_data[7] or "")

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