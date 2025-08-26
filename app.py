# Imports
from flask import Flask, render_template, redirect, request, url_for
from flask_scss import Scss
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select, func, case
from datetime import datetime

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


@app.route("/start", methods=["GET", "POST"])
def start_game():
    if request.method == 'POST':
        current_time = datetime.now()

        # Get players' names
        names = request.form.getlist("player_name")
        names = [p.strip() for p in names if p.strip()] # Remove whitespace

        # Check for existing players
        existing_players = {p.name: p for p in Player.query.filter(Player.name.in_(names)).all()}
        new_game = Game(start_at=current_time)
        db.session.add(new_game)
        db.session.flush()  # Flush to get the game_id

        for i, name in enumerate(names):
            if name in existing_players:
                # Use existing player
                player = existing_players[name]
            else:
                # Create new player
                player = Player(name=name, first_play_at=current_time)
                db.session.add(player)
                db.session.flush()

            # Link players to game
            game_player = GamePlayer(
                game_id=new_game.id,
                player_num=i+1,
                player_id=player.id
            )
            db.session.add(game_player)
        
        db.session.commit()
        app.logger.info(f"New Game #{new_game.id} started with players: {', '.join(names)}")
        return redirect(url_for('add_round_result', game_id=new_game.id, round_num=1))
    else:
        return render_template('start.html')
    # end if else


@app.route("/game/<int:game_id>/round/<int:round_num>", methods=["GET", "POST"])
def add_round_result(game_id, round_num):
    players = db.session.query(Player).join(GamePlayer).filter(GamePlayer.game_id==game_id).order_by(GamePlayer.player_num).all()
    players_names = [player.name for player in players]

    # Handle form submission for round results
    if request.method == 'POST':
        faan = int(request.form.get("faan"))
        winner = request.form.get("winner")
        deal_inner = request.form.get("deal_inner")

        # Get winner and deal-inner IDs
        winner_id = db.session.query(Player.id).filter_by(name=winner).scalar()
        deal_inner_id = db.session.query(Player.id).filter_by(name=deal_inner).scalar()

        # Calculate score
        if deal_inner_id is None: # self-drawn
            winner_score = pow(2, faan) * 3
            others_score = -pow(2, faan)
        else: # not self-drawn
            winner_score = pow(2, faan) * 2
            deal_inner_score = -pow(2, faan)
            others_score = -pow(2, faan)/2 # Adjusted to handle float division
        
        # Get all player IDs
        players_id = db.session.execute(
            select(Player.id).join(GamePlayer).where(GamePlayer.game_id == game_id)
        ).scalars().all()

        app.logger.info(f"Form players_id value: {players_id!r}")
        
        #Queries to input results
        winner_result = RoundResult(
            game_id=game_id,
            round_num=round_num, 
            player_id=winner_id, 
            score=winner_score
        )
        db.session.add(winner_result)
        
        if deal_inner_id is not None:
            deal_inner_result = RoundResult(
                game_id=game_id, 
                round_num=round_num, 
                player_id=deal_inner_id, 
                score=deal_inner_score
            )
            db.session.add(deal_inner_result)
        # end if

        for others_id in players_id:
            if others_id != winner_id and others_id != deal_inner_id:
                app.logger.info(f"Form others_id value: {others_id!r}")
                others_result = RoundResult(
                    game_id=game_id, 
                    round_num=round_num, 
                    player_id=others_id, 
                    score=others_score
                )
                db.session.add(others_result)
            # end if
        # end for

        db.session.commit()
        # Move to next round
        return redirect(url_for('add_round_result', 
                                game_id=game_id, 
                                round_num=round_num+1))
    # end POST
    
    
    # GET: Show the results of the previous rounds
    rounds = (
        db.session.query(
            RoundResult.round_num,
            *[
                func.sum(
                    case((GamePlayer.player_num == i, RoundResult.score), else_=0)
                    ).label(f"Player_{i}_score")
                for i in range(1, 5)
            ],
        )
        .join(GamePlayer, (RoundResult.game_id == GamePlayer.game_id) 
              & (RoundResult.player_id == GamePlayer.player_id))
        .filter(RoundResult.game_id == game_id)
        .group_by(RoundResult.round_num)
        .order_by(RoundResult.round_num)
        .all()
    )

    round_list = [
        {
            "round_num": r.round_num,
            "player_1_score": r.Player_1_score,
            "player_2_score": r.Player_2_score,
            "player_3_score": r.Player_3_score,
            "player_4_score": r.Player_4_score
        }
        for r in rounds
    ]
    app.logger.info(f"Round list: {round_list}")

    # Sum scores per player
    scores = (
        db.session.query(
            RoundResult.player_id,
            func.sum(RoundResult.score).label("total_score")
        )
        .filter(RoundResult.game_id == game_id)
        .group_by(RoundResult.player_id)
        .order_by(func.sum(RoundResult.score).desc())
    ).all()

    if scores:
        top_score = scores[0].total_score
        leaders = [s.player_id for s in scores if s.total_score == top_score]
    else:
        leaders = []

    return render_template('round.html', 
                           game_id=game_id, 
                           round_num=round_num, 
                           players_names=players_names, 
                           round_list=round_list, 
                           leadingPlayerId=leaders)


@app.route("/end/game/<int:game_id>")
def end_game(game_id):
    end_time = datetime.now()

    # Get players' names and scores
    players = (
        db.session.query(
            Player.name,
            func.coalesce(func.sum(RoundResult.score), 0).label("total_score"),
            Player.id
        )
        .join(RoundResult, RoundResult.player_id == Player.id)
        .filter(RoundResult.game_id == game_id)
        .group_by(RoundResult.player_id)
        .order_by(func.coalesce(func.sum(RoundResult.score), 0).desc())
        .all()
    )
    for p in players:
        app.logger.info(f"Player: {p.name}, Total Score: {p.total_score}, ID: {p.id}")

    # Update PlayerResult with player's total_score
    for p in players:
        player_result = PlayerResult(
            game_id=game_id,
            player_id=p.id,
            total_score=p.total_score,
        )
        db.session.add(player_result)

    # Update Player total_score
    for p in players:
        player = db.session.get(Player, p.id)
        player.total_score += p.total_score
    
    # Create a list of player names and their total scores
    player_list = [
        {
            "name": p.name,
            "total_score": p.total_score
        }
        for p in players
    ]
    app.logger.info(f"Player list: {player_list}")

    # Get total rounds played
    total_rounds = db.session.query(func.max(RoundResult.round_num)).filter(RoundResult.game_id == game_id).scalar()
    if total_rounds is None:
        total_rounds = 0
    
    # Update Game total_rounds and end_at
    game = db.session.get(Game, game_id)
    game.total_rounds = total_rounds
    game.end_at = end_time

    # Update Player played_num and last_play_at
    players = db.session.query(Player).join(GamePlayer).filter(GamePlayer.game_id == game_id).all()
    for player in players:
        player.played_num += 1
        player.last_play_at = end_time

    # Remove microseconds
    time_diff = str(end_time - game.start_at).split(".")[0]

    db.session.commit()
    
    return render_template('endgame.html', game_id=game_id, player_list=player_list, total_rounds=total_rounds, total_time=time_diff)

@app.route("/history", methods=["GET", "POST"])
def view_history():
    if request.method == 'POST':
        game_id = request.form.get("game_id")
        if game_id:
                return redirect(url_for('game_info', game_id=game_id))
        else:
            return render_template('history.html', error="Game ID does not exist.")
        
    return render_template('history.html')

@app.route("/history/game/<int:game_id>")
def game_info(game_id):
    # Get game info
    total_rounds = db.session.query(Game.total_rounds).filter(Game.id == game_id).scalar()
    start_time = db.session.query(Game.start_at).filter(Game.id == game_id).scalar()
    end_time = db.session.query(Game.end_at).filter(Game.id == game_id).scalar()
    total_time = str(end_time - start_time).split(".")[0] if end_time else "N/A"

    players = (
        db.session.query(
            Player.name,
            PlayerResult.total_score
        )
        .join(PlayerResult, PlayerResult.player_id == Player.id)
        .filter(PlayerResult.game_id == game_id)
        .order_by(Player.id)
        .all()
    )
    app.logger.info(f"Players in game {game_id}: {players}")

    return render_template('gameinfo.html', game_id=game_id, total_rounds=total_rounds, start_time=start_time, end_time=end_time, total_time=total_time, players=players)

@app.route("/leaderboard")
def leaderboard():
    # Get all players and their total scores
    players = (
        db.session.query(
            Player.name,
            PlayerResult.total_score
        )
        .join(PlayerResult, PlayerResult.player_id == Player.id)
        .order_by(PlayerResult.total_score.desc())
        .all()
    )
    return render_template('leaderboard.html', players=players)

    

# Runner and Debugger
if __name__ == "__main__":
    app.run(debug=True)