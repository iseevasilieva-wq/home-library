import os
import sqlite3
import pandas as pd
import streamlit as st

# Настройка страницы
st.set_page_config(
    page_title="Моя Личная Библиотека", page_icon="📚", layout="centered"
)

# Папка для хранения электронных книг
BOOKS_DIR = "uploaded_books"
os.makedirs(BOOKS_DIR, exist_ok=True)


# Подключение к БД
def get_connection():
    return sqlite3.connect("library_v2.db", check_same_thread=False)


# Инициализация структуры таблицы
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

st.title("📚 Личная библиотека")

# Боковое меню
menu = st.sidebar.radio(
    "Навигация",
    ["📖 Каталог книг", "➕ Добавить книгу", "✏️ Редактировать / Удалить"],
)

conn = get_connection()

# ==========================================
# 1. КАТАЛОГ КНИГ (Поиск, Сортировка, Просмотр)
# ==========================================
if menu == "📖 Каталог книг":
    st.header("Каталог книг")

    # Панель поиска и фильтров
    col1, col2 = st.columns([2, 1])
    with col1:
        search_query = st.text_input(
            "🔍 Поиск", placeholder="Название, автор или цитата..."
        )
    with col2:
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
        ["Названию (А-Я)", "Году издания (снач. новые)", "Году издания (снач. старые)"],
    )

    # Формируем запрос
    query = "SELECT * FROM books"
    df = pd.read_sql_query(query, conn)

    if not df.empty:
        # Фильтрация по категории
        if category_filter != "Все":
            df = df[df["category"] == category_filter]

        # Фильтрация по поиску
        if search_query:
            df = df[
                df["title"].str.contains(search_query, case=False, na=False)
                | df["author"].str.contains(search_query, case=False, na=False)
                | df["notes"].str.contains(search_query, case=False, na=False)
            ]

        # Сортировка
        if sort_by == "Названию (А-Я)":
            df = df.sort_values(by="title")
        elif sort_by == "Году издания (снач. новые)":
            df = df.sort_values(by="year", ascending=False)
        elif sort_by == "Году издания (снач. старые)":
            df = df.sort_values(by="year", ascending=True)

        st.caption(f"Найдено книг: {len(df)}")

        # Вывод книг в виде карточек
        for idx, row in df.iterrows():
            with st.expander(
                f"📖 {row['title']} — {row['author']} ({row['year'] or 'г.н. неизвестен'})"
            ):
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"**Категория:** {row['category']}")
                    st.write(f"**Статус:** {row['status']}")
                with c2:
                    st.write(f"**Местонахождение:** {row['location']}")

                if row["notes"]:
                    st.info(f"**Заметки / Цитаты:**\n\n{row['notes']}")

                # Скачивание файла, если это электронная книга
                if row["file_path"] and os.path.exists(row["file_path"]):
                    with open(row["file_path"], "rb") as f:
                        st.download_button(
                            label="📥 Скачать электронную книгу",
                            data=f,
                            file_name=os.path.basename(row["file_path"]),
                            mime="application/octet-stream",
                            key=f"dl_{row['id']}",
                        )
    else:
        st.info("В базе пока нет книг.")

# ==========================================
# 2. ДОБАВЛЕНИЕ КНИГИ
# ==========================================
elif menu == "➕ Добавить книгу":
    st.header("Добавить новую книгу в базу")

    with st.form("add_book_form", clear_on_submit=True):
        title = st.text_input("1.1. Название книги*")
        author = st.text_input("1.2. Автор*")

        col1, col2 = st.columns(2)
        with col1:
            year = st.number_input(
                "1.3. Год издания", min_value=0, max_value=2030, value=2024
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
        with col2:
            location = st.text_input(
                "1.4. Местонахождение",
                placeholder="например: Шкаф в спальне, 2 полка",
            )
            status = st.selectbox(
                "2. Статус чтения",
                [
                    "В очереди",
                    "В процессе чтения",
                    "Прочитано",
                    "Отдано почитать",
                ],
            )

        notes = st.text_area(
            "1.5. Заметки, личные мысли, цитаты",
            placeholder="Запишите интересные цитаты или впечатления...",
        )

        # Загрузка электронного файла
        uploaded_file = st.file_uploader(
            "3. Загрузить файл книги (для эл. книг)",
            type=["pdf", "epub", "fb2", "txt"],
        )

        submit = st.form_submit_button("Сохранить книгу")

        if submit:
            if title and author:
                file_path = None
                if uploaded_file is not None:
                    # Сохраняем файл локально
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
                        year,
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
                st.error("Название и автор обязательны для заполнения.")

# ==========================================
# 3. РЕДАКТИРОВАНИЕ И УДАЛЕНИЕ
# ==========================================
elif menu == "✏️ Редактировать / Удалить":
    st.header("Управление записями")

    df = pd.read_sql_query("SELECT id, title, author FROM books", conn)

    if not df.empty:
        book_to_edit = st.selectbox(
            "Выберите книгу для редактирования / удаления",
            options=df["id"].tolist(),
            format_func=lambda x: f"{df[df['id'] == x]['title'].values[0]} — {df[df['id'] == x]['author'].values[0]}",
        )

        # Извлечем данные книги
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM books WHERE id = ?", (book_to_edit,))
        book_data = cursor.fetchone()

        st.subheader("Изменить данные:")
        new_status = st.selectbox(
            "Изменить статус",
            ["В очереди", "В процессе чтения", "Прочитано", "Отдано почитать"],
            index=[
                "В очереди",
                "В процессе чтения",
                "Прочитано",
                "Отдано почитать",
            ].index(book_data[6]),
        )
        new_location = st.text_input("Изменить местонахождение", value=book_data[5])
        new_notes = st.text_area("Обновить заметки", value=book_data[7] or "")

        col_save, col_del = st.columns(2)
        with col_save:
            if st.button("💾 Сохранить изменения"):
                cursor.execute(
                    "UPDATE books SET status=?, location=?, notes=? WHERE id=?",
                    (new_status, new_location, new_notes, book_to_edit),
                )
                conn.commit()
                st.success("Изменения сохранены!")
                st.rerun()

        with col_del:
            if st.button("❌ Удалить книгу полностью"):
                cursor.execute("DELETE FROM books WHERE id=?", (book_to_edit,))
                conn.commit()
                st.success("Книга удалена!")
                st.rerun()
    else:
        st.info("База данных пуста.")