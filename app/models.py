from flask_login import LoginManager
from flask_mongoengine import MongoEngine
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = MongoEngine()


class User(db.Document, UserMixin):
    username = db.StringField(max_length=50, unique=True, required=True)
    password_hash = db.StringField(required=True)
    is_admin = db.BooleanField(default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # These methods are required by Flask-Login
    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

