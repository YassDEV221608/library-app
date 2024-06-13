from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mongoengine import MongoEngine
from gridfs import GridFS

from neo4j import GraphDatabase

bcrypt = Bcrypt()
login = LoginManager()
db = MongoEngine()

books_collection = None  # Placeholder for the books collection
fs = None  # Placeholder for the GridFS instance

def initialize_extensions(app):
    global books_collection, fs
    bcrypt.init_app(app)
    login.init_app(app)
    db.init_app(app)
    
    # Initialize MongoDB collection and GridFS
    books_collection = db.get_db().books
    fs = GridFS(db.get_db())


class Neo4jConnection:
    def __init__(self, uri, user, pwd):
        self.__uri = uri
        self.__user = user
        self.__password = pwd
        self.__driver = None
        try:
            self.__driver = GraphDatabase.driver(self.__uri, auth=(self.__user, self.__password))
        except Exception as e:
            print(f"Failed to create the driver: {e}")

    def close(self):
        if self.__driver is not None:
            self.__driver.close()

    def query(self, query, parameters=None, **kwargs):
        assert self.__driver is not None, "Driver not initialized!"
        session = None
        response = None
        try:
            session = self.__driver.session()
            response = list(session.run(query, parameters, **kwargs))
        except Exception as e:
            print(f"Query failed: {e}")
        finally:
            if session is not None:
                session.close()
        return response

neo4j_conn = Neo4jConnection(uri="bolt://localhost:7687", user="neo4j", pwd="gtahyjump")
