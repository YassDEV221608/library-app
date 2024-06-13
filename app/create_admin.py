from .models import User
from .extensions import bcrypt

def create_admin(app):
    with app.app_context():
        # Check if admin user already exists
        admin_user = User.objects(username='yassDev2201608').first()
        if not admin_user:
            # Create an admin user
            admin_user = User(username='yassDev2210608', password_hash=bcrypt.generate_password_hash('Gtahyjump-12345').decode('utf-8'), is_admin=True)
            admin_user.save()
            print("Admin user created successfully.")
        else:
            print("Admin user already exists.")

