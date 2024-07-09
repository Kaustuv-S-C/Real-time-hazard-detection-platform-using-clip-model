# Standard library imports
from datetime import datetime
import os
import sys
import threading
from threading import Lock
# Related third-party imports
import clip
import cv2
from PIL import Image
import numpy as np
import torch
import yaml

global model, preprocess, device, labels, threshold, default_label
device = None
# Global variable to signal video capture loop to stop
stop_capture = False

# Set static target width and height
target_width = 640
target_height = 480

# Global variable to store the video output object
output = None


def capture_video(username, capture_thread_id, socketio, selected_backend=cv2.CAP_ANY):
    global stop_capture, output
    vid_capture = cv2.VideoCapture(0, selected_backend)

    if not vid_capture.isOpened():
        print("Unable to open camera. Exiting.")
        return

    vid_cod = cv2.VideoWriter_fourcc(*'mp4v')
    current_time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    video_folder = 'videos'
    if not os.path.exists(video_folder):
        os.makedirs(video_folder)
    video_filename = f'{username}_{current_time}.mp4'
    output = cv2.VideoWriter(os.path.join(video_folder, video_filename), vid_cod, 20.0, (target_width, target_height))

    while not stop_capture:
        ret, frame = vid_capture.read()
        if ret and frame is not None:
            resized_frame = cv2.resize(frame, (target_width, target_height))
            cv2.imshow("", resized_frame)
            output.write(resized_frame)
            # Detect hazards in the frame
            detection = detect_hazards(frame)
            if detection:
                hazard, confidence = detection
                write_detection_to_file(hazard, confidence)

        if cv2.waitKey(1) & 0xFF == ord('x'):
            break

    if output is not None:
        output.release()
        output = None

    vid_capture.release()
    cv2.destroyAllWindows()


# Function to start video capture
def start_video_capture(username, capture_thread_id, socketio, selected_backend=cv2.CAP_ANY):
    global stop_capture
    stop_capture = False
    global model, preprocess, device, labels, threshold, default_label
    # Load YAML configuration
    with open('settings.yaml', 'r') as file:
        config = yaml.safe_load(file)

    # Load the CLIP model
    device = config['model-settings']['device']
    model_name = config['model-settings']['model-name']
    model, preprocess = clip.load(model_name, device=device)

    # Load labels
    labels = config['label-settings']['labels']
    threshold = config['model-settings']['prediction-threshold']
    default_label = config['label-settings']['default-label']

    # Start video capture in a separate thread
    capture_thread = threading.Thread(target=capture_video, args=(username, capture_thread_id, selected_backend))
    capture_thread.start()

    return capture_thread


# Function to stop video capture
def stop_video_capture():
    global stop_capture
    stop_capture = True




def write_detection_to_file(hazard, new_confidence):
    new_confidence= ((new_confidence - 29)/6)*100
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_updated = False

    # Read the existing detections
    with open('detec.txt', 'r') as file:
        lines = file.readlines()

    # Create a new list for updated lines
    updated_lines = []

    # Check if the hazard is already detected
    for line in lines:
        if hazard in line:
            # Extract the existing confidence from the line
            start = line.find("(Current Confidence: ") + len("(Current Confidence: ")
            end = line.find(")", start)
            existing_confidence = float(line[start:end])

            # Compare the new confidence with the existing one
            if new_confidence > existing_confidence:
                # Update the line with the new higher confidence and current timestamp
                updated_lines.append(f"{hazard} (Current Confidence: {new_confidence:.2f}) detected at: {current_time}\n")
                file_updated = True
            # If the new confidence is not higher, do not update
        else:
            # If the line does not contain the hazard, keep it as is
            updated_lines.append(line)

    # If the hazard was not found, append a new detection
    if not file_updated:
        updated_lines.append(f"{hazard} (Current Confidence: {new_confidence:.2f}) detected at: {current_time}\n")

    # Write the updated detections back to the file
    with open('detec.txt', 'w') as file:
        file.writelines(updated_lines)


# Function to detect hazards
def detect_hazards(frame):

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = Image.fromarray(frame_rgb)

    # Preprocess the frame
    image = preprocess(frame).unsqueeze(0).to(device)

    # Get image features
    with torch.no_grad():
        image_features = model.encode_image(image)

    # Get text features for labels
    text = ["a photo of " + label for label in labels]
    text = clip.tokenize(text).to(device)
    with torch.no_grad():
        text_features = model.encode_text(text)

    # Compute similarity scores
    similarity = image_features @ text_features.T
    values, indices = similarity[0].topk(1)

    # Get predicted label and confidence
    label_index = indices[0].cpu().item()
    confidence = values[0].cpu().item()
    if confidence >= threshold and confidence > 29:
        return labels[label_index], confidence
    
