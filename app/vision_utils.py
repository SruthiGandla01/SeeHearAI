from PIL import Image
import cv2
import torch
from transformers import BlipProcessor, BlipForConditionalGeneration
from ultralytics import YOLO

device = 'cuda' if torch.cuda.is_available() else 'cpu'
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(device)
yolo_model = YOLO("yolov8n.pt")

def detect_frame_caption(frame):
    # YOLO
    yolo_results = yolo_model.predict(frame)[0]
    objects = list(set([yolo_results.names[int(cls)] for cls in yolo_results.boxes.cls.tolist()]))

    # BLIP
    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    inputs = processor(image, return_tensors="pt").to(device)
    out = blip_model.generate(**inputs)
    caption = processor.decode(out[0], skip_special_tokens=True)

    full_caption = f"{caption}. Detected objects: {', '.join(objects)}."
    return full_caption
