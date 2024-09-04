from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import datetime
from flask_login import UserMixin, current_user, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager
import stripe
import os

app = Flask(__name__,
            static_url_path='/static',
            static_folder='static')

# Configuration
app.config["SECRET_KEY"] = os.environ.get('SECRET_KEY')
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///waggy.db")
app.config[
    "STRIPE_SECRET_KEY"] = os.environ.get('STRIPE_SECRET_KEY')
app.config[
    "STRIPE_PUBLIC_KEY"] = os.environ.get('STRIPE_PUBLIC_KEY')
app.config["DOMAIN"] = 'http://localhost:5000'

stripe.api_key = app.config["STRIPE_SECRET_KEY"]

login_manager = LoginManager()
login_manager.init_app(app)


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
db.init_app(app)



class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)


with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)


@app.route('/')
def index():
    current_year = datetime.datetime.now().year
    return render_template("index.html", current_year=current_year)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password, method="scrypt", salt_length=8)

        result = db.session.execute(db.select(User).where(User.email == email))
        existing_user = result.scalar()
        if existing_user:
            flash("You are already registered!", "Please login")
            return redirect(url_for("login"))
        else:
            new_user = User(
                name=name,
                email=email,
                password=hashed_password
            )
            db.session.add(new_user)
            db.session.commit()
            flash("You have successfully registered!", "Please login")
            return redirect(url_for("login"))

    return render_template("register.html", current_user=current_user)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        result = db.session.execute(db.select(User).where(User.email == email))
        user = result.scalar()
        if user is None:
            flash('Invalid email.')
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, password):
            flash('Invalid password.')
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('index'))

    return render_template("login.html", current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


# STRIPE API INTEGRATION
@app.route('/checkout', methods=["GET", "POST"])
def create_checkout_session():
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price': 'price_1Pv0V7G4K28d83uRzw6z6dZG',  # Replace with your actual Price ID
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url=app.config["DOMAIN"] + '/success.html?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=app.config["DOMAIN"] + '/cancel.html',
        )
        # Redirect to the Stripe checkout session URL
        return redirect(session.url, code=303)
    except Exception as e:
        return jsonify(error=str(e)), 500

    # The line below will render the checkout page, but usually, it's better to redirect the user directly to the Stripe
    # checkout session.


@app.route('/session-status', methods=['GET'])
def session_status():
    session_id = request.args.get('session_id')
    session = stripe.checkout.Session.retrieve(session_id)

    return jsonify(status=session.status, customer_email=session.customer_email)


@app.route('/success.html')
def success():
    session_id = request.args.get('session_id')
    return render_template('success.html', session_id=session_id)


@app.route('/cancel.html')
def cancel():
    return render_template('cancel.html')


@app.route('/charge', methods=['POST'])
def charge():
    data = request.get_json()
    token_id = data.get('tokenId')

    try:
        charge = stripe.Charge.create(
            amount=5000,  # Amount in cents
            currency='usd',
            description='Example charge',
            source=token_id
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)})


if __name__ == '__main__':
    app.run(debug=True)
