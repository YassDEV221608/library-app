from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from app.extensions import initialize_extensions
from config import Config
from .models import db
from .create_admin import create_admin
from .extensions import neo4j_conn

app = Flask(__name__)
app.secret_key = "5396990d5983c31e12904736905fdfe4"
app.config.from_object(Config)
initialize_extensions(app)
#create_admin(app)
db.init_app(app)
bcrypt = Bcrypt(app)
login = LoginManager(app)
login.login_view = 'login'

from app import routes
