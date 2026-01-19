from flask import Flask, flash, redirect, render_template, request, url_for, make_response
from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime
from sqlalchemy import func

app = Flask(__name__)

# In production, set the SECRET_KEY env var; for development generate one.
app.config['SECRET_KEY'] = "my-secret-key"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False,default=date.today)

with app.app_context():
    db.create_all()

CATEGORIES = ['Food', 'Transport', 'School', 'Entertainment', 'Other']

@app.route("/")
@app.route("/index")
def index():
	return render_template("index.html",
							categories=CATEGORIES,
							expenses=Expense.query.order_by(Expense.date.desc()).all()
                           )

@app.route('/add', methods=['POST'])
def add():
    description = (request.form.get('description') or "").strip()
    amount = (request.form.get('amount') or "").strip()
    category = (request.form.get('category') or "").strip()
    date_str = (request.form.get('date') or "").strip()

    if not description or not amount or not category:
        flash("Please fill description, amount, and category", "error")
        return redirect(url_for('index'))

    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except ValueError:
        flash("Amount must be a positive number", "error")
        return redirect(url_for('index'))

    try:
        d = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else date.today()

    except ValueError:
        d = date.today()
    
    e = Expense(description=description, amount=amount, category=category, date=d)
    db.session.add(e)
    db.session.commit()

    flash("Expense added successfully!", "success")
    return redirect(url_for('index'))
if __name__ == '__main__':
	app.run(debug=True)
