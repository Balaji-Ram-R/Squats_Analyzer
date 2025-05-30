import gradio as gr
import mediapipe as mp
import cv2
import numpy as np
import tempfile
import os
import warnings

warnings.filterwarnings('ignore')

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    return angle

def check_squat_feedback(landmarks):
    left_hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x, landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y]
    left_knee = [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x, landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y]
    left_ankle = [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x, landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]

    right_hip = [landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y]
    right_knee = [landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].y]
    right_ankle = [landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y]

    left_angle = calculate_angle(left_hip, left_knee, left_ankle)
    right_angle = calculate_angle(right_hip, right_knee, right_ankle)
    avg_angle = (left_angle + right_angle) / 2

    if avg_angle < 80:
        feedback = "Too Low! Raise Your Hips"
    elif 80 <= avg_angle <= 110:
        feedback = "Perfect Squat!"
    elif 110 < avg_angle <= 140:
        feedback = "Almost There! Go Lower"
    else:
        feedback = "Too High! Lower Your Hips"

    accuracy = max(0, min(100, (1 - abs(avg_angle - 95) / 50) * 100))
    return feedback, int(accuracy)

def analyze_squats(video_file):
    pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

    cap = cv2.VideoCapture(video_file)
    frame_width, frame_height = int(cap.get(3)), int(cap.get(4))
    fps = cap.get(cv2.CAP_PROP_FPS) if cap.get(cv2.CAP_PROP_FPS) > 0 else 30

    temp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    output_path = temp_output.name
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(image)
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        if results.pose_landmarks:
            mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            landmarks = results.pose_landmarks.landmark
            feedback, accuracy = check_squat_feedback(landmarks)

            color = (0, 255, 0) if "Perfect" in feedback else (0, 0, 255)
            cv2.putText(image, feedback, (50, 50), cv2.FONT_HERSHEY_COMPLEX, 1, color, 2)

        out.write(image)

    cap.release()
    out.release()
    return output_path

interface = gr.Interface(
    fn=analyze_squats,
    inputs=gr.Video(label="Upload Your Squat Video"),
    outputs=gr.Video(label="Analyzed Output"),
    title="Squat Form Analyzer",
    description="Upload a video of your squats, and get feedback on your form!"
)

# For Hugging Face and Render, no need for manual server_name/server_port
interface.launch()
