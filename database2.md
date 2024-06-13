```mermaid
graph LR
A[from flask import ...]
B[from flask_login import ...]
C[from bson.objectid import ...]
D[from .extensions import ...]  ; Assuming extensions.py holds database connections
E[from app.models import ...]
F[from app import ...]
G[login_manager = LoginManager(app)]
A --> G
B --> G
C --> G
D --> G
E --> G
F --> G
G --> H
H[login_manager.user_loader]
H --> I
I[.extensions import ...]
I --> J
J[User.objects(id=user_id).first()]
G --> K
K[@app.route('/login', methods=['GET', 'POST'])]
L[current_user.is_authenticated]
K --> L
L --> M{return redirect(url_for('index'))}
K --> N
N[form = LoginForm()]
O[form.validate_on_submit()]
N --> O
O --> P{flash('Invalid username or password', 'danger')}
O --> Q
Q[user = User.objects(username=form.username.data).first()]
Q --> R{return redirect(url_for('signup'))}
Q --> S
S[bcrypt.check_password_hash(user.password_hash, form.password.data)]
S --> T{flash('Invalid username or password', 'danger')}
S --> U
U[login_user(user, remember=form.remember_me.data)]
U --> V{session['username'] = user.username}
U --> W{session['is_admin'] = user.is_admin}
U --> X{return redirect(next_page) if next_page else redirect(url_for('index'))}
# many other routes are elided here ...
Y[@app.route('/update_book_copies/<book_id>', methods=['GET', 'POST'])]
Y --> Z{current_user.is_admin}
Z --> AA{flash('You do not have permission to update book copies.', 'danger')}
Z --> AB
AB[book = books_collection.find_one({'_id': ObjectId(book_id)})]  ; Replace with appropriate MongoDB query
AB --> AC{flash('Book not found.', 'danger')}
AB --> AD
AD[request.method == 'POST']
AD --> AE{new_copies = request.form.get('copies', type=int)}
AE --> AF{flash('Invalid number of copies.', 'danger')}
AE --> AG
AG[new_copies is not None and new_copies >= 0]
AG --> AH{books_collection.update_one( ... , {'$set': {'copies': new_copies}})}
AG --> AI{"MATCH (b:Book {title: $title, author: $author}) SET b.copies = $copies", ...}  ; Update Neo4j relationship (if applicable)
AG --> AJ{flash(..., 'success')}
AG --> AK{return redirect(url_for('view_books'))}

```