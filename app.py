from flask import Flask, render_template, redirect, url_for

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get-started')
def get_started():
    # Redirect to the get started page or functionality
    return redirect(url_for('home'))

@app.route('/login')
def login():
    # Render a login page or perform login functionality
    return render_template('login.html')

@app.route('/signup')
def signup():
    # Render a signup page or perform signup functionality
    return render_template('signup.html')

if __name__ == '__main__':
    app.run(debug=True)
