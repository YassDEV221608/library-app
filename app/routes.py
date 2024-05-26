from flask import render_template, request, redirect, url_for, flash
from app import app
import pymongo
import gridfs
from datetime import datetime, timedelta

# Connect to MongoDB
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["library"]
books_collection = db["books"]
issued_books_collection = db["issued_books"]
fs = gridfs.GridFS(db)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_book', methods=['GET', 'POST'])
def add_book():
    if request.method == 'POST':
        book_id = int(request.form['book_id'])
        title = request.form['title']
        author = request.form['author']
        copies = int(request.form['copies'])
        pdf_file = request.files.get('pdf_file')
        
        book = {
            "_id": book_id,
            "title": title,
            "author": author,
            "copies": copies,
            "pdf_file_id": None
        }
        
        if pdf_file:
            pdf_file_id = fs.put(pdf_file, filename=f"{title}.pdf")
            book["pdf_file_id"] = pdf_file_id

        books_collection.insert_one(book)
        flash(f"Book '{title}' added successfully.")
        return redirect(url_for('index'))
    
    return render_template('add_book.html')

@app.route('/delete_book', methods=['GET', 'POST'])
def delete_book():
    if request.method == 'POST':
        book_id = int(request.form['book_id'])
        book = books_collection.find_one({"_id": book_id})
        if book and book.get("pdf_file_id"):
            fs.delete(book["pdf_file_id"])
        
        result = books_collection.delete_one({"_id": book_id})
        if result.deleted_count > 0:
            flash(f"Book with ID {book_id} deleted successfully.")
        else:
            flash(f"No book found with ID {book_id}.")
        return redirect(url_for('index'))
    
    return render_template('delete_book.html')

@app.route('/view_books')
def view_books():
    books = books_collection.find()
    return render_template('view_books.html', books=books)

@app.route('/issue_book', methods=['GET', 'POST'])
def issue_book():
    if request.method == 'POST':
        book_id = int(request.form['book_id'])
        user_id = request.form['user_id']
        days = int(request.form['days'])
        
        book = books_collection.find_one({"_id": book_id})
        if book and book['copies'] > 0:
            due_date = datetime.now() + timedelta(days=days)
            issued_book = {
                "book_id": book_id,
                "user_id": user_id,
                "issue_date": datetime.now(),
                "due_date": due_date,
                "returned": False
            }
            issued_books_collection.insert_one(issued_book)
            books_collection.update_one({"_id": book_id}, {"$inc": {"copies": -1}})
            flash(f"Book with ID {book_id} issued to user {user_id} until {due_date}.")
        else:
            flash(f"Book with ID {book_id} is not available.")
        return redirect(url_for('index'))
    
    return render_template('issue_book.html')

@app.route('/return_book', methods=['GET', 'POST'])
def return_book():
    if request.method == 'POST':
        book_id = int(request.form['book_id'])
        user_id = request.form['user_id']
        
        issued_book = issued_books_collection.find_one({"book_id": book_id, "user_id": user_id, "returned": False})
        if issued_book:
            issued_books_collection.update_one({"_id": issued_book["_id"]}, {"$set": {"returned": True}})
            books_collection.update_one({"_id": book_id}, {"$inc": {"copies": 1}})
            flash(f"Book with ID {book_id} returned by user {user_id}.")
        else:
            flash(f"No issued book found for book ID {book_id} and user ID {user_id}.")
        return redirect(url_for('index'))
    
    return render_template('return_book.html')

@app.route('/defaulters')
def defaulters():
    today = datetime.now()
    defaulters_list = issued_books_collection.find({"due_date": {"$lt": today}, "returned": False})
    return render_template('defaulters.html', defaulters=defaulters_list)
