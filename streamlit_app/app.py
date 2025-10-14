# app.py — Filtros: Título, Año (exacto), Director (uno), Actor (uno), Puntaje (EXACTO)

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Best Movies of IMDb", page_icon="🎬", layout="wide")
st.title("Mejores Peliculas - Filtro")

# ── Conexión a MySQL (lee credenciales desde .streamlit/secrets.toml)
cfg = st.secrets.get("mysql", {})
user = cfg.get("user", "root")
password = cfg.get("password", "")
host = cfg.get("host", "localhost")
port = int(cfg.get("port", 3306))
database = cfg.get("database", "best_movies")

engine = create_engine(
    f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4",
    pool_pre_ping=True,
)

# Aumentar GROUP_CONCAT por si luego lo necesitás (no afecta esta versión)
with engine.begin() as con:
    con.execute(text("SET SESSION group_concat_max_len = 32768"))

# ── Cargar opciones de Director y Actor para los select (una sola elección)
# ── Cargar opciones de Director, Actor y Genero (una sola elección)
def load_options():
    with engine.begin() as con:
        directors = pd.read_sql(text("SELECT id, dir_name AS name FROM director ORDER BY dir_name"), con)
        actors    = pd.read_sql(text("SELECT id, act_name AS name FROM actor ORDER BY act_name"), con)
        genres    = pd.read_sql(text("SELECT id, gen_name AS name FROM genre ORDER BY gen_name"), con)
    return directors, actors, genres

directors_df, actors_df, genres_df = load_options()


# ── Filtros: título, año exacto, director único, actor único, puntaje EXACTO
q = st.text_input("Buscar por título (contiene)", placeholder="En Inglés, ejemplo: Inception", key="f_q")

year_str = st.text_input("Año", placeholder="2001", key="f_year")
year_val = None
if year_str.strip():
    if year_str.strip().isdigit():
        year_val = int(year_str.strip())
    else:
        st.warning("El año debe ser un número (por ejemplo 2001)")

# Director (uno solo)
director_opts = [("", "— Cualquiera —")] + list(directors_df.itertuples(index=False, name=None))
director_choice = st.selectbox(
    "Director",
    options=director_opts,
    index=0,
    key="f_dir",
    format_func=lambda x: x[1] if isinstance(x, tuple) and x else str(x),
)
director_id_val = None
if isinstance(director_choice, tuple) and director_choice and director_choice[0] != "":
    director_id_val = int(director_choice[0])

# Actor (uno solo)
actor_opts = [("", "— Cualquiera —")] + list(actors_df.itertuples(index=False, name=None))
actor_choice = st.selectbox(
    "Actor",
    options=actor_opts,
    index=0,
    key="f_actor",
    format_func=lambda x: x[1] if isinstance(x, tuple) and x else str(x),
)
actor_id_val = None
if isinstance(actor_choice, tuple) and actor_choice and actor_choice[0] != "":
    actor_id_val = int(actor_choice[0])

# Género (uno solo)
genre_opts = [("", "— Cualquiera —")] + list(genres_df.itertuples(index=False, name=None))
genre_choice = st.selectbox(
    "Género",
    options=genre_opts,
    index=0,
    key="f_genre",
    format_func=lambda x: x[1] if isinstance(x, tuple) and x else str(x),
)
genre_id_val = None
if isinstance(genre_choice, tuple) and genre_choice and genre_choice[0] != "":
    genre_id_val = int(genre_choice[0])

# Puntaje EXACTO (opcional)
score_str = st.text_input("Puntaje (exacto)", placeholder="8.6", key="f_score")
score_exact = None
if score_str.strip():
    try:
        score_exact = float(score_str.strip())
    except ValueError:
        st.warning("El puntaje debe ser numérico (ej: 8.6)")
        score_exact = None

# ── Controles de orden
orden_campo = st.selectbox(
    "Ordenar por",
    options=["Puntaje", "Título", "Año", "Duración"],
    index=0,
    key="f_sort_field",
)
orden_dir = st.radio(
    "Dirección",
    options=["Descendente", "Ascendente"],
    horizontal=True,
    index=0,
    key="f_sort_dir",
)


# --- Botón para limpiar filtros (callback seguro)
def clear_filters():
    st.session_state.update({
        "f_q": "",
        "f_year": "",
        "f_dir": director_opts[0],     # ("", "— Cualquiera —")
        "f_actor": actor_opts[0],      # ("", "— Cualquiera —")
        "f_genre": genre_opts[0],      # ("", "— Cualquiera —")
        "f_score": "",
        "f_sort_field": "Puntaje",
        "f_sort_dir": "Descendente",
    })

st.button("🧹 Limpiar filtros", on_click=clear_filters)

def build_order_by(campo: str, direccion: str) -> str:
    # Mapa seguro de nombres “amigables” -> columnas reales
    columnas = {
        "Puntaje": "m.score",
        "Título": "m.title",
        "Año": "m.mov_year",
        "Duración": "m.duration",
    }
    col = columnas.get(campo, "m.score")
    dir_sql = "DESC" if direccion == "Descendente" else "ASC"

    # Desempate estable por ranking (m.id asc)
    # COALESCE para que NULLs en duration/año no “ensucien”
    if col in ("m.duration", "m.mov_year"):
        return f"ORDER BY COALESCE({col}, 0) {dir_sql}, m.id ASC"
    elif col == "m.title":
        return f"ORDER BY {col} {dir_sql}, m.id ASC"
    else:  # m.score
        return f"ORDER BY {col} {dir_sql}, m.id ASC"

############
def build_where(q_val: str | None, year_exact: int | None, did: int | None, gid: int | None, aid: int | None, s_exact: float | None):
    clauses = ["WHERE 1=1"]
    params = {}

    if q_val and q_val.strip():
        clauses.append("AND m.title LIKE :q")
        params["q"] = f"%{q_val.strip()}%"

    if year_exact is not None:
        clauses.append("AND m.mov_year = :y")
        params["y"] = int(year_exact)

    if did is not None:
        clauses.append("AND m.director_id = :did")
        params["did"] = int(did)

    if gid is not None:
        # Género único
        clauses.append("AND EXISTS (SELECT 1 FROM movie_genre mg WHERE mg.movie_id = m.id AND mg.genre_id = :gid)")
        params["gid"] = int(gid)

    if aid is not None:
        # Actor único
        clauses.append("AND EXISTS (SELECT 1 FROM movie_actor ma WHERE ma.movie_id = m.id AND ma.actor_id = :aid)")
        params["aid"] = int(aid)

    if s_exact is not None:
        # Puntaje EXACTO
        clauses.append("AND m.score = :s")
        params["s"] = float(s_exact)

    return "\n".join(clauses), params


# ── Tabla principal con filtros
with st.expander("The Best 250 Movies - Table", expanded=True):
    try:
        where_sql, params = build_where(q, year_val, director_id_val, genre_id_val, actor_id_val, score_exact)
        # Determinar orden dinámico según selección
        order_by_sql = build_order_by(orden_campo, orden_dir)

        with engine.begin() as con:
            # Conteo robusto (DISTINCT por si se mete algún join)
            cnt_sql = f"SELECT COUNT(DISTINCT m.id) AS c FROM movie m {where_sql}"
            total = int(pd.read_sql(text(cnt_sql), con, params=params).iloc[0]["c"])
            st.caption(f"Coincidencias: {total}")

            # Listado (incluye Director y Actores)
            sql = f"""
        SELECT
            m.id        AS Pos,
            m.title     AS Pelicula,
            m.mov_year  AS Año,
            m.score     AS Puntaje,
            m.duration  AS Duracion,
            d.dir_name  AS Director,
            GROUP_CONCAT(DISTINCT g.gen_name ORDER BY g.gen_name SEPARATOR ', ') AS Generos,
            GROUP_CONCAT(DISTINCT a.act_name ORDER BY a.act_name SEPARATOR ', ') AS Actores
        FROM movie AS m
        JOIN director AS d           ON d.id = m.director_id
        LEFT JOIN movie_actor  AS ma ON ma.movie_id = m.id
        LEFT JOIN actor        AS a  ON a.id = ma.actor_id
        LEFT JOIN movie_genre  AS mg ON mg.movie_id = m.id
        LEFT JOIN genre        AS g  ON g.id = mg.genre_id
        {where_sql}
        GROUP BY m.id, m.title, m.mov_year, m.score, m.duration, d.dir_name
        {order_by_sql}
        LIMIT 500

            """
            df = pd.read_sql(text(sql), con, params=params)

        if df.empty:
            st.info("Sin resultados con esos filtros.")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Error de conexión/consulta: {e}")

# ─────────────────────────────────────────────────────────────
# 📊 Dashboard de Top N (actores, directores, años, géneros)
#   - Podés aplicar los filtros actuales o ver el total global.
#   - Usa COUNT(DISTINCT ...) cuando corresponde para no duplicar por joins.
# ─────────────────────────────────────────────────────────────

st.subheader("📊 Dashboard — Top's")

colA, colB = st.columns([1, 2])
with colA:
    top_n = st.slider("Top N", min_value=3, max_value=10, value=5, step=1)
    usar_filtros = st.checkbox("Aplicar filtros actuales al dashboard", value=False)

# Armamos un WHERE según la elección (filtros o global)
if usar_filtros:
    dash_where_sql, dash_params = build_where(q, year_val, director_id_val, actor_id_val, score_exact)
else:
    dash_where_sql, dash_params = "WHERE 1=1", {}

# Consultas
actors_sql = f"""
    SELECT
        a.act_name AS Actor,
        COUNT(DISTINCT ma.movie_id) AS Peliculas
    FROM actor a
    JOIN movie_actor ma ON ma.actor_id = a.id
    JOIN movie m ON m.id = ma.movie_id
    {dash_where_sql}
    GROUP BY a.id, a.act_name
    ORDER BY Peliculas DESC, a.act_name ASC
    LIMIT :lim
"""

directors_sql = f"""
    SELECT
        d.dir_name AS Director,
        COUNT(*) AS Peliculas
    FROM movie m
    JOIN director d ON d.id = m.director_id
    {dash_where_sql}
    GROUP BY d.id, d.dir_name
    ORDER BY Peliculas DESC, d.dir_name ASC
    LIMIT :lim
"""

years_sql = f"""
    SELECT
        m.mov_year AS Año,
        COUNT(*) AS Peliculas
    FROM movie m
    {dash_where_sql}
    GROUP BY m.mov_year
    ORDER BY Peliculas DESC, m.mov_year ASC
    LIMIT :lim
"""

genres_sql = f"""
    SELECT
        g.gen_name AS Genero,
        COUNT(DISTINCT mg.movie_id) AS Peliculas
    FROM genre g
    JOIN movie_genre mg ON mg.genre_id = g.id
    JOIN movie m ON m.id = mg.movie_id
    {dash_where_sql}
    GROUP BY g.id, g.gen_name
    ORDER BY Peliculas DESC, g.gen_name ASC
    LIMIT :lim
"""

# Ejecutar y mostrar
with engine.begin() as con:
    params = {**dash_params, "lim": int(top_n)}
    top_actors = pd.read_sql(text(actors_sql), con, params=params)
    top_directors = pd.read_sql(text(directors_sql), con, params=params)
    top_years = pd.read_sql(text(years_sql), con, params=params)
    top_genres = pd.read_sql(text(genres_sql), con, params=params)

tab1, tab2, tab3, tab4 = st.tabs(["🎭 Actores", "🎬 Directores", "📅 Años", "🏷️ Géneros"])

with tab1:
    st.write(top_actors)
    if not top_actors.empty:
        chart_df = top_actors.set_index("Actor")["Peliculas"]
        st.bar_chart(chart_df)

with tab2:
    st.write(top_directors)
    if not top_directors.empty:
        chart_df = top_directors.set_index("Director")["Peliculas"]
        st.bar_chart(chart_df)

with tab3:
    st.write(top_years)
    if not top_years.empty:
        chart_df = top_years.set_index("Año")["Peliculas"]
        st.bar_chart(chart_df)

with tab4:
    st.write(top_genres)
    if not top_genres.empty:
        chart_df = top_genres.set_index("Genero")["Peliculas"]
        st.bar_chart(chart_df)

