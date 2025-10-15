# *🍿 IMDb Top 250 Database 🍿*
## 🤔 DESCRIPCIÓN 🤔
En este trabajo estaremos mostrando el paso a paso del diseño, normalizacion y creacion de una base de datos de las 250 mejores peliculas de la historia segun IMDb actualizadas hasta el año 2024,  esto se va a crear desde un CSV descargado de una pagina de bases de datos libres.

El .csv lo descargamos directamente de la pagina kaggle.com 
# INSTALACION📥
###  1) Clonar el repositorio con: 
```bash
git clone https://github.com/EduPonce2/BEST-MOVIES-OF-IMDB_Database.git
```
### 2) Cargar el script o archivo sql  en el repositorio de su base de datos de preferencia 
# DIAGRAMA ENTIDAD-RELACION
![ERD Movies](img/diagrama.png)

# EXPLICACION SOBRE COMO FUIMOS ARMANDO LA BASE DE DATOS ✍🏻
Después de descargar el .csv, lo que hicimos fue exportarlo a MySQL WORKBENCH, lo que se hace para importarlo es lo siguiente:
-Crear la base de datos con:
```sql
CREATE DATABASE movies;
```
- Una vez creada la base de datos, en el panel lateral de Workbench, hacer click derecho en la seccion que dice 'Tables' que pertenece a la DB que hemos creado y elegir la opcion 'Table Data Import Wizard'.

- Elegir el .csv desde el boton 'Browse', una vez elegido confirmar con 'Next'. 
- Confirmar que estamos cargando en la base de datos que hemos creado, darle un nombre a la tabla que se va a crear, en nuestro caso le pusimos 'movies_cruda'.

- Al confirmar el paso anterior nos pasa a la siguiente pantalla donde vemos las columnas que se crean a partir del csv, pero hay que confirmar que está bien configurada la forma de crear de Workbench, esto lo hacemos apretando el boton con 🔧 y la configuracion debe ser la siguiente para evitar errores:
    ``` 
    Field Separator: ,

    Line Separator: LF

    Enclose Strings in: "

    null and NULL as SQL keyword: YES
    ```

- Por ultimo, corroboramos que existan todas las columnas de nuestra tabla, le damos 'Next' y se nos crea la tabla cruda de la cual luego vamos a ir sacando los datos para poblar las tablas reales de nuestra DB.


### Creamos las tablas de la siguiente forma: 
### 1) Tabla Director

``` sql
CREATE TABLE director (
id INT NOT NULL auto_increment PRIMARY KEY,
dir_name VARCHAR(100) NOT NULL UNIQUE
)CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2) Tabla Genero

``` sql
CREATE TABLE genre (
id INT NOT NULL auto_increment PRIMARY KEY,
gen_name VARCHAR(100) NOT NULL UNIQUE
)CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```
### 3) Tabla Actor

``` sql
CREATE TABLE actor (
id INT NOT NULL auto_increment PRIMARY KEY,
act_name VARCHAR(100) NOT NULL UNIQUE
)CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4) Tabla Peliculas

``` sql
CREATE TABLE  movie (
id INT NOT NULL auto_increment PRIMARY KEY,
title VARCHAR(255) NOT NULL,
mov_year SMALLINT NOT NULL,
score DECIMAL(3,1) NOT NULL,
duration INT NOT NULL, 
synopsis TEXT,
director_id INT NOT NULL,
FOREIGN KEY(director_id) REFERENCES director (id),
CONSTRAINT uq_movie_title_year UNIQUE (title, mov_year)
)CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## Seguimos con sus Relaciones 🔗

### 1) Tabla intermedia Pelicula Actor
``` sql
 CREATE TABLE movie_actor (
movie_id INT NOT NULL,
FOREIGN KEY (movie_id) REFERENCES movie(id),
actor_id INT NOT NULL,
FOREIGN KEY (actor_id) REFERENCES actor(id),
PRIMARY KEY (movie_id, actor_id)
)CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2) Tabla intermedia Pelicula Género
``` sql
CREATE TABLE movie_genre (
genre_id INT NOT NULL,
movie_id INT NOT NULL,
FOREIGN KEY (genre_id) REFERENCES genre(id),
FOREIGN KEY (movie_id) REFERENCES movie(id),
PRIMARY KEY(movie_id, genre_id)
)CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

# 🧩 EXPLICACION DE LOS SCRIPTS SQL 
 Este conjunto de sentencias SQL se utiliza para limpiar, normalizar y poblar las tablas del modelo relacional a partir de los datos crudos almacenados en movies_cruda.

### 🎬 1️⃣ Inserción de Directores 

``` sql
INSERT INTO director (dir_name)
SELECT DISTINCT TRIM(director)
FROM movies_cruda;
```

Extrae los nombres de los directores desde movies_cruda.
Elimina duplicados (DISTINCT) y espacios en blanco (TRIM).
Inserta cada director único en la tabla director.

### 🎭 2️⃣ Inserción de Géneros

``` sql
INSERT IGNORE INTO genre (gen_name)
SELECT DISTINCT TRIM(j.g) AS gen_name
FROM movies_cruda r
JOIN JSON_TABLE(
  CONCAT(
    '["',
    REPLACE(
      REGEXP_REPLACE(TRIM(r.genre), '\\s+', ' '),
      ' ',
      '","'
    ),
    '"]'
  ),
  '$[*]' COLUMNS (g.VARCHAR(100) PATH '$')
) AS j
WHERE r.genre IS NOT NULL AND r.genre <> ''
  AND j.g <> '';
```

Descompone los géneros (que pueden venir en una sola celda) usando JSON_TABLE.
Limpia espacios y genera una fila por cada género.
Inserta solo géneros distintos (DISTINCT) en la tabla genre.
El INSERT IGNORE evita duplicados.

### 🎥 3️⃣ Inserción de Películas

``` sql
INSERT INTO movie (title, mov_year, score, duration, synopsis, director_id)
SELECT
  r.name AS title,
  r.year AS mov_year,
  CAST(r.rating AS DECIMAL(3,1)) AS score,
  COALESCE(CAST(REGEXP_SUBSTR(TRIM(r.duration), '[0-9]+(?=h)') AS UNSIGNED), 0) * 60 + COALESCE(CAST(REGEXP_SUBSTR(TRIM(r.duration), '[0-9]+(?=min)') AS UNSIGNED), 0) AS duration,
  r.description AS synopsis,
  d.id AS director_id
FROM movies_cruda r
JOIN director d
  ON d.dir_name COLLATE utf8mb4_unicode_ci = TRIM(r.director) COLLATE utf8mb4_unicode_ci;
  ```

Inserta los datos de cada película, convirtiendo:
rating → número decimal (DECIMAL(3,1)).
duration → minutos totales (sumando horas y minutos).
Asocia cada película a su director mediante director_id.

### 🎞️ 4️⃣ Relación Película ↔ Género

``` sql
INSERT IGNORE INTO movie_genre (movie_id, genre_id)
SELECT
  m.id AS movie_id,
  g.id AS genre_id
FROM movies_cruda r
JOIN movie m
  ON m.title COLLATE utf8mb4_unicode_ci = TRIM(r.name) COLLATE utf8mb4_unicode_ci
 AND m.mov_year = r.year
JOIN JSON_TABLE(
  CONCAT(
    '["',
    REPLACE(REGEXP_REPLACE(TRIM(r.genre), '\\s+', ' '), ' ', '","'),
    '"]'
  ),
  '$[*]' COLUMNS (gname VARCHAR(100) PATH '$')
) jt
JOIN genre g
  ON g.gen_name COLLATE utf8mb4_unicode_ci = jt.gname COLLATE utf8mb4_unicode_ci
WHERE r.genre IS NOT NULL AND r.genre <> '' 
  AND jt.gname <> '';
  ```

Une cada película con todos sus géneros.
Si una película tiene varios géneros, genera una fila por cada combinación.
Usa INSERT IGNORE para evitar duplicados.

### 👥 5️⃣ Creación de Tabla Temporal de Actores

``` sql
DROP TEMPORARY TABLE IF EXISTS _actors_temp;
CREATE TEMPORARY TABLE _actors_temp (
  movie_id INT,
  actor_name VARCHAR(255)
);
```

Crea una tabla temporal que almacenará los pares película - actor.
Se usa como paso intermedio antes de insertar los datos finales.
Mas adelante explicaremos por qué fue necesario este paso.

### 🌟 6️⃣ Poblar la Tabla Temporal

``` sql
INSERT INTO _actors_temp (movie_id, actor_name)
SELECT
  m.id AS movie_id,
  TRIM(j.actor) AS actor_name
FROM movies_cruda c
JOIN movie m
  ON m.title COLLATE utf8mb4_unicode_ci = c.name COLLATE utf8mb4_unicode_ci
 AND m.mov_year = c.year
JOIN JSON_TABLE(
  CONCAT(
    '["',
    REPLACE(REPLACE(TRIM(COALESCE(c.stars,'')), ' # ', '#'), '#', '","'),
    '"]'
  ),
  '$[*]' COLUMNS (actor VARCHAR(255) PATH '$')
) AS j
WHERE TRIM(j.actor) <> '';
```

Extrae los actores del campo stars, que viene separado por #.
Limpia los valores y crea una fila por cada actor con su película correspondiente.

### 🔍 7️⃣ Verificación de la Carga

``` sql
SELECT * FROM _actors_temp ORDER BY movie_id, actor_name LIMIT 20;
SELECT COUNT(*) FROM _actors_temp;
``` 

Permite verificar visualmente que los datos de la tabla temporal se cargaron correctamente y contar la cantidad total de registros.

### 🎬 8️⃣ Inserción Final de Actores y Relaciones

``` sql
INSERT IGNORE INTO actor (act_name)
SELECT DISTINCT actor_name FROM _actors_temp;
``` 

```sql
INSERT IGNORE INTO movie_actor (movie_id, actor_id)
SELECT t.movie_id, a.id
FROM _actors_temp t
JOIN actor a
  ON TRIM(a.act_name) COLLATE utf8mb4_unicode_ci
   = TRIM(t.actor_name) COLLATE utf8mb4_unicode_ci;
   ```

Estas sentencias sirven para migrar datos desde una tabla temporal _actors_temp hacia el modelo final de base de datos:
La primera carga los actores nuevos.
La segunda vincula los actores con sus películas, creando relaciones en movie_actor.
# 🚨 ERRORES O PROBLEMAS QUE APARECIERON 🚨

## 🧩 Tabla Genre (Género)

El archivo .csv original contenía las siguientes columnas:
name, genre, description, duration, rating, director, stars.

El primer problema surgió porque la columna genre contenía múltiples valores dentro de una misma celda, es decir, una película podía tener más de un género (por ejemplo: Drama, Adventure, Sci-Fi).
Esto violaba el principio de atomicidad de las bases de datos relacionales, donde cada campo debe contener un único valor.

Para resolverlo:

- Se creó la tabla genre con un campo gen_name único (UNIQUE), garantizando que no existan géneros duplicados.

- Luego, se extrajeron todos los valores distintos de la columna genre del CSV, separándolos por comas y eliminando repeticiones.

- Finalmente, se generó la tabla intermedia movie_genre, que relaciona cada película con sus respectivos géneros mediante los id de ambas tablas.

Este proceso permitió normalizar los datos, asegurando una relación muchos a muchos (N:M) entre películas y géneros, donde una película puede pertenecer a varios géneros y un género puede aplicarse a varias películas.

## 🎭 Tabla Actor

La columna stars del CSV presentaba un desafío mayor.
Cada película incluía tres actores en una misma celda, y estos podían tener diferentes estructuras de nombre:

- un nombre y un apellido (Leonardo DiCaprio),

- dos nombres y un apellido o apellido compuesto (Robert Downey Jr. o Robert De Niro),

- o incluso un solo nombre artístico (Zendaya).

Esto imposibilitaba separar los actores simplemente usando espacios o comas, ya que se podía confundir partes de nombres compuestos.

🔧 Solución implementada

Se editó manualmente el CSV usando Visual Studio Code, agregando un carácter separador personalizado # entre los nombres de los actores (por ejemplo:
Tom Holland#Zendaya#Benedict Cumberbatch).
Este símbolo fue elegido porque no aparecía en ningún nombre real y permitía separar los valores con precisión.

En SQL, se creó una tabla temporal para dividir la columna stars usando el separador #.
A partir de esa división:

- Se generó una lista limpia de actores,

- Se insertaron en la tabla actor evitando duplicados (gracias al campo UNIQUE en act_name), y se construyó la tabla intermedia movie_actor para mapear correctamente cada actor con su película mediante sus respectivos id.

De esta manera se resolvieron los problemas de estructura, codificación y relación entre las tablas, logrando una base de datos totalmente normalizada y lista para consultas complejas como “todas las películas de un actor” o “el elenco completo de una película”.