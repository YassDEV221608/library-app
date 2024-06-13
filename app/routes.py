from flask import send_file, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from .extensions import bcrypt, login, books_collection, fs
from app.models import User
from app.forms import RegistrationForm, LoginForm
from .extensions import db, neo4j_conn
from math import ceil
from run import app
from bson.objectid import ObjectId
import re
from .models import User
from flask_login import LoginManager
from datetime import datetime, timedelta


login_manager = LoginManager(app)



@login_manager.user_loader
def load_user(user_id):
    return User.objects(id=user_id).first()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.objects(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username and password:
            existing_user = User.objects(username=username).first()
            if existing_user:
                flash('Username already taken. Please choose a different one.', 'danger')
            else:
                hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
                user = User(username=username, password_hash=hashed_password, is_admin=False)
                user.save()
                flash('Your account has been created! You are now able to log in', 'success')
                return redirect(url_for('login'))
        else:
            flash('Invalid input. Please provide a username and password.', 'danger')
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('login'))

@app.route('/delete_user/<user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        flash('You do not have permission to delete users.', 'danger')
        return redirect(url_for('index'))

    try:
        user = User.objects(id=user_id).first()
        if user:
            loaned_books = books_collection.find({'loaned_to': ObjectId(user_id)})

            # Delete loaned books
            for book in loaned_books:
                books_collection.delete_one({'_id': book['_id']})
                neo4j_conn.query(
                    "MATCH (b:Book {title: $title, author: $author}) DELETE b",
                    parameters={"title": book['title'], "author": book['author']}
                )

            user.delete()
            flash('User deleted successfully.', 'success')
        else:
            flash('User not found.', 'danger')
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'danger')

    return redirect(url_for('search_users'))


@app.route('/search_users', methods=['GET', 'POST'])
@login_required
def search_users():
    if not current_user.is_admin:
        flash('You do not have access to this page.', 'danger')
        return redirect(url_for('index'))

    search_query = request.args.get('search_query', '')
    page = request.args.get('page', 1, type=int)
    per_page = 5

    if request.method == 'POST':
        search_query = request.form['search_query']

    users = User.objects(username__icontains=search_query, is_admin=False).skip((page - 1) * per_page).limit(per_page)
    total_users = User.objects(username__icontains=search_query, is_admin=False).count()
    total_pages = (total_users + per_page - 1) // per_page

    return render_template('search_users.html', users=users, search_query=search_query, page=page, total_pages=total_pages)





@app.route('/recommendations/<book_title>')
@login_required
def recommendations(book_title):
    search_query = request.args.get('search_query', '')  # Get the 'search_query' query parameter or default to ''
    page = request.args.get('page', 1, type=int)  # Get the 'page' query parameter or default to 1
    per_page = 5  # Define how many books to display per page

    # Find the book in MongoDB
    book = books_collection.find_one({"title": {"$regex": re.compile(book_title, re.IGNORECASE)}})
    if not book:
        return f"Book titled '{book_title}' not found in the library."

    author_name = book.get("author", "")
    book_title_lower = book_title.lower()

    try:
        # Retrieve recommended books from Neo4j
        results = neo4j_conn.query(
            """
            MATCH (b:Book)<-[:WRITTEN_BY]-(a:Author {name: $author_name})
            WHERE toLower(b.title) <> toLower($book_title_lower)
            RETURN b.title AS title, b.author AS author, b.pdf_file_id AS pdf_file_id
            """,
            parameters={"author_name": author_name, "book_title_lower": book_title_lower}
        )

        # Extract recommended books from Neo4j results
        recommended_books = [
            {"title": record["title"], "author": record["author"], "pdf_file_id": record["pdf_file_id"]}
            for record in results
        ]

        # Pagination logic
        total_books = len(recommended_books)
        total_pages = (total_books + per_page - 1) // per_page
        start = (page - 1) * per_page
        end = start + per_page
        recommended_books = recommended_books[start:end]

    except Exception as e:
        print(e)
        flash(f"An error occurred while fetching recommendations: {e}")
        recommended_books = []
        total_pages = 1

    return render_template(
        'recommendations.html',
        book_title=book_title,
        recommended_books=recommended_books,
        search_query=search_query,
        page=page,
        total_pages=total_pages
    )






@app.route('/')
def index():
    if current_user.is_authenticated:
        return render_template('index.html')
    return login()


@app.route('/add_book', methods=['GET', 'POST'])
@login_required
def add_book():
    if request.method == 'POST':
        title = request.form['title']
        author_name = request.form['author']  # Assuming author's name is inputted directly
        
        # Check if a book with the same title already exists in MongoDB
        existing_book_mongo = books_collection.find_one({"title": {"$regex": re.compile(f"^{title}$", re.IGNORECASE)}})
        if existing_book_mongo:
            flash(f"A book with the title '{title}' already exists in the library.")
            return redirect(request.url)

        # Check if a book with the same title already exists in Neo4j
        existing_book_neo4j = neo4j_conn.query(
            "MATCH (b:Book {title: $title}) RETURN b",
            parameters={"title": title}
        )
        if existing_book_neo4j:
            flash(f"A book with the title '{title}' already exists in the library.")
            return redirect(request.url)

        try:
            # Create or find author in Neo4j
            neo4j_conn.query(
                "MERGE (a:Author {name: $name})",
                parameters={"name": author_name}
            )

            # Create book node in Neo4j and establish relationship with author
            neo4j_conn.query(
                """
                CREATE (b:Book {title: $title})
                WITH b
                MATCH (a:Author {name: $author_name})
                CREATE (a)-[:WRITTEN_BY]->(b)
                """,
                parameters={"title": title, "author_name": author_name}
            )
            flash(f"Book '{title}' added successfully.")
        except Exception as e:
            flash(f"An error occurred while adding book '{title}' to Neo4j: {e}")

        # Prepare book data for MongoDB
        copies = int(request.form['copies'])
        cover_image = request.form['cover_image']

        # Save book data in MongoDB
        if 'pdf' in request.files:
            pdf = request.files['pdf']
            if pdf.filename.lower().endswith('.pdf'):
                pdf_file_id = fs.put(pdf.read(), filename=pdf.filename)
                book_data = {
                    "title": title,
                    "author": author_name,  # Store author's name for easier querying in MongoDB
                    "copies": copies,
                    "pdf_file_id": pdf_file_id,
                    "cover_image": cover_image,
                    "loan_status": "available",
                    "loaned_to": None
                }
                books_collection.insert_one(book_data)
                flash(f"Book '{title}' added successfully.")
            else:
                flash('Invalid file format. Only PDF files are allowed.')
                return redirect(request.url)
        else:
            flash('No PDF file uploaded.')
            return redirect(request.url)

        return redirect(url_for('index'))

    return render_template('add_book.html')





@app.route('/delete_book/<book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    if not current_user.is_admin:
        flash('You do not have permission to delete books.', 'danger')
        return redirect(url_for('index'))

    try:
        book_id = ObjectId(book_id)
    except:
        flash("Invalid book ID.")
        return redirect(url_for('index'))
    
    # Get the book from MongoDB
    book = books_collection.find_one({"_id": book_id})
    if not book:
        flash(f"No book found with ID {book_id}.")
        return redirect(url_for('index'))

    # Delete the book from MongoDB
    result = books_collection.delete_one({"_id": book_id})
    if result.deleted_count == 0:
        flash(f"No book found with ID {book_id}.")
        return redirect(url_for('index'))

    # Delete the book from Neo4j
    try:
        neo4j_conn.query(
            "MATCH (b:Book {title: $title}) DETACH DELETE b",
            parameters={"title": book['title']}
        )
        flash(f"Book '{book['title']}' deleted successfully from Neo4j.")
    except Exception as e:
        flash(f"An error occurred while deleting book '{book['title']}' from Neo4j: {e}")

    flash("Book deleted successfully.")
    return redirect(url_for('layout'))

@app.route('/search_books', methods=['GET', 'POST'])
@login_required
def search_books():
    search_query = request.args.get('search_query', '')
    page = request.args.get('page', 1, type=int)
    per_page = 5
    if request.method == 'POST':
        search_query = request.form['search_query']
    
    books = books_collection.find({"title": {"$regex": search_query, "$options": "i"}}).skip((page - 1) * per_page).limit(per_page)
    total_books = books_collection.count_documents({"title": {"$regex": search_query, "$options": "i"}})
    total_pages = (total_books + per_page - 1) // per_page

    return render_template('search_books.html', books=books, search_query=search_query, page=page, total_pages=total_pages)

@app.route('/view_books')
@login_required
def view_books():
    page = request.args.get('page', 1, type=int)
    per_page = 5
    total_books = books_collection.count_documents({})
    books = books_collection.find().skip((page - 1) * per_page).limit(per_page)
    total_pages = (total_books + per_page - 1) // per_page
   

    return render_template('view_books.html', books=books, page=page, total_pages=total_pages)

@app.route('/download/<book_id>')
@login_required
def download(book_id):
    try:
        book_id = ObjectId(book_id)
    except:
        flash('Invalid book ID.')
        return redirect(url_for('index'))

    book = books_collection.find_one({"_id": book_id})
    if book and book.get("pdf_file_id"):
        pdf_file = fs.get(book["pdf_file_id"])
        response = send_file(pdf_file, mimetype='application/pdf')
        response.headers['Content-Disposition'] = f'inline; filename="{book["title"]}.pdf"'
        return response
    else:
        flash('PDF file not available for this book.')
        return  render_template('layout.html')

@app.route('/loan/<book_id>', methods=['POST'])
@login_required
def loan_book(book_id):
    if not current_user.is_admin:
        book = books_collection.find_one({'_id': ObjectId(book_id)})
        if book:
            copies_available = book.get('copies', 0)
            if copies_available > 0:
                books_collection.update_one(
                    {'_id': ObjectId(book_id)},
                    {
                        '$set': {
                            'loan_status': 'loaned',
                            'loaned_to': current_user.id
                        },
                        '$inc': {'copies': -1}
                    }
                )
                flash('Book successfully loaned!', 'success')
            else:
                flash('No copies available for loan.', 'danger')
        else:
            flash('Book not found.', 'danger')
    else:
        flash('Admins cannot loan books.', 'danger')
    return  render_template('layout.html')

@app.route('/return/<book_id>', methods=['POST'])
@login_required
def return_book(book_id):
    book = books_collection.find_one({'_id': ObjectId(book_id)})
    if book and book['loan_status'] == 'loaned' and book['loaned_to'] == current_user.id:
        books_collection.update_one(
            {'_id': ObjectId(book_id)},
            {
                '$set': {
                    'loan_status': 'available',
                    'loaned_to': None
                },
                '$inc': {'copies': 1}
            }
        )
        flash('Book successfully returned!', 'success')
    else:
        flash('You cannot return this book.', 'danger')
    return  render_template('layout.html')

@app.route('/admin_search_loaners', methods=['GET', 'POST'])
@login_required
def admin_search_loaners():
    if not current_user.is_admin:
        flash('You do not have access to this page.', 'danger')
        return redirect(url_for('index'))

    search_query = request.args.get('search_query', '')
    page = request.args.get('page', 1, type=int)
    per_page = 5

    if request.method == 'POST':
        search_query = request.form['search_query']

    # Get users who have loaned books
    loaned_users = list(books_collection.distinct('loaned_to'))

    # Filter users by search query
    users = User.objects(username__icontains=search_query, id__in=loaned_users).skip((page - 1) * per_page).limit(per_page)
    
    total_users = User.objects(username__icontains=search_query, id__in=loaned_users).count()
    total_pages = (total_users + per_page - 1) // per_page

    return render_template('admin_search_loaners.html', users=users, search_query=search_query, page=page, total_pages=total_pages, books_collection=books_collection)



@app.route('/view_loaned_books')
@login_required
def view_loaned_books():
    search_query = request.args.get('search_query', '')  # Get the 'search_query' query parameter or default to ''
    page = request.args.get('page', 1, type=int)  # Get the 'page' query parameter or default to 1
    per_page = 5  # Define how many books to display per page

    # Determine the query based on user role
    if current_user.is_admin:
        query = {'loan_status': 'loaned'}
    else:
        query = {'loan_status': 'loaned', 'loaned_to': current_user.id}

    # Get loaned books based on the query
    books = books_collection.find(query).skip((page - 1) * per_page).limit(per_page)
    
    # Get the total number of loaned books for pagination
    total_books = books_collection.count_documents(query)
    total_pages = (total_books + per_page - 1) // per_page

    return render_template('view_loaned_books.html', books=books, page=page, total_pages=total_pages)




@app.route('/get_all_books', methods=['GET'])
@login_required
def get_all_books():
    results = neo4j_conn.query(
        """
        MATCH (b:Book)
        RETURN b.title AS title, b.author AS author, b.copies AS copies, b.cover_image AS cover_image, b.pdf_file_id AS pdf_file_id
        """
    )
    all_books = [
        {
            "title": record["title"],
            "author": record["author"],
            "copies": record["copies"],
            "cover_image": record["cover_image"],
            "pdf_file_id": record["pdf_file_id"]
        }
        for record in results
    ]
    return jsonify(all_books)


# Route to update the number of copies of a book
@app.route('/update_book_copies/<book_id>', methods=['GET', 'POST'])
@login_required
def update_book_copies(book_id):
    if not current_user.is_admin:
        flash('You do not have permission to update book copies.', 'danger')
        return redirect(url_for('index'))

    book = books_collection.find_one({'_id': ObjectId(book_id)})
    if not book:
        flash('Book not found.', 'danger')
        return redirect(url_for('view_books'))

    if request.method == 'POST':
        new_copies = request.form.get('copies', type=int)
        if new_copies is not None and new_copies >= 0:
            books_collection.update_one(
                {'_id': ObjectId(book_id)},
                {'$set': {'copies': new_copies}}
            )
            neo4j_conn.query(
                "MATCH (b:Book {title: $title, author: $author}) SET b.copies = $copies",
                parameters={"title": book['title'], "author": book['author'], "copies": new_copies}
            )
            flash(f"Number of copies for '{book['title']}' updated to {new_copies}.", 'success')
            return redirect(url_for('view_books'))
        else:
            flash('Invalid number of copies.', 'danger')

    return render_template('update_book_copies.html', book=book)
