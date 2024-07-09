# app.py
import os
import sys
import threading
from flask import Flask, flash, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO
from vidcam import start_video_capture, stop_video_capture
from authe import is_unique_username, save_user_info, authenticate_user



# Redirect stderr to null
sys.stderr = open(os.devnull, 'w')
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Set a secret key for the session, change it to a more secure value
socketio = SocketIO(app)  # Initialize the socketio variable


# Ensure 'account.txt' exists on startup
if not os.path.exists('account.txt'):
    with open('account.txt', 'w', encoding='utf-8'):
        pass


# Home Page
@app.route('/')
def home():
    return render_template('home.html')


# Signup Page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
   

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Check if the username already exists
        if not is_unique_username(username):
            return render_template('signup.html', error='Username already exists. Choose another.')

        # Save the user information to account.txt
        save_user_info(username, password)

        return redirect(url_for('login'))

    return render_template('signup.html', error=None)


# Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Check if the provided credentials are valid
        if authenticate_user(username, password):
            # Store the username in the session
            session['username'] = username

            # Create a unique identifier for the user's capture thread
            capture_thread_id = f'capture_thread_{username}'

            # Start video capture asynchronously after login
            capture_thread = start_video_capture(username, capture_thread_id, socketio)

            # Store the capture_thread_id in the session for later use
            session['capture_thread_id'] = capture_thread_id

            # Redirect to the dashboard page
            return redirect(url_for('welcome', username=username))
        else:
            flash('Invalid username or password. Please try again.', 'error')
            return render_template('login.html', error='Invalid username or password.')

    # Check if the user has an active capture thread when accessing the login page
    username = session.get('username')
    capture_thread_id = session.get('capture_thread_id')

    if username and capture_thread_id:
        # Get the existing capture thread
        capture_thread = session.get('capture_thread')

        # Stop the existing capture thread if it is still alive
        if capture_thread and capture_thread.is_alive():
            stop_video_capture(capture_thread)

        # Remove capture thread information from the session
        session.pop('capture_thread_id', None)
        session.pop('capture_thread_name', None)
    flash('Invalid username or password. Please try again.', 'error')
    return render_template('login.html', error=None)

@app.route('/welcome')
def welcome():
    username = session.get('username')
    capture_thread_id = session.get('capture_thread_id')

    if username and capture_thread_id:
        # Start video capture when the user accesses the welcome page
        capture_thread = start_video_capture(username, capture_thread_id, socketio)
        
        # Store the relevant thread information in the session
        session['capture_thread_id'] = capture_thread_id
        session['capture_thread_name'] = capture_thread.name

        return render_template('welcome.html', username=username)
    else:
        return redirect(url_for('login'))

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    if request.method == 'POST':
        # Stop video capture when logging out
        username = session.get('username')
        capture_thread_id = session.get('capture_thread_id')

        if username and capture_thread_id:
            capture_thread = session.get('capture_thread')
            if capture_thread:
                stop_video_capture(capture_thread)

            # Remove capture thread information from the session
            session.pop('capture_thread_id', None)
            session.pop('capture_thread_name', None)

        # Clear the username from the session
        session.pop('username', None)

        return redirect(url_for('home'))  # Redirect to the home page after logout

    return render_template('logout.html')  # Render the logout confirmation page

@socketio.on('user_leave')
def handle_user_leave():
    # Perform actions when the user leaves the page
    print('User left the page. Stopping video capture and saving video.')

    # Get the username from the session
    username = session.get('username')

    # Stop and save the video
    if username:
        capture_thread = session.get('capture_thread')
        if capture_thread:
            stop_video_capture(capture_thread)


@app.route('/capture_video')
def capture_video_route():
    username = session.get('username')

    if username:
        # Call the capture_video function from vidcam.py
        capture_video()
        return redirect(url_for('dashboard', username=username))
    else:
        return redirect(url_for('login'))


def capture_video():
    # Get the capture thread from the session
    capture_thread = session.get('capture_thread')

    # Check if the capture thread is already running
    if capture_thread and capture_thread.is_alive():
        print(f'Video capture is already running.')
    else:
        # Start video capture asynchronously
        new_capture_thread = start_video_capture()

        # Stop the previous capture thread if it exists
        if capture_thread and capture_thread.is_alive():
            stop_video_capture(capture_thread)

        # Store the new capture thread in the session
        session['capture_thread'] = new_capture_thread

        print('Video capture started.')


@app.route('/dashboard/<username>')
def dashboard(username):
    # Read the contents of detec.txt
    with open('detec.txt', 'r') as file:
        detected_hazards = [line.strip() for line in file.readlines()]


    # Check if the video capture thread is running
    capture_thread = session.get('capture_thread')
    capture_thread_status = capture_thread and capture_thread.is_alive()

    return render_template('dashboard.html', username=username, capture_thread_status=capture_thread_status, detected_hazards=detected_hazards)


# SocketIO events
@socketio.on('connect')
def handle_connect():
    pass

@socketio.on('disconnect')
def handle_disconnect():
    pass


# Define the "About Us" page
@app.route('/about')
def about_us():
    return render_template('about-us.html')

# Define the "Contact Us" page
@app.route('/contact')
def contact_us():
    return render_template('contact-us.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/stop_capture', methods=['POST'])
def stop_capture():
    # Stop video capture
    stop_video_capture()

    return redirect(url_for('settings'))


if __name__ == '__main__':
    # Use 'adhoc' for a self-signed certificate
    ssl_certificate = ('your-cert.pem', 'your-key.pem')

    # Run the Flask app with SSL enabled
    app.run(ssl_context=ssl_certificate, debug=True, host='0.0.0.0', port=5000)
