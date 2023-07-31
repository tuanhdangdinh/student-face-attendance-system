import numpy as np
import base64
from PIL import Image
import io
import cv2

camera = cv2.VideoCapture(0)


# Compress an image, reducing its quality.
def compress_image(image, quality=25):
    temp_image = Image.fromarray(image)
    buffer = io.BytesIO()
    temp_image.save(buffer, format='JPEG', quality=quality)
    compressed_image = Image.open(buffer)
    return np.array(compressed_image)


# General_Vision
def view1():
    # Grab the webcamera's image.
    ret, image = camera.read()
    resize = cv2.resize(image, (700, 500))
    # Compress image.
    image = compress_image(resize, quality=25)
    res, frame1 = cv2.imencode(" .jpg", image)
    data = base64.b64encode(frame1)
    return data


# Face
def faces():
    # Load the pre-trained Haar Cascade classifier for face detection

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    # Initialize the webcam
    cap = cv2.VideoCapture(0)

    while True:
        # Capture the frame from the webcam
        ret, frame = cap.read()

        # Convert the frame to grayscale (face detection works on grayscale images)
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect faces in the frame
        faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.3, minNeighbors=5, minSize=(30, 30))

        # Draw rectangles around the detected faces
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            # crop face
            face_roi = frame[y:y + h, x:x + w]

            resize = cv2.resize(face_roi, (500, 500))
            # Compress image.
            image = compress_image(resize, quality=25)
            res, frame = cv2.imencode(" .jpg", image)
            data = base64.b64encode(frame)
            return data
