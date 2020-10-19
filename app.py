import re
import os
import json
from threading import Lock
from flask import Flask, render_template, request, make_response, redirect, url_for, jsonify
from flask_httpauth import HTTPBasicAuth
from flask_restful import Resource, Api
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
lock = Lock()
api = Api(app)

if "SUPPORT_EMAIL" in os.environ:
    support_mail_address = os.environ["SUPPORT_EMAIL"]
else:
    support_mail_address = ""

if "DATA_FILE_PATH" in os.environ:
    outfile_path = os.environ["DATA_FILE_PATH"]
else:
    outfile_path = "/app/db/"
email_list_path = os.path.join(outfile_path, "email_file.txt")
quiz_path = os.path.join(outfile_path, "quiz.json")
group_path = os.path.join(outfile_path, "groups.json")


if "REGISTER_TOKEN" in os.environ:
    master_token = os.environ["REGISTER_TOKEN"]
else:
    master_token = "TestToken"

if "ADMIN_PASSWORD" in os.environ:
    admin_password = os.environ["ADMIN_PASSWORD"]
else:
    # not the most secure default, but none is
    admin_password = "admin"

auth = HTTPBasicAuth()
users = {
    "admin": generate_password_hash(admin_password),
}
del admin_password

quiz = {}
groups = {}
# quiz = {"active_question": None, "questions": {"775b8006-d8e3-49c0-a320-82584bd4e3c0": {"text": "Was?", "options": ["a", "b", "c"], "correct": "b"}}}


@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username


@app.errorhandler(404)
def return404(e):
    headers = {"Content-Type": "text/html"}
    return make_response(
        render_template("404.html", support_mail_address=support_mail_address), 200, headers
    )


@app.route("/admin")
@auth.login_required
def admin():
    headers = {"Content-Type": "text/html"}
    return make_response(render_template("admin.html"), 200, headers)


class Group(Resource):
    def get(self, access_hash):
        """
        Get the page for a certain group, contains a question, if one is active.
        Otherwise just a blank page, that says it works TODO
        """
        try:
            q = quiz["questions"][access_hash]
            del q["correct"]
            return jsonify(q)
        except:
            return make_response("Invalid access hash", 403)

    def post(self, access_hash):
        """
        Change a groups name by the access hash
        """
        global groups
        try:
            if "group_name" in request.form:
                name = request.form["group_name"]
                groups[access_hash]["group"] = name
                return make_response("OK, name changed", 200)
            elif "answer" in request.form:
                name = request.form["answer"]
                # TODO
                return make_response("OK, name changed", 200)
        except:
            return make_response("Invalid access hash", 403)


api.add_resource(Group, "/quiz/group/<string:access_hash>")


class Groups(Resource):
    @auth.login_required
    def get(self):
        """
        Get all the groups
        """
        return jsonify(groups)
    
    @auth.login_required
    def post(self):
        """
        Generate groups TODO
        """
        headers = {"Content-Type": "text/html"}
        return make_response(render_template("generate_groups.html"), 200, headers)



api.add_resource(Group, "/quiz/group")


class Question(Resource):
    @auth.login_required(optional=True)
    def get(self, access_hash):
        """
        Get a certain question
        """
        user = auth.current_user()
        if user or quiz["active_question"] == access_hash:
            q = quiz["questions"][access_hash]
            del q["correct"]
            return jsonify(q)

    @auth.login_required
    def post(self, access_hash):
        """
        Activate a question
        """
        # TODO: activate questions
        return make_response("OK", 200)


api.add_resource(Question, "/quiz/question/<string:access_hash>")


class Quiz(Resource):
    @auth.login_required()
    def get(self):
        """
        Get an admin overview of the quiz
        """
        user = auth.current_user()
        if user:
            headers = {"Content-Type": "text/html"}
            return make_response(render_template("admin_quiz.html", quiz=quiz), 200, headers)
        return make_response("Nope", 403)

    @auth.login_required
    def post(self):
        """
        Reloads the quiz from the file
        """
        global quiz
        if os.path.isfile(quiz_path):
            with open(quiz_path, "r") as f:
                quiz = json.load(f)
        return make_response("OK", 200)


api.add_resource(Quiz, "/quiz")


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
                    with open(email_list_path, "a") as f:
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
