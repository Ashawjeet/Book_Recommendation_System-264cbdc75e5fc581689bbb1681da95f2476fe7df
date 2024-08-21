from flask import Flask, render_template, request
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import pickle

from flask import Flask,render_template,request,session,redirect,url_for
import pickle
import re
import numpy as np
from flask_mysqldb import MySQL
import MySQLdb.cursors
import mysql.connector


app = Flask(__name__) 

app.secret_key = 'xyzsdfg'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'user-system'
  
mysql = MySQL(app)


@app.route('/', methods =['GET', 'POST'])
def login():
    mesage = ''
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE email = % s AND password = % s', (email, password, ))
        user = cursor.fetchone()
        if user:
            session['loggedin'] = True
            session['userid'] = user['userid']
            session['name'] = user['name']
            session['email'] = user['email']
            mesage = 'Logged in successfully !'
            return render_template('index.html', mesage = mesage)
        else:
            mesage = 'Please enter correct email / password !'
    return render_template('login.html', mesage = mesage)
  
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('userid', None)
    session.pop('email', None)
    return redirect(url_for('login'))
  

@app.route('/register', methods =['GET', 'POST'])
def register():
    mesage = ''
    if request.method == 'POST' and 'name' in request.form and 'password' in request.form and 'email' in request.form :
        userName = request.form['name']
        password = request.form['password']
        email = request.form['email']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE email = % s', (email, ))
        account = cursor.fetchone()
        if account:
            mesage = 'Account already exists !'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            mesage = 'Invalid email address !'
        elif not userName or not password or not email:
            mesage = 'Please fill out the form !'
        else:
            cursor.execute('INSERT INTO user VALUES (NULL, % s, % s, % s)', (userName, email, password, ))
            mysql.connection.commit()
            mesage = 'You have successfully registered !'
    elif request.method == 'POST':
        mesage = 'Please fill out the form !'
    return render_template('register.html', mesage = mesage)

try:
    # Load pickled DataFrame objects
    pred_df = pickle.load(open('pred_df.pkl', 'rb'))
    books = pickle.load(open('unique_books.pkl', 'rb'))
    top_50_df = pickle.load(open('top_50_books.pkl', 'rb'))
    sw = pickle.load(open('stopwords.pkl', 'rb'))

    # Continue with the rest of your code
    # ...
except Exception as e:
    # Print the exception to see the error message
    print("Error loading pickled data:", e)



def recommend_items_by_item(book_name, predictions_df, items_df=None ,topn=10, verbose=False):
    
    pdt = predictions_df.transpose() 
    cosine_similarities = cosine_similarity(np.array(pdt[book_name]).reshape(1,-1),predictions_df )
    recommended_df = pd.DataFrame( {'recStrength': cosine_similarities[0] }, index = predictions_df.index ).sort_values(by = 'recStrength',ascending = False)
    recommended_df = recommended_df.iloc[:topn,]
    # print(recommended_df)
    if verbose:
          if items_df is None:        
              raise Exception('"items_df" is required in verbose mode')
          # print(recommended_df) 
          # lower case the Book-Title of books DataFrame if not to avoid errors
          items_df['Title'] = items_df['Title'].str.lower()

          # merge recommended items with other details
          recommended_df = recommended_df.merge(items_df, how = 'left', 
                                                        # left_on = 'index', 
                                                        left_index = True,
                                                        right_on = 'Title')[['recStrength', 'ISBN', 'Title', 
                                                                            'Pub_Year','Publisher',
                                                                            'Image_Url','Author']]
          recommended_df = recommended_df.drop_duplicates(subset='Title', keep='first')
    return recommended_df

def recommend(name): 
    global title
    title = name
    if len(name) == 0:
        return f"Oops! Please Enter name of the book... Try Again"
    # split words in name and remove stopwords   
    names = name.lower().strip().split(' ')
    removed = [names.remove(word) for word in set(sw).intersection(names)]
    subset = []
    if len(names[0]) == 0:
        return f"Oops! Please Enter a better and valid name... Try Again" 
    # get all subsets of the names
    for l in range(len(names)):
        subset.append(' '.join(names[:l+1]))
        subset.append(' '.join(names[l:])) 

    # get all book names based on subset of name provided
    title = books[books['Title'].str.contains(f'|'.join(subset))]['Title'].values 
    # title = list(set(title)) 
    
    # check how muny similar words in subset are matched from the book titles 
    word_count = []
    for book in title:
        book = book.split(' ')
        both = set(book).intersection(set(subset))
        word_count.append(len(both))
    # best matched book title
    try:
      title = title[word_count.index(max(word_count))]
    except:
      return f'Enter a valid Book Name'

    # recommend 
    try: 
        books_recommendations = recommend_items_by_item(title, pred_df, books ,topn=6, verbose = True)
        return books_recommendations
    except Exception as error:
        return f"Oops! Book Not Found..... Try Again"



@app.route('/home')
def home():

    book_name = top_50_df.loc[:19,'Book-Title']
    book_auth = top_50_df.loc[:19,'Author']
    book_url = top_50_df.loc[:19,'Image_Url']

    return render_template('home.html',b_name = book_name, author = book_auth, url = book_url )


@app.route('/index')
def recommend_ui():
    return render_template('index.html')

@app.route('/recommend',methods=['post']) 
def myapp():
    user_input = request.form.get('user_input')
    recommendation_df =  recommend(user_input)
    try:
        rec_data = []
        recommendation_df = recommendation_df[['Title','Pub_Year', 'Image_Url', 'Author']]
        for i in range(len(recommendation_df.index)):
            rec_data.append(recommendation_df.iloc[i].values)
    except:
        rec_data = [['Oops! Book not Found','','','Please Try Again']]

    return render_template('index.html' , book_name = title, data = rec_data) 

# tests is only for testing cases and IO
@app.route('/tests') 
def test():
    '''This function is for testing results'''
    rec_data = []
    recommendation_df =  recommend('')
    for i in range(len(recommendation_df.index)):
            rec_data.append(recommendation_df.iloc[i].values)
    return recommendation_df['Image_Url'].values[0]

if __name__ == '__main__':
    app.run(debug = True, port=8089)

