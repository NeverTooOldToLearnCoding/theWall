from flask import Flask, render_template, request, session, redirect, flash
from flask_bcrypt import Bcrypt
from mysqlconnection import connectToMySQL
import re
import copy
from datetime import datetime, timedelta

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9.+_-]+\.[a-zA-z]+$')

app=Flask(__name__)
app.secret_key = "ThisIsASecret"
bcrypt = Bcrypt(app)     # we are creating an object called bcrypt, 
                         # which is made by invoking the function Bcrypt with our app as an argument

@app.template_filter('duration_elapsed')
def timesince(dt, default="just now"):

    now = datetime.now()
    diff = now - dt
    
    periods = (
        (diff.days / 365, "year", "years"),
        (diff.days / 30, "month", "months"),
        (diff.days / 7, "week", "weeks"),
        (diff.days, "day", "days"),
        (diff.seconds / 3600, "hour", "hours"),
        (diff.seconds / 60, "minute", "minutes"),
        (diff.seconds, "second", "seconds"),
    )

    for period, singular, plural in periods:
        if period:
            return "%d %s ago" % (period, singular if period == 1 else plural)
    return default

@app.route("/")

def index():

	if 'loggedin' not in session:
		session["first_name"] = ""
		session["last_name"] = ""
		session["email"] = ""
		session["userid"] = ""
		session["loggedin"] = False
	elif session["loggedin"] == True:
		session.clear()

	return render_template ("index.html")

@app.route("/register", methods = ["POST"])

def logincheck():


	#first name errors
	if len(request.form['first_name']) < 1:
		flash("This field is required", "flashfirstname")
	elif len(request.form['first_name']) < 2:
		session["first_name"] = request.form['first_name']
		flash("First name needs to be longer than two characters, and contain only text.","flashfirstname")
	elif request.form['first_name'].isalpha() == False:
		flash("First name cannot contain numbers", "flashfirstname")

	#last name errors
	if len(request.form['last_name']) < 1:
		flash("This field is required", "flashlastname")
	elif len(request.form['last_name']) < 2:
		flash("Last name needs to be longer than two characters, and contain only text.", "flashlastname")
	elif request.form['last_name'].isalpha() == False:
		flash("Last name cannot contain numbers", "flashlastname")

	#email errors
	if len(request.form['email']) < 1:
		flash("This field is required", "flashemail")
	elif not EMAIL_REGEX.match(request.form['email']):
		flash("Invalid Email Address", "flashemail")

	#check e-mail against database and returns count
	mysql = connectToMySQL("mydb")
	query = "select idUsers,emails from users where emails = %(emails)s;"
	data = {"emails":request.form["email"]}
	emailcheck = mysql.query_db(query,data)

	#password errors
	if len(request.form['password']) < 1:
		flash("This field is required", "flashpassword")
	elif len(request.form['password']) < 8:
		flash("Password name needs to be longer than eight characters", "flashpassword")

	#confirm password errors
	if len(request.form['confirmpassword']) < 1:
		flash("This field is required", "flashconfirmpassword")
	elif len(request.form['confirmpassword']) < 8:
		flash("Password name needs to be longer than eight characters", "flashconfirmpassword")
	elif request.form['password'] != request.form['confirmpassword']:
		flash("The passwords do not match.","flashpassword")

	# if emailcheck: <- checks if you get a result or not
	#if count of e-mails is less than 1 insert into table
	if emailcheck:
		flash("This email is already registered.", "flashemail")

	if '_flashes' in session.keys():

		session["email"] = request.form["email"]
		session["first_name"] = request.form["first_name"]
		session["last_name"] = request.form["last_name"]
		session["loggedin"] = False

		return redirect("/")
	else:
		session["email"] = request.form["email"]
		session["first_name"] = request.form["first_name"]
		session["last_name"] = request.form["last_name"]
		session["loggedin"] = True

		pw_hash = bcrypt.generate_password_hash(request.form['password'])

		mysql = connectToMySQL('mydb')
		query2 = "insert into users (idUsers,first_name,last_name,emails,password,date_created,last_updated) values (idUsers,%(first_name)s, %(last_name)s,%(emails)s,%(password_hash)s,now(),now())"
		data2 = {
		"first_name": request.form["first_name"],
		"last_name": request.form["last_name"],
		"emails":request.form["email"],
		"password_hash": pw_hash
		}
		insertemail = mysql.query_db(query2,data2)

		mysql = connectToMySQL("mydb")
		query = "select idUsers,emails from users where emails = %(emails)s;"
		data = {"emails":request.form["email"]}
		emailcheck = mysql.query_db(query,data)
		session['userid'] = emailcheck[0]['idUsers']

		flash("You've successly been registered.", "flashsuccess")
		return redirect("/success")

@app.route("/login", methods = ["POST"])

def login():

	mysql = connectToMySQL("mydb")
	query = "SELECT idUsers,emails,password,first_name FROM users WHERE emails = %(emails)s;"
	data = { 
		"emails" : request.form["email"]
	}
	result = mysql.query_db(query, data)
	# print (result)

	if result:
		if bcrypt.check_password_hash(result[0]['password'], request.form['password']):
		# if we get True after checking the password, we may put the user id in session
			session['userid'] = result[0]['idUsers']
			session["first_name"] = result[0]["first_name"]
			session["loggedin"] = True
			return redirect('/thewall')
	flash("This email login and password combination does not exist.","flashlogin")
	return redirect("/")

@app.route("/success")

def success():

	# print(session["userid"])

	if session["userid"] == "":
		flash("You must be logged in to enter this website.", "flashlogout")
		return redirect ("/")
	else:
		return redirect ("/thewall")

@app.route("/thewall")

def thewall():


	#shows all messages and the users who sent them
	mysql = connectToMySQL("mydb")
	query = "select * from messages inner join users on users.idUsers = messages.sender_id"
	messages = mysql.query_db(query)

	#shows all comments made on each message
	mysql = connectToMySQL("mydb")
	query = "select * from comments inner join messages on comments.message_id = messages.idmessages inner join users on comments.user_id = users.idUsers order by comments.created_at asc"
	comments = mysql.query_db(query)

	#counts number of messages received
	# mysql = connectToMySQL("mydb")
	# query = "select count(message) as Total  from messages inner join users on users.idUsers = messages.sender_id where messages.recepient_id = %(sessionid)s;"
	# data = {
	# "sessionid" : session["userid"]
	# }
	# totalreceivedmessages = mysql.query_db(query,data)
	
	#used for for statement to display all users in db on right side
	# mysql = connectToMySQL("mydb")
	# query = "select * from users where idUsers <> %(sessionid)s;"
	# data = {
	# "sessionid" : session["userid"]
	# }
	# friends = mysql.query_db(query,data)

	#used for for statement to display total messages sent
	# mysql = connectToMySQL("mydb")
	# query = "select count(message) as Total from messages where sender_id = %(sessionid)s;"
	# data = {
	# "sessionid" : session["userid"]
	# }

	# totalsentmessages = mysql.query_db(query,data)

	# querys a user's messages received from friends in a database

	return render_template("thewall.html",messages = messages, comments = comments)

	# friends = friends, totalsentmessages = totalsentmessages[0]['Total'],totalreceivedmessages = totalreceivedmessages[0]['Total']

@app.route("/sendmessage", methods = ["POST"])

def send():

	mysql = connectToMySQL('mydb')
	query = "INSERT INTO messages (message,recepient_id,sender_id,date_created,last_updated) VALUES (%(message)s,%(recepient_id)s, %(sender_id)s, now(),now())"

	data = {
		'message': request.form["message"],
		'recepient_id': request.form['recepientID'],
		'sender_id': session['userid']
		}
	sendmessage = mysql.query_db(query,data)

	return redirect("/thewall")

@app.route('/delete/<id>')

def delete(id):

    mysql = connectToMySQL('mydb')
    query = ("DELETE FROM messages WHERE (idmessages = %(del)s) and recepient_id = %(rid)s")
    data = {
        'del' : id,
        'rid':session['userid']
    }

    new_delete = mysql.query_db(query,data)

    return redirect('/thewall')

@app.route("/logout")

def logout():

	session.clear()
	print(session)
	flash("You have been logged out.","flashlogout")
	return redirect ("/")

if __name__ == "__main__":
	app.run(debug=True)