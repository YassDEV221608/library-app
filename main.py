import pymongo
from datetime import datetime, timedelta

# Connect to MongoDB
client = pymongo.MongoClient("mongodb://mongo:27017/")
db = client["library"]
books_collection = db["books"]
issued_books_collection = db["issued_books"]

def add_book(book_id, title, author, copies):
    book = {
        "_id": book_id,
        "title": title,
        "author": author,
        "copies": copies
    }
    books_collection.insert_one(book)
    print(f"Book '{title}' added successfully.")

def delete_book(book_id):
    result = books_collection.delete_one({"_id": book_id})
    if result.deleted_count > 0:
        print(f"Book with ID {book_id} deleted successfully.")
    else:
        print(f"No book found with ID {book_id}.")

def view_books():
    books = books_collection.find()
    for book in books:
        print(book)

def issue_book(book_id, user_id, days):
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
        print(f"Book with ID {book_id} issued to user {user_id} until {due_date}.")
    else:
        print(f"Book with ID {book_id} is not available.")

def return_book(book_id, user_id):
    issued_book = issued_books_collection.find_one({"book_id": book_id, "user_id": user_id, "returned": False})
    if issued_book:
        issued_books_collection.update_one({"_id": issued_book["_id"]}, {"$set": {"returned": True}})
        books_collection.update_one({"_id": book_id}, {"$inc": {"copies": 1}})
        print(f"Book with ID {book_id} returned by user {user_id}.")
    else:
        print(f"No issued book found for book ID {book_id} and user ID {user_id}.")

def defaulters():
    today = datetime.now()
    defaulters_list = issued_books_collection.find({"due_date": {"$lt": today}, "returned": False})
    for defaulter in defaulters_list:
        print(defaulter)

# Example usage:
add_book(1, "The Great Gatsby", "F. Scott Fitzgerald", 3)
delete_book(1)
view_books()
issue_book(1, "user123", 7)
return_book(1, "user123")
defaulters()
