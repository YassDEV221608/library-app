from flask import Flask
import pymongo
import gridfs

app = Flask(__name__)
app.secret_key = '545a601fef35e5203a13fbf68599c646'  # Replace with a strong secret key

# MongoDB setup
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["library"]
books_collection = db["books"]
issued_books_collection = db["issued_books"]
fs = gridfs.GridFS(db)

from app import routes
