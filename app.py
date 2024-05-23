from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import requests
import pdb
import pprint
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for session management
# Define the URL of the endpoint to submit reviews
# 8000
REVIEW_ENDPOINT = "http://parcial-lb-533779242.us-east-1.elb.amazonaws.com:8002/review/"
BOOKLIST_ENDPOINT = "http://parcial-lb-533779242.us-east-1.elb.amazonaws.com:8001"
BOOKUSER_ENDPOINT = 'http://parcial-lb-533779242.us-east-1.elb.amazonaws.com:8000'

@app.route('/')
def home():
    return render_template('index.html')


''' ---------------- USERS CRUD ------------------- '''

@app.route('/login', methods=['GET', 'POST'])
def login():
    ''' ------ READ User ------ '''

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        endpoint = f'{BOOKUSER_ENDPOINT}/user/login'
        
        response = requests.post(endpoint, json={'email': email, 'password': password})
        if response.status_code == 200:
            user_data = response.json()
            session['user_id'] = 3
            session['email'] = user_data['email']
            return redirect('/dashboard')
        else:
            return redirect('/login')
        
    return render_template('login.html')

@app.route('/register', methods=['GET'])
def show_register():
    return render_template('register.html')


@app.route('/register', methods=['POST'])
def register():
    '''------ CREATE User, CREATE Lists ------'''

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        repeat_password = request.form['repeat-password']

        if password != repeat_password:
            return render_template('register.html')

        user_data = {
            'name': name,
            'email': email,
            'password': password
        }

        response = requests.post(f'{BOOKUSER_ENDPOINT}/user', json=user_data)

        if response.ok:
            result = response.json()
            session['user_id'] = result.get('id') 
            
            #Crear las listas:
            list_response = requests.post(f'{BOOKLIST_ENDPOINT}/list/all/{session["user_id"]}')
            if list_response.ok:
                return redirect('/dashboard')
        else:
            error = response.json()
            return f"Error: {error.get('detail')}"
        


@app.route('/edit_profile')
def load_edit():
    ''' ------------ READ User ------------ '''

    if 'user_id' not in session:
        return redirect('/login')
    user_id = session['user_id']
    response = requests.get(f'{BOOKUSER_ENDPOINT}/user/{user_id}')
    if response.ok:
        user = response.json()
        return render_template('edit_profile.html', user=user)
    else:
        return redirect('/dashboard')
    

@app.route('/edit_profile', methods=['POST'])
def update_profile():
    ''' ------------ EDIT User ------------'''

    if 'user_id' not in session:
        return redirect('/login')
    user_id = session['user_id']
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
    
    response = requests.put(f'{BOOKUSER_ENDPOINT}/user/{user_id}', json=user_data)
    if response.ok:
        return redirect('/dashboard')
    else:
        return "Failed to update user."


'''-------------------- Books CRUD --------------------'''
# No hacemos create, update ni delete desde front porque se cargan mediante postman - admin

@app.route('/book/<isbn>')
def search(isbn):
    '''---------------- READ Book ----------------'''
    response = requests.get(f'{BOOKUSER_ENDPOINT}/book/{isbn}')
    if response.ok:
        session['current_book'] = isbn
        book = response.json()
        # print(book['description'])
        return render_template('search_result.html',isbn=isbn, book=book)
    else:
        return redirect('/dashboard')
    


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    user_id = session['user_id']
    response = requests.get(f'{BOOKUSER_ENDPOINT}/user/{user_id}')

    if response.ok:
        user = response.json()
    
    user_reviews = []
    response = requests.get(f'{REVIEW_ENDPOINT}user/{user_id}')
    if response.ok:
        user_reviews = response.json()

        for review in user_reviews: 
            book_id = review['book_id']
            book_response = requests.get(f'{BOOKUSER_ENDPOINT}/book/{book_id}')
            if book_response.ok:
                review['book'] = book_response.json()
    else:
        user_reviews = []
    
    latest_books = []
    response = requests.get(f'{BOOKUSER_ENDPOINT}/book/all/')
    if response.ok:
        latest_books = response.json()

    return render_template('dashboard.html', user=user, user_reviews =user_reviews, latest_books=latest_books)


'''---------------- BookList  & Records CRUD ---------------- '''

@app.route('/add-to-list', methods=['POST'])
def add_to_list():
    '''------------------- CREATE Record  ---------------------'''

    if request.method == 'POST':
        if 'user_id' not in session:
            return jsonify({"error": "User not authenticated."}), 401
        
        user_id = session['user_id']
        book_id = session['current_book']
        list_type = request.form['list']
        
        endpoint = f'{BOOKLIST_ENDPOINT}/record/{user_id}/{book_id}?type={list_type}'
        response = requests.post(endpoint)
        
        if response.status_code == 201:
            return redirect('/dashboard')
        else:
            return redirect(f'/book/{book_id}')

@app.route('/lists')
def lists():
    '''------------------- READ Lists  ---------------------'''
    if 'user_id' not in session:
        return redirect('/login')
    user_id = session['user_id']
    response = requests.get(f'{BOOKLIST_ENDPOINT}/list/all/{user_id}')
    if response.ok:
        lists = response.json()
        lists = lists['user_list']
        for list in lists: 
            list['books'] = []
            if len(list['records'])>0:
                for record in list['records']:
                    book_id = record['book_id']
                    book_response = requests.get(f'{BOOKUSER_ENDPOINT}/book/{book_id}')
                    if book_response.ok:
                        list['books'].append(book_response.json())

        return render_template('lists.html', lists=lists)
    else:
        return redirect('/dashboard')
    

@app.route('/list/<list_id>?=<list_type>')
def list_detail(list_id):
    '''---------------- READ Records -----------------'''
    ''' A su vez es un read de Books (doble llamada get)'''

    if 'user_id' not in session:
        return redirect('/login')
    user_id = session['user_id']
    list_type = list_type
    response = requests.get(f'{BOOKLIST_ENDPOINT}/record/{list_id}')
    books = []
    if response.ok:
        for obj in response: 
            book_id = obj['book_id']
            book_response = requests.get(f'{BOOKUSER_ENDPOINT}/book/{book_id}')
            books.append(book_response.json())
        return render_template('list_detail.html', books=books, list_type=list_type)
    else:
        return redirect('/dashboard')
    

@app.route('/delete/<list_id>/<book_id>')
def delete_record(list_id, book_id):
    '''---------------- DELETE Records -----------------'''

    if 'user_id' not in session:
        return redirect('/login')
    
    # Security check:
    user_id = session['user_id']
    response = requests.get(f'{BOOKLIST_ENDPOINT}/list/all/{user_id}')
    list_ids = []
    if response.ok:
        for obj in response:
            list_ids.append(obj['id'])
        if list_id not in list_ids:
            return redirect('/dashboard')
        
    response = requests.delete(f'{BOOKLIST_ENDPOINT}/record/{list_id}/{book_id}')
    if response.ok:
        return redirect('/lists')
    else:
        return redirect('/dashboard')


''' ----------------- REVIEWS -------------------'''


@app.route('/submit_review', methods=['POST'])
def submit_review():
    '''---------------- CREATE Reviews  -----------------'''
    
    if request.method == 'POST':
        if 'user_id' not in session:
            return jsonify({"error": "User not authenticated."}), 401
        
        user_id = session['user_id']
        book_id = session['current_book']
        rating = request.form['rating']
        review_text = request.form['review_text']
        
        payload = {
            "user_id": user_id,
            "book_id": (book_id),
            "rating": int(rating),
            "description": review_text
        }
        
        response = requests.post(REVIEW_ENDPOINT, json=payload)
        if response.status_code == 200:
            return redirect('/dashboard')
        else:
            return redirect('/dashboard')
        

@app.route('/reviews')
def load_user_reviews():
    '''---------------- READ Reviews de un usuario (todos) -----------------'''

    if 'user_id' not in session:
        return redirect('/login')
    user_id = session['user_id']
    user_reviews = []
    response = requests.get(f'{REVIEW_ENDPOINT}user/{user_id}')
    if response.ok:
        user_reviews = response.json()

        for review in user_reviews: 
            book_id = review['book_id']
            book_response = requests.get(f'{BOOKUSER_ENDPOINT}/book/{book_id}')
            if book_response.ok:
                review['book'] = book_response.json()
        
        return render_template('reviews.html', reviews=user_reviews)
    else:
        return redirect('/dashboard')
    
@app.route('/review/<id>')
def load_single_review(id):
    '''---------------- READ un review -----------------'''

    if 'user_id' not in session:
        return redirect('/login')
    user_id = session['user_id']
    
    response = requests.get(f'{REVIEW_ENDPOINT}/{id}')
    if response.ok:
        review = response.json()
        return render_template('review.html', review=review)
    else:
        return redirect('/dashboard')
    

@app.route('/review/<id>/edit')
def load_edit_review(id):
    '''---------------- READ un review (para editarlo) -----------------'''

    if 'user_id' not in session:
        return redirect('/login')
    user_id = session['user_id']
    
    response = requests.get(f'{REVIEW_ENDPOINT}/{id}')
    if response.ok:
        review = response.json()
        return render_template('edit_review.html', review=review)
    else:
        return redirect('/dashboard')
    

@app.route('/review/<id>', methods=['POST'])
def update_review(id):
    '''---------------- UPDATE un review -----------------'''

    if 'user_id' not in session:
        return redirect('/dashboard')
    
    user_id = session['user_id']
    rating = request.form['rating']
    review_text = request.form['review_text']
    
    payload = {
        "user_id": user_id,
        "rating": int(rating),
        "description": review_text
    }
    
    response = requests.put(f'{REVIEW_ENDPOINT}/{id}', json=payload)
    
    if response.ok:
        return redirect('/review/{id}')
    else:
        return redirect('/dashboard')

@app.route('/review/<id>', methods=['DELETE'])
def delete_review(id):
    '''---------------- DELETE un review -----------------'''

    if 'user_id' not in session:
        return redirect('/dashboard')
    
    response = requests.delete(f'{REVIEW_ENDPOINT}/{id}')
    if response.ok:
        return redirect('/reviews')
    else:
        return redirect('/dashboard')
    



if __name__ == '__main__':
    app.run(debug=True)
