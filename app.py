import re
import os
import json
import random
import smtplib, ssl
import pathlib
import uuid

from enum import Enum
from threading import Lock
from flask import Flask, render_template, request, make_response, redirect, url_for, jsonify
from flask_httpauth import HTTPBasicAuth
from flask_restful import fields, marshal_with
from flask_restful import Resource, Api
from typing import Dict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.security import generate_password_hash, check_password_hash
import jinja2 


app = Flask(__name__)
lock = Lock()
api = Api(app)

### --------------- Read Config --------------- ### 


if "SUPPORT_EMAIL" in os.environ:
    support_mail_address = os.environ["SUPPORT_EMAIL"]
else:
    support_mail_address = ""

if "DATA_FILE_PATH" in os.environ:
    outfile_path = os.environ["DATA_FILE_PATH"]
else:
    outfile_path = os.path.join(pathlib.Path().absolute() , "oe-landingpage/")
email_list_path = os.path.join(outfile_path, "email_file.txt")
quiz_path = os.path.join(outfile_path, "quiz.json")
group_path = os.path.join(outfile_path, "groups.json")
template_path = os.path.join(outfile_path, "mail_to_participants.txt.jinja2")
communication_link_path = os.path.join(outfile_path, "communication_link_path.txt")

if "REGISTER_TOKEN" in os.environ:
    master_token = os.environ["REGISTER_TOKEN"]
else:
    master_token = "TestToken"

if "ADMIN_PASSWORD" in os.environ:
    admin_password = os.environ["ADMIN_PASSWORD"]
else:
    # not the most secure default, but none is
    admin_password = "admin"

if "MAIL_SUBJECT" in os.environ:
    MAIL_SUBJECT = os.environ["MAIL_SUBJECT"]
else:
    MAIL_SUBJECT = "Subject"

if "MAIL_FROM" in os.environ:
    MAIL_FROM = os.environ["MAIL_FROM"]
else:
    MAIL_FROM = "from@example.com"

if "MAIL_PASSWORD" in os.environ:
    MAIL_PASSWORD = os.environ["MAIL_PASSWORD"]
else:
    MAIL_PASSWORD = "password"

if "MAIL_SMTP_SERVER" in os.environ:
    MAIL_SMTP_SERVER = os.environ["MAIL_SMTP_SERVER"]
else:
    MAIL_SMTP_SERVER = "mail.example.com"

if "MAIL_SMTP_SERVER_PORT" in os.environ:
    MAIL_SMTP_SERVER_PORT = int(os.environ["MAIL_SMTP_SERVER_PORT"])
else:
    MAIL_SMTP_SERVER_PORT = 465

### --------------- Authentication --------------- ### 


auth = HTTPBasicAuth()
users = {
    "admin": generate_password_hash(admin_password),
}
del admin_password


@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username


@app.errorhandler(404)
def return404(e):
    headers = {"Content-Type": "text/html"}
    return make_response(
        render_template("404.html.jinja", support_mail_address=support_mail_address), 200, headers
    )


### --------------- API --------------- ### 


class GroupDao(object):
    def __init__(self, access_hash, emails, name, com_link):
        self.access_hash = access_hash
        self.emails = emails
        self.name = name
        self.answers = {}
        self.communicationlink = com_link
        self.points = 0


def get_list_of_communication_links():
    links = []
    with open(communication_link_path, "r") as f:
        while a := f.readline():
            links.append(a.strip())
    return links


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
        Generate groups, given with a minimum size.
        Any overhang will be evenly divided over the groups, starting from the first
        """
        global groups
        size_min = int(request.form["size_min"])

        # get all the email adresses
        emails = []
        with open(email_list_path, "r") as f:
            while a := f.readline():
                if a.strip() != "":
                    emails.append(a.strip())

        # generate groups 
        random.shuffle(emails)
        amount_to_many = len(emails) % size_min
        left_over = emails [:amount_to_many]
        generated_groups = []
        emails = emails[amount_to_many:]
        for i in range(0, len(emails), size_min):
            generated_groups.append(emails[i:i + size_min])
        for i, mail in enumerate(left_over):
            generated_groups[i % len(generated_groups)].append(mail)

        comm_links = get_list_of_communication_links()
        if len(comm_links) < len(generated_groups):
            return make_response(f"Generated {len(groups)}. Not enough communications links, either more of those or larger group size", 400)

        groups = {}
        for i, group in enumerate(generated_groups):
            g = GroupDao(str(uuid.uuid4()), group, f"Group {i}", comm_links[i])
            groups[g.access_hash] = g

        with open(group_path, "w") as f:
            json.dump([groups[g].__dict__ for g in groups], f)
        
        return f"Generated {len(groups)} Groups, with the size distribution of {[len(groups[x].emails) for x in groups]}"


api.add_resource(Groups, "/api/group")


class Group(Resource):
    def get(self, access_hash):
        """
        Get a representaion of the group
        """
        if access_hash in groups:
            q = quiz.get_active_question()
            return make_response(render_template("group.html.jinja", group=groups[access_hash], question=q[0] if len(q) > 0 else None), 200)
        return make_response("Invalid access hash", 403)

    def post(self, access_hash):
        """
        Set the answer for the current question
        """
        global groups
        if access_hash not in groups:
            return make_response("Invalid access hash", 403)
        if "answer" in request.form:
            group = groups[access_hash]
            answer = request.form["answer"]
            question = quiz.get_active_question()
            if len(question) == 0:
                q = quiz.get_active_question()
                return make_response(render_template("group.html.jinja", group=groups[access_hash], question=q[0] if len(q) > 0 else None, error="No question is being played"), 200)
            question = question[0]
            if answer not in question.answers:
                q = quiz.get_active_question()
                return make_response(render_template("group.html.jinja", group=groups[access_hash], question=q[0] if len(q) > 0 else None, error="Invalid answer"), 200)
            group.answers[question.access_hash] = answer
            q = quiz.get_active_question()
            return make_response(render_template("group.html.jinja", group=groups[access_hash], question=q[0] if len(q) > 0 else None, success="Answer saved"), 200)
        if "group_name" in request.form:
            name = request.form["group_name"]
            groups[access_hash].name = name
            q = quiz.get_active_question()
            return make_response(render_template("group.html.jinja", group=groups[access_hash], question=q[0] if len(q) > 0 else None, success="Name saved"), 200)
        return make_response("Missing parameter", 400)

api.add_resource(Group, "/group/<string:access_hash>")


@app.route("/api/mail", methods=["POST"])
@auth.login_required
def send_mails():
    templateLoader = jinja2.FileSystemLoader("/")
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template(template_path)

    context = ssl.create_default_context()
    for x in groups:
        group = groups[x]

        message = MIMEMultipart()
        message["Subject"] = MAIL_SUBJECT
        message["From"] = MAIL_FROM
        message["To"] = "undisclosed"
        text = template.render(group=group)
        textPart = MIMEText(text, 'plain')
        message.attach(textPart)

        with smtplib.SMTP_SSL(MAIL_SMTP_SERVER, MAIL_SMTP_SERVER_PORT, context=context) as server:
            try:
                server.login(MAIL_FROM, MAIL_PASSWORD)  
                server.set_debuglevel(1)
                server.sendmail(MAIL_FROM, group.emails, message.as_string())
            except:
                continue

    return "OK"


class QuestionStatus(Enum):
    NEW = 1
    ACTIVE = 2
    FINISHED = 3


class QuestionDao:
    def __init__(self, access_hash, question, answers, correct):
        self.access_hash = access_hash
        self.question = question
        self.answers = answers
        self.status = QuestionStatus.NEW
        self.correct = correct


class Question(Resource):
    @auth.login_required(optional=True)
    @marshal_with(
        {"question": fields.String, "answers": fields.List(fields.String), "status": fields.String}
    )
    def get(self, access_hash):
        """
        Get a certain question
        """
        if access_hash == "current":
            return jsonify(quiz.get_active_question())
        question = quiz.get_by_access_hash(access_hash)
        user = auth.current_user()
        if user or question.status == QuestionStatus.ACTIVE:
            return question

    @auth.login_required
    def post(self, access_hash):
        """
        Change the question status
        """
        status = request.form.get("status")
        status = QuestionStatus[status]
        if quiz.update_question_status(access_hash, status):
            return make_response("OK", 200)
        return make_response("Could not change status", 400)


api.add_resource(Question, "/api/question/<string:access_hash>")


class QuizDao:
    def __init__(self, questions):
        self.questions = {}
        self.last_finished: QuestionDao = None
        for x in questions:
            q = QuestionDao(**questions[x])
            self.questions[q.access_hash] = q

    def get_by_access_hash(self, access_hash):
        if access_hash in self.questions:
            return self.questions[access_hash]
        return None

    def get_active_question(self):
        return [self.questions[x] for x in self.questions if self.questions[x].status == QuestionStatus.ACTIVE]

    def get_last_finished(self):
        return self.last_finished

    def update_question_status(self, access_hash: str, status: QuestionStatus) -> bool:
        if (question := quiz.get_by_access_hash(access_hash)) == None:
            return False
        if status == QuestionStatus.ACTIVE and len(self.get_active_question()) > 0:
            return False
        question.status = status
        if status == QuestionStatus.FINISHED:
            self.last_finished = question
        return True


def load_quiz_from_disk():
    global quiz
    if os.path.isfile(quiz_path):
        with open(quiz_path, "r") as f:
            quiz = QuizDao(**json.load(f))
            if quiz == None:
                raise Exception(f"Quiz {quiz_path} not loaded correctly")

    else:
        raise Exception(f"Quiz {quiz_path} not found")
    


class Quiz(Resource):
    @auth.login_required
    def get(self):
        """
        Get the entire quiz
        """
        return make_response(render_template("quiz.html.jinja", questions=quiz.questions, QuestionStatus=QuestionStatus), 200)

    @auth.login_required
    def post(self):
        """
        Reloads the quiz from the file
        """
        load_quiz_from_disk()
        return make_response("OK", 200)


api.add_resource(Quiz, "/quiz")


### --------------- Views --------------- ### 

@app.route("/")
@app.route("/index")
def index():
    headers = {"Content-Type": "text/html"}
    return make_response(render_template("index.html.jinja"), 200, headers)


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
                        render_template("register.html.jinja", saved=True), 200, headers
                    )
        except Exception as e:
            print(e)
            return make_response(render_template("register.html.jinja", notsaved=True), 200, headers)
    return make_response(render_template("register.html.jinja"), 200, headers)


@app.route("/admin")
@auth.login_required
def admin():
    headers = {"Content-Type": "text/html"}
    return make_response(render_template("admin.html.jinja"), 200, headers)


@app.route("/question")
def overlay_question():
    q = quiz.get_active_question()
    if len(q) > 0:
        q = q[0]
    else:
        q = quiz.get_last_finished()
    headers = {"Content-Type": "text/html"}
    return make_response(render_template("question.html.jinja", question=q, QuestionStatus=QuestionStatus), 200, headers)


@app.route("/scoreboard")
def scoreboard():
    points = []
    for x in groups:
        group = groups[x]
        p = 0
        for a in group.answers:
            question = quiz.get_by_access_hash(a)
            if question.status == QuestionStatus.FINISHED and question.correct == group.answers[a]:
                p += 1
        points.append((group.name, p))
    headers = {"Content-Type": "text/html"}
    return make_response(render_template("scoreboard.html.jinja", points=list(sorted(points, key=lambda x: x[1], reverse=True))), 200, headers)


### --------------- Main --------------- ### 

quiz = None
groups: Dict[str, GroupDao] = {}

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0")
    
