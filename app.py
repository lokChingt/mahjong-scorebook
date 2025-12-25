# Imports
from flask import Flask, render_template, redirect, request, url_for
from flask_scss import Scss
from sqlalchemy import select, func, case
from datetime import datetime

# Models
from models import db, Game, Player, GamePlayer, PlayerResult, RoundResult

# My App
app = Flask(__name__)
Scss(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/mahjong_db'
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
                game_id=new_game.game_id,
                player_num=i+1,
                player_id=player.player_id
            )
            db.session.add(game_player)
        
        db.session.commit()
        return redirect(url_for('add_round_result', game_id=new_game.game_id, round_num=1))
    else:
        return render_template('start.html')
    # end if else

def get_round_info(game_id):
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

    return round_list

@app.route("/game/<int:game_id>/round/<int:round_num>", methods=["GET", "POST"])
def add_round_result(game_id, round_num):
    # Handle form submission for round results
    if request.method == 'POST':
        faan = int(request.form.get("faan"))

        # Get winner and deal-inner IDs
        winner_id = int(request.form.get("winner"))
        deal_inner_id = request.form.get("deal_inner")
        if deal_inner_id:
            deal_inner_id = int(deal_inner_id)

        # Calculate score
        if not deal_inner_id: # self-drawn
            winner_score = pow(2, faan) * 3
            others_score = -pow(2, faan)
        else: # not self-drawn
            winner_score = pow(2, faan) * 2
            deal_inner_score = -pow(2, faan)
            others_score = -pow(2, faan)/2
        
        # Get all player IDs
        players_id = db.session.execute(
            select(Player.player_id).join(GamePlayer).where(GamePlayer.game_id == game_id)
        ).scalars().all()

        
        # Queries to input results
        winner_result = RoundResult(
            game_id=game_id,
            round_num=round_num, 
            player_id=winner_id, 
            score=winner_score
        )
        db.session.add(winner_result)
        
        if deal_inner_id:
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
    players = db.session.query(Player).join(GamePlayer).filter(GamePlayer.game_id==game_id).order_by(GamePlayer.player_num).all()
    players_info = [{"id": player.player_id, "name": player.name} for player in players]

    round_list = get_round_info(game_id)

    # Sum scores per player
    scores = (
        db.session.query(
            GamePlayer.player_num,
            func.sum(RoundResult.score).label("total_score")
        )
        .filter(RoundResult.game_id == game_id)
        .join(GamePlayer, (RoundResult.game_id == GamePlayer.game_id) 
              & (RoundResult.player_id == GamePlayer.player_id))
        .group_by(GamePlayer.player_num)
        .order_by(func.sum(RoundResult.score).desc())
    ).all()

    if scores:
        top_score = scores[0].total_score
        leaders = [s.player_num for s in scores if s.total_score == top_score]
    else:
        leaders = []

    return render_template('round.html', 
                           game_id=game_id, 
                           round_num=round_num, 
                           players_info=players_info, 
                           round_list=round_list, 
                           leadingPlayerId=leaders)

@app.route("/game/<int:game_id>/round/<int:round_num>/edit", methods=["GET", "POST"])
def edit(game_id, round_num):
    players = (
        db.session.query(
            Player.player_id,
            Player.name,
            RoundResult.score
        )
        .join(
            GamePlayer,
            (RoundResult.player_id == GamePlayer.player_id) &
            (RoundResult.game_id == GamePlayer.game_id)
        )
        .join(Player, GamePlayer.player_id == Player.player_id)
        .filter(
            RoundResult.game_id == game_id,
            RoundResult.round_num == round_num
        )
        .order_by(GamePlayer.player_num)
        .all()
    )

    players_info = [
        {
            "id": p.player_id,
            "name": p.name,
            "score": p.score
        }
        for p in players
    ]

    total_score = 0

    # Update scores based on form input
    if request.method == "POST":
        for player in players_info:
            field_name = f"player{player["id"]}_score"
            new_score = request.form.get(field_name)
            app.logger.info(f"Form {field_name} value: {new_score!r}")
            if new_score is not None:
                player = db.session.get(RoundResult, (game_id, round_num, player["id"]))
                player.score = int(new_score)
                total_score += int(new_score)
        
        # Check if the scores are valid
        if total_score != 0:
            error_msg = f"Total score for round {round_num} must be 0."
            return render_template('edit.html', 
                                   game_id=game_id, 
                                   round_num=round_num,
                                   players=players_info,
                                   error=error_msg)

        # Get the max round number for the game
        max_round_num = (
            db.session.query(func.max(RoundResult.round_num))
            .filter(RoundResult.game_id==game_id)
            .scalar()
        )

        db.session.commit()
        return redirect(url_for("add_round_result", game_id=game_id, round_num=max_round_num+1))


    return render_template('edit.html', 
                           game_id=game_id, 
                           round_num=round_num,
                           players=players_info)

@app.route("/game/<int:game_id>/round/<int:round_num>/delete")
def delete(game_id, round_num):
    delete_round = (
        db.session.query(RoundResult)
        .filter(RoundResult.game_id==game_id, RoundResult.round_num==round_num)
        .all()
    )

    for r in delete_round:
        db.session.delete(r)
        db.session.commit()

    return redirect(url_for("add_round_result", game_id=game_id, round_num=round_num))

@app.route("/end/game/<int:game_id>")
def end_game(game_id):
    end_time = datetime.now()

    # Get players' names and scores
    players = (
        db.session.query(
            Player.name,
            func.coalesce(func.sum(RoundResult.score), 0).label("total_score"),
            Player.player_id
        )
        .join(RoundResult, RoundResult.player_id == Player.player_id)
        .filter(RoundResult.game_id == game_id)
        .group_by(RoundResult.player_id)
        .order_by(func.coalesce(func.sum(RoundResult.score), 0).desc())
        .all()
    )

    for p in players:
        player_result = PlayerResult(
            game_id=game_id,
            player_id=p.player_id,
            total_score=p.total_score,
        )
        db.session.add(player_result)

    # Update Player total_score
    for p in players:
        player = db.session.get(Player, p.player_id)
        player.total_score += p.total_score
    
    # Create a list of player names and their total scores
    player_list = [
        {
            "name": p.name,
            "total_score": p.total_score
        }
        for p in players
    ]

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
    
    return render_template('endgame.html', 
                           game_id=game_id, 
                           player_list=player_list, 
                           total_rounds=total_rounds, 
                           total_time=time_diff)


@app.route("/history", methods=["GET", "POST"])
def view_history():
    if request.method == 'POST':
        game_id = request.form.get("game_id")
        if game_id in [str(g.game_id) for g in Game.query.all()]:
                return redirect(url_for('game_info', game_id=game_id))
        else:
            return render_template('history.html', error="Game ID does not exist.")
        
    return render_template('history.html')


@app.route("/history/game/<int:game_id>")
def game_info(game_id):
    # Get game info
    total_rounds = db.session.query(Game.total_rounds).filter(Game.game_id == game_id).scalar()
    start_at = db.session.query(Game.start_at).filter(Game.game_id == game_id).scalar()
    end_at = db.session.query(Game.end_at).filter(Game.game_id == game_id).scalar()
    total_time = str(end_at - start_at).split(".")[0] if end_at else "N/A"

    # Format date and time
    if start_at and end_at:
        date = start_at.strftime("%Y-%m-%d")
        start_time = start_at.strftime("%H:%M:%S")
        end_time = end_at.strftime("%H:%M:%S")
    else:
        date = "N/A"
        start_time = "N/A"
        end_time = "N/A"

    # Get players info
    players_info = (
        db.session.query(Player.name)
        .join(PlayerResult, PlayerResult.player_id == Player.player_id)
        .filter(PlayerResult.game_id == game_id)
        .all()
    )

    # Get players rank and their scores
    players_rank = (
        db.session.query(
            Player.name,
            func.sum(PlayerResult.total_score).label("total_score"),
        )
        .join(PlayerResult, PlayerResult.player_id == Player.player_id)
        .filter(PlayerResult.game_id == game_id)
        .group_by(Player.name)
        .order_by(func.sum(PlayerResult.total_score).desc())
        .all()
    )
    app.logger.info(f"total_rounds: {total_rounds}")

    # Check if game exists
    if total_rounds is None:
        return render_template('history.html', error="Game ID does not exist.")
    elif total_rounds == 0:
        return render_template('history.html', error="This game has no rounds played.")
    
    # Get all rounds results
    round_list = get_round_info(game_id)

    return render_template('gameinfo.html', 
                           game_id=game_id, 
                           total_rounds=total_rounds,
                           date=date,
                           start_time=start_time, 
                           end_time=end_time, 
                           total_time=total_time, 
                           players_rank=players_rank,
                           players=players_info,
                           round_list=round_list)


@app.route("/leaderboard")
def leaderboard():
    # Get all players and their total scores
    players = (
        db.session.query(
            Player.name,
            func.sum(PlayerResult.total_score).label("total_score"),
        )
        .join(PlayerResult, PlayerResult.player_id == Player.player_id)
        .group_by(Player.name)
        .order_by(func.sum(PlayerResult.total_score).desc())
        .all()
    )
    return render_template('leaderboard.html', players=players)

    

# Runner and Debugger
if __name__ == "__main__":
    app.run(debug=True)