import os
from flask import Flask, request, redirect, render_template, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import plotly.express as px
import pandas as pd

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Set a secret key for session security

# Use SQLite for local development
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///info.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define a password for accessing the site
ACCESS_PASSWORD = "lol"

# Define a model for storing info
class Info(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    number = db.Column(db.Float, nullable=False)  # Change to Float for score
    date = db.Column(db.String(20), nullable=True)
    place = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f"<Info {self.name}: {self.number}, {self.date}, {self.place}>"

# Create the database and tables within the application context
with app.app_context():
    db.create_all()

@app.route('/')
def home():
    if session.get('password_entered'):
        return render_template('home.html')  # Redirect to home page
    else:
        return render_template('login.html', title="Login")

@app.route('/login', methods=['POST'])
def login():
    password = request.form['password']
    if password == ACCESS_PASSWORD:
        session['password_entered'] = True
        return redirect(url_for('home'))  # Redirect to home page after successful login
    else:
        return "Unauthorized: Incorrect password"

@app.route('/logout')
def logout():
    session.pop('password_entered', None)  # Clear session variable upon logout
    return redirect('/')

@app.route('/add_info_form')
def add_info_form():
    return render_template('add_info_form.html', title="Add Players")

@app.route('/add_info', methods=['POST'])
def add_info():
    num_players = int(request.form['num_players'])
    date = request.form['date']  # Get the date
    place = request.form['place']  # Get the place
    total_score = 0.0
    players = []

    for i in range(num_players):
        name_key = f'name{i}'
        number_key = f'number{i}'
        name = request.form.get(name_key)

        # Ensure the name and score are provided
        if not name:
            flash(f'Name is required for player {i + 1}.')
            return redirect(url_for('add_info_form'))

        number_str = request.form.get(number_key)
        if not number_str:
            flash(f'Score is required for player {i + 1}.')
            return redirect(url_for('add_info_form'))

        # Convert score to float
        try:
            number = float(number_str)
        except ValueError:
            flash(f'Score for player {i + 1} must be a valid number.')
            return redirect(url_for('add_info_form'))

        total_score += number
        new_info = Info(name=name, number=number, date=date, place=place)  # Store date and place
        db.session.add(new_info)
        players.append(new_info)

    db.session.commit()
    return render_template('add_info_success.html', title="Add Info", num_players=num_players, players=players)

@app.route('/view_info')
def view_info():
    info_list = Info.query.all()
    return render_template('view_info.html', title="Current Info", info_list=info_list)

@app.route('/edit_info/<int:info_id>', methods=['GET', 'POST'])
def edit_info(info_id):
    info = Info.query.get_or_404(info_id)
    if request.method == 'POST':
        info.number = float(request.form['number'])  # Change to float
        db.session.commit()
        return redirect(url_for('view_info'))
    return render_template('edit_info.html', info=info)

@app.route('/total_score')
def total_score():
    info_list = Info.query.all()
    total_score = sum([info.number for info in info_list])
    return render_template('total_score.html', title="Total Score", total_score=total_score)

@app.route('/separated_scores')
def separated_scores():
    info_list = Info.query.all()
    total_dict = {}
    individual_dict = {}
    for info in info_list:
        if info.name in total_dict:
            total_dict[info.name] += info.number
            individual_dict[info.name].append(info.number)
        else:
            total_dict[info.name] = info.number
            individual_dict[info.name] = [info.number]
    return render_template('separated_scores.html', title="Separated Scores", total_dict=total_dict, individual_dict=individual_dict)

@app.route('/graph', methods=['GET', 'POST'])
def graph():
    if request.method == 'POST':
        selected_players = request.form.getlist('players')
        date = request.form.get('date')  # Optional date
        place = request.form.get('place')  # Optional place

        # Query the database for selected players
        info_list = Info.query.filter(Info.name.in_(selected_players)).all()

        # Prepare data for plotting
        data = {
            'names': [info.name for info in info_list],
            'scores': [info.number for info in info_list],
            'dates': [info.date for info in info_list],
            'places': [info.place for info in info_list]
        }

        # Create a DataFrame from the data
        df = pd.DataFrame(data)

        # Create a scatter plot with a line using Plotly
        fig = px.line(df, x='names', y='scores', title='Player Scores', labels={'names': 'Player Name', 'scores': 'Score'})

        # Optionally add annotations for date and place
        if date:
            fig.add_annotation(text=f'Date: {date}', xref="paper", yref="paper", x=0.5, y=1.1, showarrow=False)
        if place:
            fig.add_annotation(text=f'Place: {place}', xref="paper", yref="paper", x=0.5, y=1.15, showarrow=False)

        # Render the graph as HTML
        graph_html = fig.to_html(full_html=False)

        return render_template('graph.html', graph_html=graph_html)  # Render the graph in a new template

    # For GET request, display the selection form with all players
    players = Info.query.distinct(Info.name).all()  # Get unique player names
    return render_template('select_graph.html', players=players)  # Render the selection form

if __name__ == '__main__':
    app.run(debug=True)
