import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    rows = db.execute("SELECT * FROM accounts WHERE user_id = :id", id = session["user_id"])
    # rows = db.execute("SELECT * FROM users WHERE id = :id", id = session["user_id"])
    username = db.execute("SELECT username FROM users where id = :id", id = session["user_id"])
    Cash = db.execute("SELECT cash FROM users where id = :id", id = session["user_id"])
    return render_template("index.html", rows = rows, Cash = Cash, username = username)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":

        symbol = request.form.get("Symbol")
        shares = request.form.get("Quanitity")
        quote = lookup(symbol)


        # Check that no box was left blank
        if not symbol:
            return apology("You must provide a symbol", 400)

        elif not shares:
            return apology("You must provide the shares of stock", 400)

        # CHeck that value inserted are acceptable
        if quote == None:
            return apology("Please provide a valid stock", 400)
        elif float(shares) <= 0  or shares.isdigit() == False:
            return apology("Please provide a valid number of shares", 400)
        else:
            Total = float(shares) * quote["price"]
            Cash = db.execute("SELECT cash FROM users where id = :id", id = session["user_id"])

            # Check if they have enough cash
            remaining_Cash = Cash[0]["cash"]
            if remaining_Cash <= Total:
                 return apology("You don't have enough money", 400)
            else:
                remaining_Cash = remaining_Cash - Total
                # Insert into transactions database
                db.execute("INSERT INTO Transactions (id, Symbol, Name, Quantity, Price, Total) VALUES (:id, :symbol, :Name, :Shares, :Price, :Total)", id = session["user_id"], symbol = symbol, Name = quote["name"], Shares = shares, Price = quote["price"], Total = Total)
                # Check if stock already exist in Portofolio database
                Check = db.execute("SELECT symbol FROM accounts where symbol = :symbol", symbol = symbol)
                 # If Stock doesn't exist, add stock to portfolio
                if not Check:
                    db.execute("INSERT INTO accounts (user_id, symbol, Name, Quantity) Values (:id, :symbol, :Name, :Shares)", id = session["user_id"], symbol = symbol, Name = quote["name"], Shares = shares)
                # If Stock does exist, Alter table to reflect change
                else:
                    old_Quantity = db.execute("SELECT Quantity FROM accounts where symbol = :symbol", symbol = symbol)
                    Cash2 = old_Quantity[0]["Quantity"]
                    new_Quantity = int(Cash2) + int(shares)
                    db.execute("UPDATE accounts set quantity = :new_Quantity where symbol = :symbol",new_Quantity = new_Quantity ,symbol = symbol)
                    db.execute("UPDATE user set cash = :cash where user_id = :user_id",cash = remaining_Cash, user_id = session["user_id"])

                return render_template("bought.html", Total = Total, quote = quote, Cash = Cash, symbol = symbol, shares = shares,)

    else:
        return render_template("buy.html")



@app.route("/history")
@login_required
def history():
    Cash = db.execute("SELECT cash FROM users where id = :id", id = session["user_id"])
    rows = db.execute("SELECT * FROM purchases WHERE id = :id", id = session["user_id"])
    return render_template("history.html", rows = rows, Cash = Cash)



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("You must provide a symbol", 400)
        else:
            quote = lookup(request.form.get("symbol"))
            if not quote:
                return apology("Stock index not found")

        return render_template("quote_2.html", quote = quote)

    else:
        return render_template("quote.html")




@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Check that all the boxes were filled
        username = request.form.get("username")
        password = request.form.get("password")
        password_Confirm = request.form.get("password_Confirm")
        # Check that username was entered
        if not username:
            return("You must provide a username", 403)
        # Check that a password was entered
        elif not password:
            return("You must provide a password", 403)
        # Check that username was password was entered again
        elif not password_Confirm:
            return("You must provide a password again", 403)

        # Check that both passwords entered match
        if password != password_Confirm:
            return("Passwords don't match", 403)

        #Check that username is available
        rows = db.execute("SELECT username FROM users WHERE username = :username", username = username)

        if len(rows) != 1:
            db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", username = username, hash=generate_password_hash(password))

        #new_user_id = db.execute("SELECT id FROM usere WHERE username = :username", username = username)

        #session["user_id"] = new_user_id
        session["user_id"] = rows[0]["id"]

        return render_template("/")

    else:
        return render_template("/register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":
        symbol = request.form.get("Symbol")
        shares = request.form.get("Quanitity")
        quote = lookup(symbol)


        # Check that no box was left blank
        if not symbol:
            return apology("You must provide a symbol", 400)

        elif not shares:
            return apology("You must provide the shares of stock", 400)

        # CHeck that value inserted are acceptable
        if quote == None:
            return apology("Please provide a valid stock", 400)
        elif float(shares) <= 0  or shares.isdigit() == False:
            return apology("Please provide a valid number of shares", 400)
        else:
            Shares = int(shares) * -1
            Total = Shares * quote["price"]
            Cash = db.execute("SELECT cash FROM users where id = :id", id = session["user_id"])

            db.execute("INSERT INTO purchases (id, Symbol, Name, Quantity, Price, Total) VALUES (:id, :symbol, :Name, :Shares, :Price, :Total )", id = session["user_id"], symbol = symbol, Name = quote["name"], Shares = Shares, Price = quote["price"], Total = Total )
            return render_template("sold.html", Total = Total, quote = quote, Cash = Cash, symbol = symbol, shares = shares,)
        # return render_template("sold.html")
    else:
        Cash = db.execute("SELECT cash FROM users where id = :id", id = session["user_id"])
        rows = db.execute("SELECT * FROM purchases WHERE id = :id", id = session["user_id"])
        return render_template("sell.html", rows = rows, Cash = Cash)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
