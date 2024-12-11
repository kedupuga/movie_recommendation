from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from surprise import Dataset, Reader, SVD
import pandas as pd

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('movie.db')
    conn.row_factory = sqlite3.Row
    return conn

# Home Page
@app.route('/')
def index():
    conn = get_db_connection()
    movies = conn.execute('SELECT * FROM movies').fetchall()
    conn.close()
    return render_template('index.html', movies=movies)

# Add Movie
@app.route('/add', methods=('GET', 'POST'))
def add_movie():
    if request.method == 'POST':
        title = request.form['title']
        genre = request.form['genre']
        rating = request.form['rating']
        conn = get_db_connection()
        conn.execute('INSERT INTO movies (title, genre, rating) VALUES (?, ?, ?)', (title, genre, rating))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    return render_template('add_movie.html')

# Edit Movie
@app.route('/edit/<int:id>', methods=('GET', 'POST'))
def edit_movie(id):
    conn = get_db_connection()
    movie = conn.execute('SELECT * FROM movies WHERE id = ?', (id,)).fetchone()
    if request.method == 'POST':
        title = request.form['title']
        genre = request.form['genre']
        rating = request.form['rating']
        conn.execute('UPDATE movies SET title = ?, genre = ?, rating = ? WHERE id = ?',
                     (title, genre, rating, id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    conn.close()
    return render_template('edit_movie.html', movie=movie)

# Delete Movie
@app.route('/delete/<int:id>', methods=('POST',))
def delete_movie(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM movies WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# Rate Movie
@app.route('/rate', methods=('GET', 'POST'))
def rate_movie():
    conn = get_db_connection()
    movies = conn.execute('SELECT * FROM movies').fetchall()
    conn.close()
    if request.method == 'POST':
        user_id = request.form['user_id']
        movie_id = request.form['movie_id']
        rating = request.form['rating']
        conn = get_db_connection()
        conn.execute('INSERT OR REPLACE INTO user_ratings (user_id, movie_id, rating) VALUES (?, ?, ?)',
                     (user_id, movie_id, rating))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    return render_template('rate_movie.html', movies=movies)

# Recommendations
@app.route('/recommendations', methods=('GET',))
def recommendations():
    user_id = request.args.get('user_id', type=int)
    conn = get_db_connection()
    ratings = pd.read_sql_query('SELECT * FROM user_ratings', conn)
    movies = pd.read_sql_query('SELECT * FROM movies', conn)
    conn.close()

    if ratings.empty or user_id is None:
        return render_template('recommendations.html', movies=[])

    reader = Reader(rating_scale=(0.5, 5.0))
    data = Dataset.load_from_df(ratings[['user_id', 'movie_id', 'rating']], reader)
    trainset = data.build_full_trainset()

    model = SVD()
    model.fit(trainset)

    user_ratings = ratings[ratings['user_id'] == user_id]
    rated_movie_ids = user_ratings['movie_id'].values
    predictions = [
        (movie['id'], movie['title'], model.predict(user_id, movie['id']).est)
        for _, movie in movies.iterrows()
        if movie['id'] not in rated_movie_ids
    ]
    predictions.sort(key=lambda x: x[2], reverse=True)
    recommendations = predictions[:5]
    return render_template('recommendations.html', movies=recommendations)

if __name__ == '__main__':
    app.run(debug=True)
