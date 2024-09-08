from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import datetime
from flask_login import UserMixin, current_user, login_user, logout_user, LoginManager
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select, asc
from sqlalchemy.orm import DeclarativeBase
from werkzeug.security import generate_password_hash, check_password_hash
import stripe
import os

app = Flask(__name__,
            static_url_path='/static',
            static_folder='static')

# Configuration
app.config["SECRET_KEY"] = os.environ.get('SECRET_KEY')
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///waggy.db")
app.config["STRIPE_SECRET_KEY"] = os.environ.get('STRIPE_SECRET_KEY')
app.config["STRIPE_PUBLIC_KEY"] = os.environ.get('STRIPE_PUBLIC_KEY')
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
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self):
        return f'<User {self.name}>'

    def get_id(self):
        return str(self.id)

    @property
    def is_user_active(self):
        """Returns True if the user account is active."""
        return self.is_active


class Cart(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    foodies_id = db.Column(db.Integer, db.ForeignKey('foodies.id'))
    clothing_id = db.Column(db.Integer, db.ForeignKey('clothing.id'))


class Foodies(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_file = db.Column(db.String(255), nullable=True)  # Changed from image_url to image_file
    stock = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return f'<Foodies {self.name}>'


class Clothing(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_file = db.Column(db.String(255), nullable=True)  # Changed from image_url to image_file
    stock = db.Column(db.Integer, nullable=False, default=0)
    rating = db.Column(db.Integer, nullable=True)

    def __repr__(self):
        return f'<Clothing {self.name}>'


with app.app_context():
    db.create_all()
    foodies = Foodies.query.all()
    print(foodies)
    print(Clothing.query.all())
    print(Cart.query.all())

    # # Create sample foodies
    # foodies1 = Foodies(name="Fresh Kisses", description="kisses.", price=9.99, image_file="item9.jpg",
    #                    stock=50)
    # foodies2 = Foodies(name="Pulsitos", description="chocolates", price=5.99,
    #                    image_file="item11.jpg", stock=30)
    #
    # # Create sample clothing
    # clothing1 = Clothing(name="Black T", description="Comfortable black T-shirt.", price=15.99,
    #                      image_file="item4.jpg", stock=100, rating=5)
    # clothing2 = Clothing(name="Gray T", description="Stylish gray T.", price=39.99, image_file="item3.jpg", stock=75,
    #                      rating=8)
    #
    # # Add foodies and clothing to the database
    # db.session.add(foodies1)
    # db.session.add(foodies2)
    # db.session.add(clothing1)
    # db.session.add(clothing2)
    # db.session.commit()



@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)


@app.route('/')
def index():
    current_year = datetime.datetime.now().year

    foodies_data = Foodies.query.all()
    clothing_items = Clothing.query.all()

    cart_items = []
    total_price = 0

    if current_user.is_authenticated:
        cart_items = Cart.query.filter_by(user_id=current_user.id).all()
        total_price = sum(item.price * item.quantity for item in cart_items)

    return render_template("index.html", current_year=current_year, foodies=foodies_data,
                           clothing_items=clothing_items,
                           cart_items=cart_items, total_price=total_price,
                           current_user=current_user)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password, method="scrypt", salt_length=8)

        existing_user = User.query.filter_by(email=email).first()
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

        user = User.query.filter_by(email=email).first()
        if user is None:
            flash('Invalid email.')
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, password):
            flash('Invalid password.')
            return redirect(url_for('login'))
        else:
            login_user(user)  # Pass the user object, not current_user
            return redirect(url_for('index'))

    return render_template("login.html", current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/single-product/<int:product_id>')
def single_product(product_id):
    foodie = Foodies.query.get(product_id)
    clothing = Clothing.query.get(product_id)

    if foodie:
        return render_template('single-product.html', product=foodie, category='foodies')
    elif clothing:
        return render_template('single-product.html', product=clothing, category='clothing')
    else:
        return "Product not found", 404



@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if not current_user.is_authenticated:
        flash("You need to log in to add items to the cart.")
        return redirect(url_for('login'))

    product_id = int(request.form.get('product_id'))
    quantity = int(request.form.get('quantity', 1))

    # Query for foodies and clothing items
    foodies_item = Foodies.query.get(product_id)
    clothing_item = Clothing.query.get(product_id)

    if foodies_item:
        cart_item = Cart(user_id=current_user.id, foodies_id=foodies_item.id, quantity=quantity,
                         price=foodies_item.price, name=foodies_item.name)
    elif clothing_item:
        cart_item = Cart(user_id=current_user.id, clothing_id=clothing_item.id, quantity=quantity,
                         price=clothing_item.price, name=clothing_item.name)
    else:
        flash("Product not found.")
        return redirect(url_for('index'))

    # Add cart item to the database
    db.session.add(cart_item)
    db.session.commit()

    # Redirect to the index page
    return redirect(url_for('index'))



@app.route('/cart')
def show_cart():
    cart_items = []
    total_price = 0


    if current_user.is_authenticated:
        cart_items = Cart.query.filter_by(user_id=current_user.id).all()
        total_price = sum(item.price * item.quantity for item in cart_items)

    # Debug print to confirm data retrieval
    print(f"Cart items: {cart_items}")

    return render_template('cart.html', cart_items=cart_items, total_price=total_price, current_user=current_user)


@app.route('/checkout', methods=["GET"])
def create_checkout_session():
    try:
        cart_items = Cart.query.filter_by(user_id=current_user.id).all()
        line_items = []
        for item in cart_items:
            if item.foodies_id:
                product = Foodies.query.get(item.foodies_id)
            else:
                product = Clothing.query.get(item.clothing_id)
            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': product.name,
                    },
                    'unit_amount': int(product.price * 100),
                },
                'quantity': item.quantity,
            })

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=app.config["DOMAIN"] + '/success.html?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=app.config["DOMAIN"] + '/cancel.html',
        )

        return redirect(session.url, code=303)

    except Exception as e:
        print(f"Error during checkout: {e}")
        return jsonify(error=str(e)), 500


@app.route('/session-status', methods=['GET'])
def session_status():
    session_id = request.args.get('session_id')
    session = stripe.checkout.Session.retrieve(session_id)

    return jsonify(status=session.status, customer_email=session.customer_email)


@app.route('/success.html')
def success():
    session_id = request.args.get('session_id')

    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            return render_template('success.html', session=session)
        except stripe.error.InvalidRequestError as e:
            return jsonify(error=str(e)), 400
    else:
        return "Session ID is missing", 400


@app.route('/cancel.html')
def cancel():
    return render_template('cancel.html')


if __name__ == '__main__':
    app.run(debug=True)
