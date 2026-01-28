from app import app
from models import db, Game, Player, GamePlayer, PlayerResult, RoundResult

with app.app_context():
    db.drop_all()
    db.create_all()
    print("Successfully resetted all tables")
