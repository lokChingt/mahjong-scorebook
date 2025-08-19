# Imports
from flask import Flask, render_template, redirect, request, url_for
from flask_scss import Scss
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select, func, case

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
        # Get players' names
        names = request.form.getlist("player_name")
        names = [p.strip() for p in names if p.strip()] # Remove whitespace

        # Check for existing players
        existing_players = {p.name: p for p in Player.query.filter(Player.name.in_(names)).all()}
        new_game = Game()
        db.session.add(new_game)
        db.session.flush()  # Flush to get the game_id

        for i, name in enumerate(names):
            if name in existing_players:
                # Use existing player
                player = existing_players[name]
            else:
                # Create new player
                player = Player(name=name)
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
    players = db.session.query(Player).join(GamePlayer).filter(GamePlayer.game_id==game_id).all()
    players_names = [player.name for player in players]

    # Handle form submission for round results
    if request.method == 'POST':
        faan = int(request.form.get("faan"))
        winner = request.form.get("winner")
        deal_inner = request.form.get("deal_inner")
        
        # Calculate score
        winner_score = pow(2, faan) * 2
        deal_inner_score = -pow(2, faan)
        others_score = float(-pow(2, faan)/2) # Adjusted to handle float division

        # Get winner and deal-inner IDs
        winner_id = db.session.query(Player.id).filter_by(name=winner).scalar()
        deal_inner_id = db.session.query(Player.id).filter_by(name=deal_inner).scalar()
        
        # Get all player IDs
        query = select(Player.id).join(GamePlayer).where(GamePlayer.game_id == game_id)
        result = db.session.execute(query)
        players_id = result.scalars().all()

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
        return redirect(url_for('add_round_result', game_id=game_id, round_num=round_num+1))
    # end if
    
    
    # GET: Show the results of the previous rounds
    rounds = (
        db.session.query(
            RoundResult.round_num,
            func.sum(case((RoundResult.player_id == 1, RoundResult.score), else_=0)).label("Player_1"),
            func.sum(case((RoundResult.player_id == 2, RoundResult.score), else_=0)).label("Player_2"),
            func.sum(case((RoundResult.player_id == 3, RoundResult.score), else_=0)).label("Player_3"),
            func.sum(case((RoundResult.player_id == 4, RoundResult.score), else_=0)).label("Player_4"),
        )
        .filter(RoundResult.game_id == game_id)
        .group_by(RoundResult.round_num)
        .order_by(RoundResult.round_num)
        .all()
    )

    round_list = [
        {
            "round_num": r.round_num,
            "Player_1": r.Player_1,
            "Player_2": r.Player_2,
            "Player_3": r.Player_3,
            "Player_4": r.Player_4,
        }
        for r in rounds
    ]
    app.logger.info(f"Round list: {round_list}")
    return render_template('round.html', game_id=game_id, round_num=round_num, players_names=players_names, round_list=round_list)

@app.route("/history")
def view_history():
    return render_template('history.html')

@app.route("/leaderboard")
def leaderboard():
    return render_template('leaderboard.html')

    

# Runner and Debugger
if __name__ == "__main__":
    app.run(debug=True)