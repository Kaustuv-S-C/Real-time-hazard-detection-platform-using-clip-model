import clip
import cv2
import numpy as np
import torch
import yaml
from PIL import Image
from datetime import datetime
import sys

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

def write_detection_to_file(hazard, new_confidence):
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
            start = line.find("(Confidence: ") + len("(Confidence: ")
            end = line.find(")", start)
            existing_confidence = float(line[start:end])

            # Compare the new confidence with the existing one
            if new_confidence > existing_confidence:
                # Update the line with the new higher confidence and current timestamp
                updated_lines.append(f"{hazard} (Confidence: {new_confidence:.2f}) detected at: {current_time}\n")
                file_updated = True
            # If the new confidence is not higher, do not update
        else:
            # If the line does not contain the hazard, keep it as is
            updated_lines.append(line)

    # If the hazard was not found, append a new detection
    if not file_updated:
        updated_lines.append(f"{hazard} (Confidence: {new_confidence:.2f}) detected at: {current_time}\n")

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
    if confidence >= threshold:
        return labels[label_index], confidence

# Main function for detecting hazards
def main():
    # Create a VideoCapture object
    cap = cv2.VideoCapture(0)  # Use 0 for the default camera

    # Check if the webcam is opened correctly
    if not cap.isOpened():
        raise IOError("Cannot open webcam")

    while True:
        ret, frame = cap.read()
        if not ret:
            break  # Break the loop if there are no frames to read

        # Detect hazards in the frame
        detection = detect_hazards(frame)
        if detection:
            hazard, confidence = detection
            write_detection_to_file(hazard, confidence)

        # Display the resulting frame
            cv2.imshow('frame', frame)

        # Press 'q' to exit the loop
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release the VideoCapture object and close all windows
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
