from threading import Lock
import re
import os
from flask import Flask, render_template, request, make_response, redirect, url_for


app = Flask(__name__)
lock = Lock()

if "SUPPORT_EMAIL" in os.environ:
    support_mail_address = os.environ["SUPPORT_EMAIL"]
else:
    support_mail_address = ""

if "EMAIL_FILE_PATH" in os.environ:
    outfile_path = os.environ["EMAIL_FILE_PATH"]
else:
    outfile_path = "/app/db/email_file.txt"

if "REGISTER_TOKEN" in os.environ:
    master_token = os.environ["REGISTER_TOKEN"]
else:
    master_token = "TestToken"


@app.errorhandler(404)
def return404(e):
    headers = {"Content-Type": "text/html"}
    return make_response(
        render_template("404.html", support_mail_address=support_mail_address), 200, headers
    )


@app.route("/")
@app.route("/index")
def index():
    headers = {"Content-Type": "text/html"}
    return make_response(render_template("index.html"), 200, headers)


@app.route("/register", methods=["GET", "POST"])
def register():
    headers = {"Content-Type": "text/html"}
    if request.method == "POST":
        email = request.form.get("email")
        token = request.form.get("token")
        value = request.form.get("check_consent")
        regex_mail = r"""(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9]))\.){3}(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9])|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])"""
        try:
            if re.match(regex_mail, email) and token == master_token and value == "on":
                with lock:
                    with open(outfile_path, "a") as f:
                        f.write(email + "\n")
                    return make_response(
                        render_template("register.html", saved=True), 200, headers
                    )
        except Exception as e:
            print(e)
            return make_response(render_template("register.html", notsaved=True), 200, headers)
    return make_response(render_template("register.html"), 200, headers)


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0")
