import os
import sqlite3
from contextlib import closing
from secrets import token_hex
from urllib.parse import urlsplit

from flask import Flask, abort, flash, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or token_hex(32)
DATABASE = "posts.db"

dog_links = [
    {
        "title": "30 Fun and Fascinating Dog Facts",
        "url": "https://www.akc.org/expert-advice/lifestyle/dog-facts/",
        "score": 10,
        "hidden": False,
    },
    {
        "title": "Why Do Dogs Tilt Their Heads?",
        "url": "https://www.sciencefocus.com/nature/why-do-dogs-tilt-their-head-when-you-speak-to-them",
        "score": 5,
        "hidden": False,
    },
    {
        "title": "r/dogs — top posts",
        "url": "https://www.reddit.com/r/dogs/",
        "score": 3,
        "hidden": False,
    },
    {
        "title": "Basic Dog Training Guide",
        "url": "https://www.animalhumanesociety.org/resource/how-get-most-out-training-your-dog",
        "score": 2,
        "hidden": False,
    },
    {
        "title": "The Dogist (photo stories)",
        "url": "https://thedogist.com/",
        "score": 1,
        "hidden": False,
    },
]


def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with closing(get_db_connection()) as connection, connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                score INTEGER NOT NULL,
                hidden INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Serialize the empty check and seed when two processes start together.
        connection.execute("BEGIN IMMEDIATE")
        if connection.execute("SELECT 1 FROM posts LIMIT 1").fetchone() is None:
            connection.executemany(
                "INSERT INTO posts (title, url, score, hidden) VALUES (?, ?, ?, ?)",
                [(link["title"], link["url"], link["score"], link["hidden"]) for link in dog_links],
            )


def update_post(query):
    post_id = request.form.get("post_id", type=int)
    if post_id is None or not 0 < post_id <= 2**63 - 1:
        abort(400)
    with closing(get_db_connection()) as connection, connection:
        if connection.execute(query, (post_id,)).rowcount == 0:
            abort(404)
    return redirect(url_for("homepage"))


@app.post("/upvote")
def upvote():
    return update_post("UPDATE posts SET score = score + 1 WHERE id = ?")


@app.post("/downvote")
def downvote():
    return update_post("UPDATE posts SET score = score - 1 WHERE id = ?")


@app.post("/toggle-hide")
def toggle_hide():
    return update_post("UPDATE posts SET hidden = 1 - hidden WHERE id = ?")


def is_web_url(url):
    if any(character.isspace() for character in url):
        return False
    try:
        parsed = urlsplit(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.hostname)
    except ValueError:
        return False


@app.post("/submit")
def submit():
    title = request.form.get("title", "").strip()
    url = request.form.get("url", "").strip()
    if not title:
        flash("Enter a title for the post.")
    elif not is_web_url(url):
        flash("Enter a full web address beginning with http:// or https://.")
    else:
        with closing(get_db_connection()) as connection, connection:
            connection.execute(
                "INSERT INTO posts (title, url, score) VALUES (?, ?, 1)",
                (title, url),
            )
    return redirect(url_for("homepage"))


@app.get("/")
def homepage():
    with closing(get_db_connection()) as connection:
        links = connection.execute("SELECT * FROM posts ORDER BY score DESC, id").fetchall()

    return render_template(
        "index.html",
        links=[link for link in links if not link["hidden"]],
        hidden_links=[link for link in links if link["hidden"]],
    )


init_db()
