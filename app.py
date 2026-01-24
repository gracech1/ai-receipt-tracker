from flask import Flask, flash, redirect, render_template, request, url_for, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime
from sqlalchemy import func
from dotenv import load_dotenv
from tabscanner import process_receipt
import os
import tempfile
import time

load_dotenv()

app = Flask(__name__)

# secret key variable
app.config['SECRET_KEY'] = "my-secret-key"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# makes database
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False,default=date.today)


with app.app_context():
    db.create_all()

CATEGORIES = ['Food', 'Transport', 'Utilities', 'Entertainment', 'Other']

# helper to parse date
def parse_date_or_none(s: str):
    if not s:
        return None
    try:
        return datetime.strptime(s, '%Y-%m-%d').date()
    except ValueError:
        return None

# home page
@app.route('/')
def index():
    # read query string
    start_str = (request.args.get("start") or "").strip()
    end_str = (request.args.get("end") or "").strip()
    selected_category = (request.args.get("category") or "").strip()

    # parsing
    start_date = parse_date_or_none(start_str)
    end_date = parse_date_or_none(end_str)

    if start_date and end_date and end_date < start_date:
        flash("End date cannot be before start date", "error")
        start_date = end_date = None
        start_str = end_str = ""

    q = Expense.query
    if start_date:
        q = q.filter(Expense.date >= start_date)
    if end_date:
        q = q.filter(Expense.date <= end_date)
    if selected_category:
        q = q.filter(Expense.category == selected_category)

    expenses = q.order_by(Expense.date.desc(), Expense.id.desc()).all()
    total = round(sum(e.amount for e in expenses), 2)

    # pie chart
    cat_q = db.session.query(Expense.category, func.sum(Expense.amount))
    if start_date:
        cat_q = cat_q.filter(Expense.date >= start_date)
    if end_date: 
        cat_q = cat_q.filter(Expense.date <= end_date)
    if selected_category:
        cat_q = cat_q.filter(Expense.category == selected_category)

    cat_row = cat_q.group_by(Expense.category).all()
    print(cat_row)
    cat_labels = [c for c, _ in cat_row]
    cat_values = [round(float(s or 0), 2) for _, s in cat_row]
    print(cat_values)

    # day chart
    day_q = db.session.query(Expense.date, func.sum(Expense.amount))
    if start_date:
        day_q = day_q.filter(Expense.date >= start_date)
    if end_date: 
        day_q = day_q.filter(Expense.date <= end_date)
    if selected_category:
        day_q = day_q.filter(Expense.category == selected_category)

    day_row = day_q.group_by(Expense.date).all()
    print(day_row)
    day_labels = [d.isoformat() for d, _ in day_row]
    day_values = [round(float(s or 0), 2) for _, s in day_row]
    print(day_values)

    return render_template('index.html',
                            categories=CATEGORIES, 
                            today=date.today().isoformat(),
                            expenses=expenses, 
                            total=total,
                            start_str=start_str,
                            end_str=end_str,
                            selected_category=selected_category,
                            cat_labels=cat_labels,
                            cat_values=cat_values,
                            day_labels=day_labels,
                            day_values=day_values,
                            )

@app.route('/add', methods=['POST'])
def add():
    description = (request.form.get('description') or "").strip()
    amount = (request.form.get('amount') or "").strip()
    category = (request.form.get('category') or "").strip()
    date_str = (request.form.get('date') or "").strip()

    # validation
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
    
    # adding entry
    e = Expense(description=description, amount=amount, category=category, date=d)
    db.session.add(e)
    db.session.commit()

    flash("Expense added successfully!", "success")
    return redirect(url_for('index'))

# delete entry
@app.route('/delete/<int:expense_id>', methods=['POST'])
def delete(expense_id):
    e = Expense.query.get_or_404(expense_id)
    db.session.delete(e)
    db.session.commit()
    flash("Expense deleted successfully!", "success")
    return redirect(url_for('index'))

# tabscanner API
@app.route("/upload", methods=["POST"])
def upload():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "No file uploaded"}), 400
    
    # save to temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(f.filename)[1])
    f.save(tmp.name)
    tmp.close()

    # process receipt
    result = process_receipt(tmp.name)
    if not result:
        return jsonify({"error": "Failed to process receipt"}), 500
    
    os.remove(tmp.name)

    establishment = result["establishment"]
    date = result["date"]
    total = result["total"]

    # Tabscanner response
    return jsonify({
        "establishment": establishment,
        "date": date,
        "total": total
    })

if __name__ == '__main__':
    app.run(debug=True)