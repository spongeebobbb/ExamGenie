import firebase_admin
from firebase_admin import credentials, auth, db
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import bcrypt
import requests
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a strong secret key

# Initialize Firebase Admin SDK
cred = credentials.Certificate("examgenie-a727d-firebase-adminsdk-857c0-1dee3695f7.json")
firebase_app = firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://examgenie-a727d-default-rtdb.firebaseio.com',
    'authDomain': 'examgenie-a727d.firebaseapp.com'  # Add your auth domain
})

# Firebase Web API Key (get this from your Firebase Console)
FIREBASE_WEB_API_KEY = 'AIzaSyDLijPd1eyBBs3NpnIs0n9hSXhlsAfNq7s'  # Replace with your Web API key

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    if 'user_id' in session:
        # Redirect directly to the loggedin page if the user is logged in
        return redirect(url_for('loggedin'))
    else:
        # If not logged in, redirect to the login page
        return redirect(url_for('login'))


@app.route('/get-started')
def get_started():
    return redirect(url_for('signup'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        name = request.form.get('name', 'User')
        
        try:
            # Use Firebase REST API for authentication (sign up user)
            auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_WEB_API_KEY}"
            auth_data = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }
            
            auth_response = requests.post(auth_url, json=auth_data)
            auth_response.raise_for_status()  # Raise exception for bad status codes
            auth_info = auth_response.json()
            
            user_id = auth_info['localId']
            
            # Hash password for database storage
            password_hash = hash_password(password)
            
            # Create user data in Realtime Database
            user_ref = db.reference(f'users/{user_id}')
            user_data = {
                'email': email,
                'name': name,
                'password_hash': password_hash,
                'signup_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'last_login': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'profile_completed': False
            }
            
            user_ref.set(user_data)
            flash("Account created successfully! Please log in.", "success")
            return redirect(url_for('login'))
            
        except requests.exceptions.RequestException as e:
            flash(f"Error creating account. Please try again.", "danger")
            print(f"Signup error: {str(e)}")
            
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        try:
            # Use Firebase REST API for authentication (sign in user)
            auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
            auth_data = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }
            
            auth_response = requests.post(auth_url, json=auth_data)
            auth_response.raise_for_status()  # Raise exception for bad status codes
            auth_info = auth_response.json()
            
            user_id = auth_info['localId']
            
            # Get user data from Realtime Database
            user_ref = db.reference(f'users/{user_id}')
            user_data = user_ref.get()
            
            if user_data:
                # Store user session
                session['user_id'] = user_id  # Save user ID to session
                session['token'] = auth_info['idToken']  # Save Firebase ID token to session
                
                # Update last login
                user_ref.update({
                    'last_login': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                
                flash(f"Welcome back, {user_data.get('name', 'User')}!", "success")
                return redirect(url_for('loggedin'))  # Redirect to the loggedin page
                
            else:
                flash("User data not found. Please try again.", "danger")
                
        except requests.exceptions.RequestException as e:
            flash(f"Invalid credentials. Please try again.", "danger")
            print(f"Login error: {str(e)}")
            
    return render_template('login.html')

@app.route('/loggedin')
@login_required
def loggedin():
    try:
        user_ref = db.reference(f'users/{session["user_id"]}')
        user_data = user_ref.get()
        
        if not user_data:
            session.clear()
            flash("User data not found. Please log in again.", "warning")
            return redirect(url_for('login'))
            
        return render_template('loggedin.html', user=user_data)
        
    except Exception as e:
        flash("An error occurred. Please try again.", "danger")
        print(f"Logged-in route error: {str(e)}")
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    if 'user_id' in session:
        user_ref = db.reference(f'users/{session["user_id"]}')
        user_ref.update({
            'last_logout': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    session.clear()  # Clear the session to log out the user
    flash("You have been logged out successfully.", "info")
    return redirect(url_for('login'))

@app.route('/protected')
@login_required
def protected():
    try:
        user_ref = db.reference(f'users/{session["user_id"]}')
        user_data = user_ref.get()
        
        if not user_data:
            session.clear()
            flash("User data not found. Please log in again.", "warning")
            return redirect(url_for('login'))
            
        return render_template('protected.html', user=user_data)
        
    except Exception as e:
        flash("An error occurred. Please try again.", "danger")
        print(f"Protected route error: {str(e)}")
        return redirect(url_for('login'))

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    try:
        user_ref = db.reference(f'users/{session["user_id"]}')
        
        update_data = {
            'name': request.form.get('name'),
            'bio': request.form.get('bio'),
            'profile_completed': True,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        user_ref.update(update_data)
        flash("Profile updated successfully!", "success")
        
    except Exception as e:
        flash("Error updating profile.", "danger")
        print(f"Profile update error: {str(e)}")
        
    return redirect(url_for('protected'))

def hash_password(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def check_password(password, hashed_password):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

if __name__ == '__main__':
    app.run(debug=True)
