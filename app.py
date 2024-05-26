from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, current_app
from flask_mail import Mail, Message

from flask_login import current_user
from werkzeug.utils import secure_filename
import os
from pymongo import MongoClient

client = MongoClient('mongodb://user:password@ds053764.mongolab.com:53764/web_design')
db = client.web_design
pro = db["profile"]
book = db["books"]
collection = db["users"]
message = db["messages"]

app = Flask(__name__)

app.config.update(dict(
    DEBUG=True,
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USE_SSL=False,
    MAIL_USERNAME='abc@gmail.com',
    MAIL_PASSWORD='**********',
))
mail = Mail(app)

app.config['UPLOAD_FOLDER'] = 'templates/upload/'
app.config['ALLOWED_EXTENSIONS'] = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']

@app.route("/")
@app.route("/home")
def hello():
    return render_template("home.html")

@app.route('/index')
def index():
    return render_template('index.html')

@app.route("/create_profile")
def create_profile():
    profile = {
        "Name": "DON",
        "Phone": ["982833049043", "09293048u52843", "qw548293854"],
        "Address": {
            "postbox": 50505,
            "house No": 34,
            "city": "Wilayah Kuala Lumpur",
            "country": "Malaysia"
        }
    }
    pro.insert(profile)
    return "done !!!"

@app.route("/show_profile")
def show_profile():
    data = {"data": list(pro.find())}
    print(data)
    return render_template("profile.html", data=data)

@app.route("/create_books")
def create_books():
    books = [
        {
            "Title": "Harry Potter",
            "Publisher": ["Sasbadi SDN BHD", "OSBORN"],
            "Author": "J.K Rowling",
            "ISBN": "952536578",
            "Price": "RM 56.90"
        },
        {
            "Title": "Hunger Games",
            "Publisher": ["Hadi Books", "Sasbadi SDN BHD"],
            "Author": "Parminder",
            "ISBN": "58898745245",
            "Price": "RM 25.30",
        },
        {
            "Title": "Jack and Beanstalk",
            "Publisher": ["Kuntum", "Pearson"],
            "Author": "Justin ",
            "ISBN": "2256699871",
            "Price": "RM 15.30",
        },
        {
            "Title": "Hunger Games Part 2",
            "Publisher": ["Hadi Books", "Sasbadi SDN BHD"],
            "Author": ["Parminder", "Jack", "Bond"],
            "ISBN": "254723687",
            "Price": "RM 25.30",
        }
    ]

    for i in range(4):
        book.insert(books[i])

    return "done !!!"

@app.route("/show_books")
def show_books():
    book1 = {"books": list(book.find())}
    print(book1)
    return render_template("books.html", book={"books": list(book.find())})

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/location")
def location():
    return render_template("location.html")

@app.route("/form", methods=['POST', 'GET'])
def form():
    if request.method == 'POST':
        data = {
            'name': request.form['username'],
            'passs': request.form['password'],
            'emai': request.form['email'],
            'status': False
        }

        token = generate_token(data['emai'])
        data['token'] = str(token)

        print("Token: ", token)

        db = client.web_design.users
        db.insert(data)

        frm = "parmin.rock@gmail.com"
        subject = "Welcome To Permin Rock, Confirm Your Account"
        recipients = data['emai']

        confirm_url = "https://forms-parmin-rock.c9users.io/activate/" + str(token)

        innerMsg = """Your account was successfully created.Please click the link to confirm your 
        email address and activate your account: <a href='{0}'>Click To Activate</a>""".format(confirm_url)

        send_mail(innerMsg, innerMsg, frm, recipients, subject)

    return render_template("form.html")

@app.route('/activate/<token>', methods=['GET'])
def activate(token):
    db = client.web_design.users
    q = db.find_one({'token': token})

    print(q)

    try:
        if q != []:
            return jsonify(data={"activate": 'successfully', "User": q['name']})
        else:
            return jsonify(data='Failed !!!')
    except:
        pass

@app.route('/login2')
def login2():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        password = request.form['password']

        db = client.web_design
        collection = db['users']
        user = request.form['username']
        password = request.form['password']

        verify = list(collection.find({'user': user, 'password': password}))

        if verify:
            return render_template('userpage.html')
        else:
            return redirect(url_for('home'))

    return render_template('login.html')

def checkdetails():
    user = request.args.get('user')

    db = client.web_design
    collection = db['users']
    c = collection.find({'user': user})

    if c.count():
        UserInfo = {'name': "MAysam", 'imageAddress': r"/static/image/silver34.jpg"}
    else:
        UserInfo = {'name': "Idon't know", 'imageAddress': r"/static/image/Harry Potter.jpg"}
    return render_template('home12.html', name=UserInfo['name'], imageAddress=UserInfo['imageAddress'])

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/upload', methods=['POST'])
def upload_another():
    try:
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('uploaded_file', filename=filename))
    except:
        pass

    return "Error!!!!!"

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/logout')
def logout():
    return render_template('home.html')

@app.route('/messages')
def messages():
    return 'Messages'

@app.route('/submit_message', methods=['POST'])
def submit_message():
    print(request.form)
    return redirect(url_for('messages'))

def send_mail(html, body, frm, receivers, subject):
    from mailer import Mailer
    from mailer import Message

    message = Message(From=frm, To=receivers, BCC=[], charset="utf-8")
    message.Subject = subject
    message.Html = html
    message.Body = body

    sender = Mailer(host="smtp.gmail.com", port=587, use_tls=True, usr="parmin.rock@gmail.com", pwd="Learning36")
    sender.send(message)

@app.route('/confirm/<token>')
def confirm_email(token):
    return redirect(url_for('login'))

def generate_token(email):
    import uuid
    return uuid.uuid4()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
