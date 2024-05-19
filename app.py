from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import requests
import pdb

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for session management
# Define the URL of the endpoint to submit reviews
REVIEW_ENDPOINT = "http://parcial-lb-2019743473.us-east-1.elb.amazonaws.com:8000/review/"
BOOKLIST_ENDPOINT = "http://parcial-lb-2019743473.us-east-1.elb.amazonaws.com:8001"

@app.route('/')
def home():
    return render_template('index.html')
    # return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        # Assuming your backend API endpoint for login is /api/login
        response = requests.post('http://parcial-lb-2019743473.us-east-1.elb.amazonaws.com:8000/api/login', json={'email': email, 'password': password})
        if response.status_code == 200:
            user_data = response.json()
            session['user_id'] = user_data['userId']
            return redirect(url_for('dashboard'))
        else:
            return "Login failed, please try again."
    return render_template('login.html')

@app.route('/register', methods=['GET'])
def show_register():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        repeat_password = request.form['repeat-password']

    
        if password != repeat_password:
            return "Passwords do not match."

        user_data = {
            'name': name,
            'email': email,
            'password': password
        }
        response = requests.post('http://parcial-lb-2019743473.us-east-1.elb.amazonaws.com:8000/user/', json=user_data)
        if response.ok:
            result = response.json()
            session['user_id'] = result.get('id')  # Adjust based on actual field name
            return redirect('/dashboard')
        else:
            error = response.json()
            return f"Error: {error.get('detail')}"
        

@app.route('/search/<isbn>')
def search(isbn):
    
    response = requests.get(f'http://parcial-lb-2019743473.us-east-1.elb.amazonaws.com:8000/book/{isbn}')
    if response.ok:
        session['current_book'] = isbn
        book = response.json()
        return render_template('search_result.html',isbn=isbn, book=book)
    else:
        return redirect('/dashboard')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/add-to-list', methods=['POST'])
def add_to_list():
    if request.method == 'POST':
        # Check if user_id exists in session
        if 'user_id' not in session:
            return jsonify({"error": "User not authenticated."}), 401
        
        # Retrieve user_id from session
        user_id = session['user_id']
        
        book_id = session['current_book']
        
        list_type = request.form['list']
    
        # Make the POST request to the review endpoint
        endpoint = f'{BOOKLIST_ENDPOINT}/record/{user_id}/{book_id}?type={list_type}'
        pdb.set_trace()
        response = requests.post(endpoint)
        
        # Check the response status code
        if response.status_code == 200:
            return redirect('/dashboard')
        else:
            return jsonify({"error": "Failed to add book to list."}), response.status_code




@app.route('/submit_review', methods=['POST'])
def submit_review():
    if request.method == 'POST':
        # Check if user_id exists in session
        if 'user_id' not in session:
            return jsonify({"error": "User not authenticated."}), 401
        
        # Retrieve user_id from session
        user_id = session['user_id']
        
        book_id = session['current_book']
        rating = request.form['rating']
        review_text = request.form['review_text']
        
        # Prepare data to submit to the review endpoint
        payload = {
            "user_id": user_id,
            "book_id": int(book_id),
            "rating": int(rating),
            "description": review_text
        }
        
        # Make the POST request to the review endpoint
        response = requests.post(REVIEW_ENDPOINT, json=payload)
        
        # Check the response status code
        if response.status_code == 200:
            return redirect('/dashboard')
        else:
            return redirect('/dashboard')




if __name__ == '__main__':
    app.run(debug=True)
