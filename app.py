from flask import Flask,redirect,session,render_template, url_for, request
from youtube_transcript_api import YouTubeTranscriptApi as yt
from flask_mail import Mail, Message
import sqlite3 as sql
import re
import markdown
import pyttsx3
import google.generativeai as genai

import pyttsx3
text_speech = pyttsx3.init()


app = Flask(__name__)
genai.configure(api_key="AIzaSyDz-PKuG1g2zZiXoJOfwe0oDbaKDBBVjok")
app.secret_key = 'YTsummarizer_key'
# Set up the model
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 0,
    "max_output_tokens": 8192,
}

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
    },
]

model = genai.GenerativeModel(
    model_name="gemini-1.5-pro-latest",
    generation_config=generation_config,
    safety_settings=safety_settings,
)

convo = model.start_chat(history=[])


app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'ytsummarizerofficial@gmail.com'
app.config['MAIL_PASSWORD'] = 'lvkb cids eyoz gnym'
app.config['MAIL_DEFAULT_SENDER'] = 'ytsummarizerofficial@gmail.com'
mail = Mail(app)

@app.route('/send-mail/',methods=['POST','GET'])
def send_mail():
    if request.method == "POST":
        try:
            f_user = request.form["f_user"]
            with sql.connect("database.db") as conn:
                    curr = conn.cursor()
                    curr.execute("SELECT * FROM auth WHERE username = ?",(f_user,))
                    f_pass = curr.fetchall()
                    conn.close()
                    if f_pass:
                        row  = f_pass[0]
                        username = row[0]
                        password = row[1]
                        email = row[2]
                        m = f'Password Reminder for Your YT Summarizer Account, {username}'
                        b = f'''
                        Dear {username},

                        We received a request to remind you of your password for your YT Summarizer account. Your current password is provided below.

                        Your password: {password}

                        Please ensure to keep your password secure and do not share it with anyone. If you did not request this reminder, please contact our support team immediately.

                        Thank you for your attention to this matter.

                        Best regards,

                        Team YT Summarizer
                        '''
                        msg = Message(m,
                                      recipients=[email])
                        msg.body = b
                        mail.send(msg)
                        
                        return redirect(url_for('login'))
                    else:
                        return '<h1>Invalid user not found</h1>'
        except:
            err = 'err'
    return redirect(url_for('login'))



@app.route("/login")
def login():
    if not ('logged_in' in session and session['logged_in']):
        return render_template('login.html')
    else:
        return redirect(url_for('home'))



@app.route("/signupreg")
def registration():
    return render_template('signup.html')
@app.route("/signup",methods = ['POST','GET'])
def signup():
    if request.method == "POST":
        try:
            r_user = request.form["username"]
            r_pas = request.form["password"]
            r_email = request.form["email"]
            with sql.connect("database.db") as conn:
                curr = conn.cursor()
                curr.execute("INSERT OR REPLACE INTO auth (username,password,email) VALUES(?,?,?)",(r_user,r_pas,r_email))
                conn.commit()
        except:
            conn.rollback()
        conn.close()
    return redirect(url_for('login'))
@app.route("/verify",methods = ['POST','GET'])
def verify():
    if request.method == "POST":
        pas = ""
        try:
            global user
            user = request.form["username"]
            pas = request.form["password"]
            with sql.connect("database.db") as conn:
                curr = conn.cursor()
                curr.execute(
                    "CREATE TABLE IF NOT EXISTS auth (username TEXT NOT NULL PRIMARY KEY,password TEXT NOT NULL,email TEXT NOT NULL)"
                )
                conn.commit()
                curr.execute("SELECT password FROM auth WHERE username = ?",(user,))
                d_pas = curr.fetchall()
                conn.close()
        except:
            print("Error occured")
        try:
            if pas == d_pas[0][0]:
                session['logged_in'] = True
                session['username'] =  user
                with sql.connect("database.db") as con:
                        cur = con.cursor()
                        cur.execute(
                            f"CREATE TABLE IF NOT EXISTS {session['username']} (lnk TEXT NOT NULL PRIMARY KEY,info TEXT NOT NULL)"
                        )
                        con.commit()
                return redirect(url_for('home'))
            else:
                return redirect(url_for('login'))
        except:
            return redirect(url_for('login'))
    return redirect(url_for('login'))







@app.route("/", methods=["POST", "GET"])
def home():
    if 'logged_in' in session and session['logged_in']:
        if request.method == "POST":
            try:
                lnk = request.form["url"]
                lnk = lnk.split("=")
                v_id = lnk[1]
                data = yt.get_transcript(v_id)
                transcript = ""
                for value in data:
                    for key, val in value.items():
                        if key == "text":
                            transcript += val
                l = transcript.splitlines()
                final_text = "##summarize the below youtube subtitles##" + " ".join(l)
                convo.send_message(final_text)
                final_text = markdown.markdown(convo.last.text)
                
            except:
                final_text = "There is some problem in the URL please cross check it or UnAvailble for this video"
            try:
                    with sql.connect("database.db") as con:
                        cur = con.cursor()
                        cur.execute(
                            f"CREATE TABLE IF NOT EXISTS {session['username']} (lnk TEXT NOT NULL PRIMARY KEY,info TEXT NOT NULL)"
                        )
                        con.commit()
                        cur.execute(f"INSERT OR REPLACE INTO {session['username']} (lnk,info) VALUES (?,?)", (v_id, final_text))
                        con.commit()
            except:
                    con.rollback()
            con.close()
        final_text = "Try by entering some url"

        con = sql.connect("database.db")
        # con.row_factory = sql.Row

        cur = con.cursor()
        cur.execute(f"SELECT * FROM {session['username']}")
        rows = cur.fetchall()
        # con.close()
        return render_template("home.html", rows=rows,u=session['username'])
    return redirect(url_for('login'))

@app.route('/delete',methods=["POST","GET"])
def delete():
    if 'logged_in' in session and session['logged_in']:
        if request.method == "POST":
            try:
                url = request.form['link']
                with sql.connect("database.db") as conn:
                    curr = conn.cursor()
                curr.execute(f"DELETE FROM {session['username']} WHERE lnk = ?",(url,))
                conn.commit()
            except:
                err='err'
        return redirect(url_for('home'))


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
