import torch
from transformers import AutoModelForVision2Seq, AutoProcessor
from PIL import Image
import cv2
import numpy as np

print("Initializing camera...")
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print("Loading OpenVLA model...")
processor = AutoProcessor.from_pretrained("openvla/openvla-7b", trust_remote_code=True)
model = AutoModelForVision2Seq.from_pretrained(
    "openvla/openvla-7b",
    torch_dtype=torch.float16,
    low_cpu_mem_usage=True,
    trust_remote_code=True
).to("cuda:0")

print("\n" + "="*60)
print("OpenVLA Ready for Robot Control!")
print("="*60)
print("\nExample instructions to try:")
print("  - pick up the red object")
print("  - move to the blue block")
print("  - grasp the cup")
print("  - move left")
print("  - open the gripper")
print("\nControls:")
print("  'p' - Get action prediction for current view")
print("  's' - Save current frame")
print("  'q' - Quit")
print("="*60 + "\n")

frame_count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break
    
    # Convert BGR to RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(frame_rgb)
    
    # Add text overlay
    cv2.putText(frame, "Press 'p' for prediction, 'q' to quit", 
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    # Display frame
    cv2.imshow('OpenVLA Camera Feed', frame)
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('s'):
        filename = f"frame_{frame_count}.jpg"
        cv2.imwrite(filename, frame)
        print(f"Saved {filename}")
        frame_count += 1
    elif key == ord('p'):
        instruction = input("\n🤖 Enter robot instruction: ")
        
        print(f"Processing: '{instruction}'...")
        inputs = processor(instruction, pil_image).to("cuda:0", dtype=torch.float16)
        
        with torch.no_grad():
            action = model.predict_action(**inputs, unnorm_key="bridge_orig", do_sample=False)
        
        print("\n" + "─"*50)
        print(f"📸 Instruction: {instruction}")
        print(f"🎯 Predicted Action Vector: {action}")
        print("─"*50)
        print(f"  📍 Position Delta (xyz): [{action[0]:+.4f}, {action[1]:+.4f}, {action[2]:+.4f}]")
        print(f"  🔄 Rotation Delta (rpy): [{action[3]:+.4f}, {action[4]:+.4f}, {action[5]:+.4f}]")
        print(f"  🤏 Gripper State: {action[6]:.4f} → {'🟢 OPEN' if action[6] > 0.5 else '🔴 CLOSE'}")
        print("─"*50 + "\n")

cap.release()
cv2.destroyAllWindows()
print("\n👋 Shutting down OpenVLA")
