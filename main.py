from random import random
from flask import Flask, render_template
from flask import request, redirect, url_for, Response, flash
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
import os
import cv2
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db, storage
from detection.face_recognition import detect_faces, align_face
from detection.face_recognition import extract_features, match_face
from mqtt_modules.face_detect import *
from mqtt_modules.hardware import *
from utils.configuration import load_yaml
# mqtt
import time
import sys
import numpy as np
import base64
from PIL import Image
from Adafruit_IO import MQTTClient
from datetime import date, datetime
import io
import imghdr
import threading

# flask app
config_file_path = load_yaml("configs/database.yaml")

TEACHER_PASSWORD_HASH = config_file_path["teacher"]["password_hash"]
print(TEACHER_PASSWORD_HASH)

# Initialize Firebase
cred = credentials.Certificate(config_file_path["firebase"]["pathToServiceAccount"])
firebase_admin.initialize_app(
    cred,
    {
        "databaseURL": config_file_path["firebase"]["databaseURL"],
        "storageBucket": config_file_path["firebase"]["storageBucket"],
    },
)


def upload_database(filename):
    """
    Checks if a file with the given filename already exists in the
    database storage, and if not, uploads the file to the database.
    """
    valid = False
    # If the fileName exists in the database storage, then continue
    if storage.bucket().get_blob(filename):
        valid = True
        error = f"<h1>{filename} already exists in the database</h1>"

    # First check if the name of the file is a number
    if not filename[:-4].isdigit():
        valid = True
        error = f"<h1>Please make sure that the name of the {filename} is a number</h1>"

    if not valid:
        # Image to database
        filename = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        bucket = storage.bucket()
        blob = bucket.blob(filename)
        blob.upload_from_filename(filename)
        error = None

    return valid, error


def match_with_database(img, database):
    '''The function "match_with_database" takes an image and a database as input, detects faces in the
    image, aligns and extracts features from each face, and matches the face to a face in the database.
    '''
    global match
    # Detect faces in the frame
    faces = detect_faces(img)

    # Draw the rectangle around each face
    for x, y, w, h in faces:
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 4)

    # save the image
    cv2.imwrite("static/recognized/recognized.png", img)

    for face in faces:
        try:
            # Align the face
            aligned_face = align_face(img, face)

            # Extract features from the face
            embedding = extract_features(aligned_face)

            embedding = embedding[0]["embedding"]

            # Match the face to a face in the database
            match = match_face(embedding, database)

            if match is not None:
                return f"Match found: {match}"
            else:
                return "No match found"
        except:
            return "No face detected"
        # break # TODO: remove this line to detect all faces in the frame


app = Flask(__name__, template_folder="template")
app.secret_key = "123456"  # Add this line

# Specify the directory to save uploaded images
UPLOAD_FOLDER = "static/images"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/add_info")
def add_info():
    return render_template("add_info.html")


@app.route("/teacher_login", methods=["GET", "POST"])
def teacher_login():
    if request.method == "POST":
        password = request.form.get("password")
        if check_password_hash(TEACHER_PASSWORD_HASH, password):
            return redirect(url_for("attendance"))
        else:
            flash("Incorrect password")
    return render_template("teacher_login.html")


@app.route("/attendance")
def attendance():
    ref = db.reference("Students")
    number_student = len(ref.get())
    # attandence
    students = {}
    for i in range(1, number_student):
        studentInfo = db.reference(f"Students/{i}").get()
        students[i] = [
            studentInfo["name"],
            studentInfo["email"],
            studentInfo["userType"],
            studentInfo["classes"],
        ]
    return render_template("attendance.html", students=students)


@app.route("/upload", methods=["POST"])
def upload():
    global filename
    # Check if a file was uploaded
    if "file" not in request.files:
        return "No file uploaded", 400

    file = request.files["file"]

    # Check if the file is one of the allowed types/extensions
    if file.filename == "":
        return "No selected file", 400

    if file and allowed_file(file.filename):
        # Make the filename safe, remove unsupported chars
        filename = secure_filename(file.filename)
        # change the name of the file to the studentId
        # Information to database
        ref = db.reference("Students")
        try:
            # Obtain the last studentId number from the database
            studentId = len(ref.get())
        except TypeError:
            studentId = 1

        filename = f"{studentId}.png"

        # Move the file from the temporal folder to
        # the upload folder we setup
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        # Upload the file to the database
        val, err = upload_database(filename)

        if val:
            return err

        # Redirect the user to the uploaded_file route, which
        # will basically show on the browser the uploaded file
        return redirect(url_for("add_info"))

    return "File upload failed", 400


def allowed_file(filename):
    # Put your allowed file types here
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")  # for browser cache
    # Generate the URL of the image
    url = url_for("static", filename="images/" + filename, v=timestamp)
    # Return an HTML string that includes an <img> tag
    return f'<h1>File uploaded successfully</h1><img src="{url}" alt="Uploaded image">'


@app.route("/video_feed")
def video_feed():
    return Response(gen_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/capture", methods=["POST"])
def capture():
    global filename
    ret, frame = video.read()
    if ret:
        # Information to database
        ref = db.reference("Students")

        try:
            # Obtain the last studentId number from the database
            studentId = len(ref.get())

        except TypeError:
            studentId = 1

        # Save the image
        filename = f"{studentId}.png"
        # Save the frame as an image
        cv2.imwrite(os.path.join(app.config["UPLOAD_FOLDER"], filename), frame)

        # Upload the file to the database
        val, err = upload_database(filename)

        if val:
            return err
    # Redirect to the success page
    return redirect(url_for("add_info"))


@app.route("/success/<filename>")
def success(filename):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")  # for browser cache
    # Generate the URL of the image
    url = url_for("static", filename="images/" + filename, v=timestamp)
    # Return an HTML string that includes an <img> tag
    return f'<h1>{filename} image uploaded successfully to the database</h1><img src="{url}" alt="Uploaded image">'


@app.route("/submit_info", methods=["POST"])
def submit_info():
    # Get the form data
    name = request.form.get("name")
    email = request.form.get("email")
    userType = request.form.get("userType")
    classes = request.form.getlist("classes")  # Get all selected classes
    password = request.form.get("password")

    # Get the last uploaded image
    studentId, _ = os.path.splitext(filename)
    fileName = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    data = cv2.imread(fileName)

    # Detect faces in the image
    faces = detect_faces(data)

    for face in faces:
        # Align the face
        aligned_face = align_face(data, face)

        # Extract features from the face
        embedding = extract_features(aligned_face)
        break

    # Add the information to the database
    ref = db.reference("Students")
    data = {
        str(studentId): {
            "name": name,
            "email": email,
            "userType": userType,
            "classes": {class_: int("0") for class_ in classes},
            "password": password,
            "embeddings": embedding[0]["embedding"],
        }
    }

    for key, value in data.items():
        ref.child(key).set(value)

    return redirect(url_for("success", filename=filename))


@app.route("/recognize", methods=["GET", "POST"])
def recognize():
    global detection
    ret, frame = video.read()
    if ret:
        # Information to database
        ref = db.reference("Students")
        # Obtain the last studentId number from the database
        number_student = len(ref.get())
        print("There are", (number_student - 1), "students in the database")

        database = {}
        for i in range(1, number_student):
            studentInfo = db.reference(f"Students/{i}").get()
            studentName = studentInfo["name"]
            studentEmbedding = studentInfo["embeddings"]
            database[studentName] = studentEmbedding

        detection = match_with_database(frame, database)

    # Return a successful response
    return redirect(url_for("select_class"))


@app.route("/select_class", methods=["GET", "POST"])
def select_class():
    if request.method == "POST":
        # Get the selected class from the form data
        selected_class = request.form.get("classes")

        # Generate the URL of the image
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")  # for browser cache
        url = url_for("static", filename="recognized/recognized.png", v=timestamp)

        # Information to database
        ref = db.reference("Students")
        # Obtain the last studentId number from the database
        number_student = len(ref.get())

        for i in range(1, number_student):
            studentInfo = db.reference(f"Students/{i}").get()
            if match == studentInfo["name"]:
                # Check if the selected class is in the list of studentInfo['classes']
                print(studentInfo["classes"])
                if selected_class in studentInfo["classes"]:
                    # Update the attendance in the database
                    ref.child(f"{i}/classes/{selected_class}").set(
                        int(studentInfo.get("classes", {}).get(selected_class)) + 1
                    )
                    # Render the template, passing the detection result and image URL
                    return f'<h2>Selected Class: {selected_class} - {detection}</h2><img src="{url}" alt="Recognized face">'
                else:
                    return f'<h2>Student not in class - {detection}</h2><img src="{url}" alt="Recognized face">'
    else:
        # Render the select class page
        return render_template("select_class.html")


def gen_frames():
    global video
    video = cv2.VideoCapture(0)
    while True:
        success, frame = video.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode(".jpg", frame)
            frame = buffer.tobytes()
        yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")


# mqtt
AIO_FEED_ID = ["Today", "Time", "Humidity", "Temperature", "General_Vision", "AI_Camera", "Button", "number_student"]
AIO_USERNAME = "NhanVGU"
AIO_KEY = ""


def connected(client):
    print("Connected to server!!!")
    for things in AIO_FEED_ID:
        client.subscribe(things)


def subscribe(client, userdata, mid, granted_qos):
    print("Subscribe successfully ...")


def disconnected(client):
    print("Disconnected ...")
    sys.exit(1)


def message(client, feed_id, payload):
    print(f"AI result from {feed_id} : {payload}")
    if feed_id == "Button":
        values.append(payload)
        write_to_file(values, "data.txt")


client = MQTTClient(AIO_USERNAME, AIO_KEY)
client.on_connect = connected
client.on_disconnect = disconnected
client.on_message = message
client.on_subscribe = subscribe
client.connect()
client.loop_background()


def humidity():
    value = random.randint(40, 80)
    return value


def temperature():
    value1 = random.randint(14, 40)
    return value1


turn_on = turn_on_AC()
client.publish("Button", turn_on)
check = 1
values = [1]
write_to_file(values, "data.txt")


def mqtt():
    global check, chatbot
    while True:
        now = datetime.now()
        today = date.today()
        humi = humidity()
        tem = temperature()
        view = view1()
        face = faces()
        # Information to database
        ref = db.reference("Students")
        # Obtain the last studentId number from the database
        number_student = len(ref.get())
        number_stu = f"There are {number_student - 1} students in the database"

        # publish
        client.publish("Time", now.strftime("%H hours %M minutes %S seconds"))
        client.publish("Today", today.strftime("%B %d, %Y"))
        client.publish("General_Vision", view)
        client.publish("AI Camera", face)
        client.publish("Humidity", humi)
        client.publish("Temperature", tem)
        client.publish("number_student", number_stu)
        if tem <= 20:
            if check != 0:
                client.publish("Button", 0)
                check = 0
        if tem > 20:
            if check != 1:
                client.publish("Button", 1)
                check = 1
        time.sleep(30)

# thread for mqtt
def run_mqtt():
    mqtt_thread = threading.Thread(target=mqtt)
    mqtt_thread.daemon = True
    mqtt_thread.start()

if __name__ == "__main__":
    run_mqtt()
    app.run(debug=True)
