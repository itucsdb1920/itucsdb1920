from datetime import datetime
from passlib.hash import pbkdf2_sha256 as hasher

from flask import abort, current_app, render_template, request, redirect, url_for, flash
from book import Book
from forms import BookEditForm, LoginForm, RegistrationForm, ReviewForm, ProfileEditForm
from user import User
from review import Review
from flask_login import login_user, logout_user, current_user, login_required

def home_page():
    today = datetime.today()
    day_name = today.strftime("%A")
    return render_template("home.html", day=day_name)

def books_page():
    db = current_app.config["db"]
    if request.method == "GET":
        books = db.get_books()
        return render_template("books.html", books=books)

def book_page(book_id):
    db = current_app.config["db"]
    book = db.get_book(book_id)
    reviews, user_ids = db.get_reviews(book_id)
    if book is None:
        abort(404)
    form = ReviewForm()
    if form.validate_on_submit():
        score = form.data["score"]
        comment = form.data["comment"]
        author = db.get_user_id(current_user.username)
        review = Review(author=author, book=book_id, score=score, comment=comment)
        review_id = db.add_review(review)
        review.id = review_id
        return redirect(url_for("book_page", book_id = book_id))
    return render_template("book.html", book=book, form=form, reviews=reviews, user_ids=user_ids)
	
@login_required
def book_add_page():
    if not current_user.is_admin:
        abort(401)
    form = BookEditForm()
    if form.validate_on_submit():
        title = form.data["title"]
        author = form.data["author"]
        year = form.data["year"]
        genre = form.data["genre"]
        pageNumber = form.data["pageNumber"]
        cover = form.data["cover"]
        book = Book(title=title, author=author, year=year, genre=genre, pageNumber=pageNumber, cover=cover)
        db = current_app.config["db"]
        book_id = db.add_book(book)
        return redirect(url_for("book_page", book_id=book_id))
    return render_template("book_edit.html", form=form)
	
@login_required
def book_edit_page(book_id):
    db = current_app.config["db"]
    book = db.get_book(book_id)
    form = BookEditForm()
    if form.validate_on_submit():
        title = form.data["title"]
        author = form.data["author"]
        year = form.data["year"]
        genre = form.data["genre"]
        pageNumber = form.data["pageNumber"]
        cover = form.data["cover"]
        book = Book(title=title, author=author, year=year, genre=genre, pageNumber=pageNumber, cover=cover)
        db.update_book(book_id, book)
        return redirect(url_for("book_page", book_id=book_id))
    form.title.data = book.title
    form.author.data = book.author if book.author else ""
    form.year.data = book.year if book.year else ""
    form.genre.data = book.genre if book.genre else ""
    form.pageNumber.data = book.pageNumber if book.pageNumber else ""
    form.cover.data = book.cover if book.cover else ""
    return render_template("book_edit.html", form=form)

def validate_book_form(form):
    form.data = {}
    form.errors = {}

    form_title = form.get("title", "").strip()
    if len(form_title) == 0:
        form.errors["title"] = "Title can not be blank."
    else:
        form.data["title"] = form_title

    form_year = form.get("year")
    if not form_year:
        form.data["year"] = None
    elif not form_year.isdigit():
        form.errors["year"] = "Year must consist of digits only."
    else:
        year = int(form_year)
        if (year < 0                       ) or (year > datetime.now().year):
            form.errors["year"] = "Year not in valid range."
        else:
            form.data["year"] = year

    return len(form.errors) == 0

def registration_page():
    db = current_app.config["db"]
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.data["username"]
        email = form.data["email"]
        user = db.get_user_by_username(username)
        if user is None:
            user = db.get_user_by_email(email)
            if user is None:
                password = hasher.hash(form.data["password"])
                user = User(username, email=email, password=password)
                db.add_user(user)
                user = db.get_user_by_username(username)
                login_user(user)
                flash("Registration successful.")
                next_page = request.args.get("next", url_for("home_page"))
                return redirect(next_page)
            flash("E-mail is already in use.")
            return render_template("register.html", form=form)
        flash("Username already exists.")
    return render_template("register.html", form=form)
    	
def login_page():
    db = current_app.config["db"]
    form = LoginForm()
    if form.validate_on_submit():
        username = form.data["username"]
        user = db.get_user_by_username(username)
        remember = form.data["remember"]
        if user is not None:
            password = form.data["password"]
            if hasher.verify(password, user.password):
                login_user(user, remember=remember)
                flash("You have logged in.")
                next_page = request.args.get("next", url_for("home_page"))
                return redirect(next_page)
        flash("Invalid credentials.")
    return render_template("login.html", form=form)

def logout_page():
    logout_user()
    flash("You have logged out.")
    return redirect(url_for("home_page"))

@login_required
def delete_review(review_id):
    db = current_app.config["db"]
    review_ = db.get_review(review_id)
    if current_user.id == review_.author or current_user.is_admin:
        db.delete_review(review_id)
    return redirect(url_for("book_page", book_id=review_.book))

@login_required
def delete_book(book_id):
    db = current_app.config["db"]
    if current_user.is_admin:
        db.delete_book(int(book_id))
    return redirect(url_for("books_page"))

def profile_page(user_id=None):
    db = current_app.config["db"]
    user = db.get_user_by_id(user_id)
    reviews, book_names = db.get_reviews_by_user(user.id)
    return render_template("profile.html", user=user, reviews=reviews, books=book_names, user_id=user_id)

@login_required
def profile_edit_page(user_id):
    db = current_app.config["db"]
    user = db.get_user_by_id(user_id)
    form = ProfileEditForm()
    if form.validate_on_submit():
        username = form.data["username"]
        email = form.data["email"]
        password = hasher.hash(form.data["new_password"])
        new_user = User(username=username, email=email, password=password)
        if hasher.verify(form.data["old_password"], user.password):
            db.update_user(user_id, new_user)
            flash("User information updated successfully.")
            return redirect(url_for("profile_page", user_id=user_id))
        else:
            flash("Old password is wrong.")
    form.username.data = user.username
    form.email.data = user.email
    return render_template("register.html", form=form)

@login_required
def delete_profile(user_id):
    db = current_app.config["db"]
    if current_user.is_admin or current_user.id == user_id:
        db.delete_user(int(user_id))
    return redirect(url_for("home_page"))