import os
import cv2
import numpy as np
import base64
import urllib.request

CLASSES = [
    "background", "aeroplane", "bicycle", "bird", "boat",
    "bottle", "bus", "car", "cat", "chair", "cow",
    "diningtable", "dog", "horse", "motorbike", "person",
    "pottedplant", "sheep", "sofa", "train", "tvmonitor"
]

def download_model_files(model_dir):
    prototxt_url = "https://raw.githubusercontent.com/chuanqi305/MobileNet-SSD/master/voc/MobileNetSSD_deploy.prototxt"
    model_url = "https://raw.githubusercontent.com/shixiangan/MobileNet-SSD/master/mobilenet_iter_73000.caffemodel"
    
    prototxt_path = os.path.join(model_dir, "MobileNetSSD_deploy.prototxt")
    model_path = os.path.join(model_dir, "mobilenet_iter_73000.caffemodel")
    
    if not os.path.exists(prototxt_path):
        print("Downloading MobileNet-SSD prototxt...")
        urllib.request.urlretrieve(prototxt_url, prototxt_path)
    if not os.path.exists(model_path):
        print("Downloading MobileNet-SSD model weights...")
        urllib.request.urlretrieve(model_url, model_path)
        
    return prototxt_path, model_path

def detect_objects_locally(image_base64: str) -> str:
    try:
        # Resolve model directory in python_backend
        base_dir = os.path.dirname(os.path.dirname(__file__))
        model_dir = os.path.join(base_dir, "models")
        os.makedirs(model_dir, exist_ok=True)
        
        prototxt_path, model_path = download_model_files(model_dir)
        
        # Decode base64 image
        img_data = base64.b64decode(image_base64)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return "Failed to decode captured image."
            
        # Load DNN
        net = cv2.dnn.readNetFromCaffe(prototxt_path, model_path)
        
        # Prep blob
        blob = cv2.dnn.blobFromImage(cv2.resize(img, (300, 300)), 0.007843, (300, 300), 127.5)
        net.setInput(blob)
        detections = net.forward()
        
        detected_objects = []
        for i in range(0, detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > 0.45:  # confidence threshold
                class_id = int(detections[0, 0, i, 1])
                label = CLASSES[class_id]
                if label != "background":
                    detected_objects.append(label)
                    
        if not detected_objects:
            return "No objects detected locally."
            
        # Group duplicates
        grouped = {}
        for obj in detected_objects:
            grouped[obj] = grouped.get(obj, 0) + 1
            
        summary = ", ".join([f"{count} {obj}" for obj, count in grouped.items()])
        return f"I detected: {summary}."
    except Exception as e:
        print(f"Error during local object detection: {e}")
        return f"Local object detection failed: {str(e)}"
