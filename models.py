from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint
from datetime import datetime

db = SQLAlchemy()

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    total_rounds = db.Column(db.Integer, default=1)
    start_at = db.Column(db.DateTime, default=datetime.now)
    end_at = db.Column(db.DateTime, default=datetime.now)


class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    played_num = db.Column(db.Integer, default=0)
    first_play_at = db.Column(db.DateTime, default=datetime.now)
    last_play_at = db.Column(db.DateTime, default=datetime.now)
    total_score = db.Column(db.Integer, default=0)


class GamePlayer(db.Model):
    __tablename__ = 'game_player'

    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), primary_key=True)
    player_num = db.Column(db.Integer, nullable=False, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'))

    @classmethod
    def default_order(cls):
        return cls.query.order_by(cls.game_id.asc())


class PlayerResult(db.Model):
    __tablename__ = 'player_result'

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'))
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'))
    total_score = db.Column(db.Integer, default=0)


class RoundResult(db.Model):
    __tablename__ = 'round_result'

    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), primary_key=True)
    round_num = db.Column(db.Integer, default=1, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), primary_key=True)
    score = db.Column(db.Integer, default=0)
