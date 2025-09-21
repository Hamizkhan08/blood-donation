from flask import Flask, render_template, request, redirect, session, flash, url_for
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
app = Flask(__name__)
app.secret_key = "supersecretkey"

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'hamiz.afkhan@gmail.com'
app.config['MAIL_PASSWORD'] = 'oxxl ugfb ykus jtih'  # Use App Password (not main password)

mail = Mail(app)

# MySQL connection
def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",          # change if needed
        password="",          # your MySQL password
        db="bloodfinder",
        cursorclass=pymysql.cursors.DictCursor
    )

def get_request_by_id(req_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM blood_requests WHERE id=%s", (req_id,))
    req = cur.fetchone()
    cur.close()
    conn.close()
    return req

def send_email_alert(to_email, subject, body):
    msg = Message(subject, sender=app.config['MAIL_USERNAME'], recipients=[to_email])
    msg.body = body
    mail.send(msg)

# ---------------- USER HOME ----------------
@app.route('/')
def home():
    if "user_id" in session:
        return render_template("home.html", name=session["name"])
    elif "admin_id" in session:
        return redirect("/admin/dashboard")
    return redirect("/login")

# ---------- REGISTER ----------
@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        blood_group = request.form["blood_group"]
        location = request.form["location"]
        contact = request.form["contact"]

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users (name, email, password, blood_group, location, contact) VALUES (%s,%s,%s,%s,%s,%s)",
                (name, email, password, blood_group, location, contact)
            )
            conn.commit()
            flash("Registration successful! Please login.", "success")
            return redirect("/login")
        except Exception as e:
            flash("Error: " + str(e), "danger")
        finally:
            cur.close()
            conn.close()
    return render_template("register.html")

# ---------- LOGIN ----------
@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            flash("Login successful!", "success")
            return redirect("/")
        else:
            flash("Invalid email or password", "danger")
    return render_template("login.html")

# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect("/login")

# ---------- SEARCH DONORS ----------
@app.route('/search', methods=["GET", "POST"])
def search():
    donors = []
    if request.method == "POST":
        blood_group = request.form["blood_group"]
        location = request.form["location"]

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT name, blood_group, location, contact, verified FROM users WHERE blood_group=%s AND location LIKE %s",
            (blood_group, "%" + location + "%")
        )
        donors = cur.fetchall()
        cur.close()
        conn.close()

    return render_template("search.html", donors=donors)

# ---------- REQUEST BLOOD ----------
@app.route('/request_blood', methods=["GET", "POST"])
def request_blood():
    if request.method == "POST":
        requester_name = request.form["name"]
        blood_group = request.form["blood_group"]
        location = request.form["location"]
        contact = request.form["contact"]
        message = request.form["message"]

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO blood_requests (requester_name, blood_group, location, contact, message) VALUES (%s,%s,%s,%s,%s)",
            (requester_name, blood_group, location, contact, message)
        )
        conn.commit()
        cur.close()
        conn.close()

        flash("Blood request submitted successfully!", "success")
        return redirect("/")

    return render_template("request_blood.html")

# ---------- ADMIN LOGIN ----------
@app.route('/admin/login', methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM admins WHERE username=%s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and user["password"] == password:  # or hashed check
            session["admin_id"] = user["id"]
            session["admin_name"] = user["username"]
            flash("Login successful!", "success")
            return redirect("/admin/dashboard")
        else:
            flash("Invalid admin credentials", "danger")
    return render_template("admin_login.html")

# ---------- ADMIN DASHBOARD ----------
@app.route('/admin/dashboard')
def admin_dashboard():
    if "admin_id" not in session:
        return redirect("/admin/login")

    conn = get_db_connection()
    cur = conn.cursor()

    # Pending donors
    cur.execute("SELECT * FROM users WHERE verified=0")
    pending_donors = cur.fetchall()

    # Pending blood requests
    cur.execute("SELECT * FROM blood_requests WHERE approved=0")
    pending_requests = cur.fetchall()

    # Approved requests (history)
    cur.execute("SELECT * FROM blood_requests WHERE approved=1")
    approved_requests = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "admin_dashboard.html",
        donors=pending_donors,
        pending_requests=pending_requests,
        approved_requests=approved_requests
    )

# ---------- VERIFY DONOR ----------
@app.route('/admin/verify_donor/<int:user_id>')
def verify_donor(user_id):
    if "admin_id" not in session:
        return redirect("/admin/login")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET verified=1 WHERE id=%s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Donor verified successfully!", "success")
    return redirect("/admin/dashboard")

# ---------- APPROVE BLOOD REQUEST ----------
@app.route('/admin/approve_request/<int:request_id>')
def approve_request(request_id):
    if "admin_id" not in session:
        return redirect("/admin/login")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE blood_requests SET approved=1 WHERE id=%s", (request_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Blood request approved successfully!", "success")
    return redirect("/admin/dashboard")

# ---------- REJECT BLOOD REQUEST ----------
@app.route('/admin/reject_request/<int:request_id>')
def reject_request(request_id):
    if "admin_id" not in session:
        return redirect("/admin/login")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM blood_requests WHERE id=%s", (request_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Blood request rejected/removed.", "info")
    return redirect("/admin/dashboard")


@app.route("/send_alert/<int:req_id>")
def send_alert(req_id):
    req = get_request_by_id(req_id)
    if not req:
        flash("Request not found.", "danger")
        return redirect(url_for("admin_dashboard"))

    subject = f"EMERGENCY: {req['blood_group']} Blood Needed!"
    body = f"""
Urgent request for {req['blood_group']} blood.
Patient: {req['requester_name']}
Location: {req['location']}
Contact: {req['contact']}
Message: {req['message']}
"""

    # Fetch all verified donors with the required blood group
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT email FROM users WHERE blood_group=%s AND verified=1",
        (req['blood_group'].strip(),)  # remove any spaces
    )
    donors = cur.fetchall()
    cur.close()
    conn.close()

    if not donors:
        flash("No verified donors with that blood group found!", "warning")
        return redirect(url_for("admin_dashboard"))

    # Send email to each donor
    print("Sending alert to the following emails:")
    for donor in donors:
        email = donor.get('email')
        if email:
            send_email_alert(email.strip(), subject, body)

    flash(f"Emergency email alert sent to {len(donors)} donors!", "success")
    return redirect(url_for("admin_dashboard"))




if __name__ == "__main__":
    app.run(debug=True)
