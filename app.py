# Imports
from flask import Flask, render_template
from flask_scss import Scss
from flask_sqlalchemy import SQLAlchemy

# Models
from models import db, Game, Player, GamePlayer, PlayerResult, RoundResult

# My App
app = Flask(__name__)
Scss(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:mySQLpw00!@localhost/mahjong_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


# Routes to Webpages
@app.route("/")
def index():
    return render_template('index.html')

@app.route("/start")
def start_game():
    return render_template('start.html')

@app.route("/history")
def view_history():
    return render_template('history.html')

@app.route("/leaderboard")
def leaderboard():
    return render_template('leaderboard.html')

    

# Runner and Debugger
if __name__ == "__main__":
    app.run(debug=True)