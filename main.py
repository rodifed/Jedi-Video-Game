import cv2
import mediapipe as mp
import datetime
import detectron2

# MediaPipe setup
mp_drawing = mp.solutions.drawing_utils
mp_holistic = mp.solutions.holistic
holistic = mp_holistic.Holistic(
    model_complexity=1,  # You can change to 0 for more speed
    refine_face_landmarks=True,
    enable_segmentation=False
)

cap = cv2.VideoCapture(0)
triple_team = False
clone_margin = 250
num_clones = 2

# Recording setup
recording = False
video_writer = None

# Drawing helpers
def draw_face_mesh(frame, landmarks, offset_x=0, color=(0, 255, 0)):
    h, w, _ = frame.shape
    for lm in landmarks.landmark:
        x = int(lm.x * w + offset_x)
        y = int(lm.y * h)
        cv2.circle(frame, (x, y), 2, color, -1)

def draw_hand(frame, landmarks, connections, offset_x=0, color=(255, 100, 255)):
    h, w, _ = frame.shape
    points = [(int(lm.x * w + offset_x), int(lm.y * h)) for lm in landmarks.landmark]
    for conn in connections:
        p1, p2 = points[conn[0]], points[conn[1]]
        cv2.line(frame, p1, p2, color, 2)
        cv2.circle(frame, p1, 2, color, -1)

def draw_pose(frame, landmarks, connections, offset_x=0, color=(0, 255, 255)):
    h, w, _ = frame.shape
    points = [(int(lm.x * w + offset_x), int(lm.y * h)) for lm in landmarks.landmark]
    for conn in connections:
        p1, p2 = points[conn[0]], points[conn[1]]
        cv2.line(frame, p1, p2, color, 3)
        cv2.circle(frame, p1, 3, (255, 255, 255), -1)
    try:
        s_l, s_r = points[11], points[12]
        h_l, h_r = points[23], points[24]
        cv2.line(frame, s_l, h_l, (0, 200, 255), 2)
        cv2.line(frame, s_r, h_r, (0, 200, 255), 2)
        cv2.line(frame, s_l, s_r, (0, 200, 255), 2)
        cv2.line(frame, h_l, h_r, (0, 200, 255), 2)
    except:
        pass

# Main loop
while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape

    # Process the RGB version
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = holistic.process(rgb)

    # Draw the main person
    if results.face_landmarks:
        draw_face_mesh(frame, results.face_landmarks)
    if results.left_hand_landmarks:
        mp_drawing.draw_landmarks(frame, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
    if results.right_hand_landmarks:
        mp_drawing.draw_landmarks(frame, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
    if results.pose_landmarks:
        mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS)

    # Draw clones
    if triple_team:
        offsets = []
        for i in range(1, (num_clones // 2) + 1):
            offsets.extend([-i * clone_margin, i * clone_margin])
        if num_clones % 2 != 0:
            offsets.append(0)

        for offset in sorted(offsets):
            if results.face_landmarks:
                draw_face_mesh(frame, results.face_landmarks, offset_x=offset)
            if results.left_hand_landmarks:
                draw_hand(frame, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS, offset_x=offset)
            if results.right_hand_landmarks:
                draw_hand(frame, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS, offset_x=offset)
            if results.pose_landmarks:
                draw_pose(frame, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS, offset_x=offset)

    # Handle recording
    if recording and video_writer is not None:
        video_writer.write(frame)

    # UI overlay
    cv2.putText(frame, f"Triple-Team: {'ON' if triple_team else 'OFF'}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0) if triple_team else (0, 0, 255), 2)
    cv2.putText(frame, f"Margin: {clone_margin}", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
    cv2.putText(frame, f"Clones: {num_clones}", (10, 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
    cv2.putText(frame, f"Recording: {'ON' if recording else 'OFF'}", (10, 120),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255) if recording else (100, 100, 100), 2)

    cv2.imshow("Triple-Team: Adjustable Holograms", frame)

    # Keyboard controls
    key = cv2.waitKey(1)
    if key == 27:
        break
    elif key == ord('2'):
        triple_team = not triple_team
    elif key in [ord('+'), ord('=')]:
        clone_margin = max(10, clone_margin - 10)
    elif key in [ord('-'), ord('_')]:
        clone_margin = min(1000, clone_margin + 10)
    elif key == ord(']'):
        num_clones = min(10, num_clones + 1)
    elif key == ord('['):
        num_clones = max(1, num_clones - 1)
    elif key == ord('r'):
        recording = not recording
        if recording:
            now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{now}.mov"
            fourcc = cv2.VideoWriter_fourcc(*'H264')
            fps = 20.0
            video_writer = cv2.VideoWriter(filename, fourcc, fps, (w, h))
            print(f"🔴 Started recording: {filename}")
        else:
            if video_writer:
                video_writer.release()
                video_writer = None
                print("🛑 Stopped recording")
    elif key == ord("q"):
        break

cap.release()
if video_writer:
    video_writer.release()
cv2.destroyAllWindows()
