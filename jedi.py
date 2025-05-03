import cv2
import mediapipe as mp
import numpy as np
import random
import time
import json
import os
import math
import pygame

# ========== SOUNDS ==========
pygame.mixer.init()
swing_sound = pygame.mixer.Sound(os.path.join("sounds", "swing.wav"))


# ========== CONFIG ==========
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "blade_colors": {
        "right": [0, 0, 255],
        "left": [0, 255, 0]
    },
    "high_score": 0
}

if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(DEFAULT_CONFIG, f)

with open(CONFIG_FILE, 'r') as f:
    config = json.load(f)

blade_colors = config['blade_colors']
high_score = config['high_score']

# ========== SETUP ==========
mp_pose = mp.solutions.pose
pose = mp_pose.Pose()
cap = cv2.VideoCapture(0)

state = 'menu'
score = 0
new_high = False
shots = []
shot_interval = 1.5
last_shot_time = time.time()
lives = 3

customizing_side = 'right'
input_color = blade_colors['right'][:]

previous_vector = {
    "left": None,
    "right": None
}

paused = False  # New variable to track if the game is paused

def smooth_direction(previous, current, alpha=0.7):
    if previous is None:
        return current
    angle_prev = math.atan2(previous[1], previous[0])
    angle_curr = math.atan2(current[1], current[0])
    smooth_angle = alpha * angle_curr + (1 - alpha) * angle_prev
    length = math.hypot(current[0], current[1])
    smooth_x = length * math.cos(smooth_angle)
    smooth_y = length * math.sin(smooth_angle)
    return smooth_x, smooth_y

def draw_menu(frame):
    cv2.putText(frame, "JEDI BLADE GAME", (100, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 0), 3)
    cv2.putText(frame, "Press P to Play", (120, 160), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)
    cv2.putText(frame, "Press C to Customize Blade Colors", (120, 210), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (100, 200, 255), 2)
    cv2.putText(frame, "Press Q to Quit", (120, 260), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 2)

def draw_customization_menu(frame, side, color):
    cv2.putText(frame, f"Customize {side.capitalize()} Blade Color", (50, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(frame, f"Current RGB: {color}", (80, 140),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (color[0], color[1], color[2]), 2)
    cv2.putText(frame, "Use keys R/G/B (up: +, down: -)", (80, 200),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
    cv2.putText(frame, "Press ENTER to save, TAB to switch blade, M for Menu", (40, 250),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 2)

def draw_game_over(frame, score, high_score, new_high):
    league = get_league(score)
    cv2.putText(frame, "GAME OVER", (150, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
    cv2.putText(frame, f"Score: {score}", (180, 180), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
    if new_high:
        cv2.putText(frame, "High Score!", (180, 230), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)
    cv2.putText(frame, f"League: {league}", (180, 280), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 200, 0), 2)
    cv2.putText(frame, "Press M to return to Menu", (100, 330), cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 200), 2)

def get_league(score):
    if score <= 20:
        return "Padawan"
    elif 20 < score <= 50:
        return "Master"
    elif 50 < score <= 100:
        return "Grandmaster"
    elif 100 < score <= 200:
        return "Legendary master"
    else:
        return "Legend"

def save_high_score(score):
    with open(CONFIG_FILE, 'r+') as f:
        data = json.load(f)
        data['high_score'] = score
        f.seek(0)
        json.dump(data, f)
        f.truncate()

def detect_blades(frame, landmarks, width, height, colors):
    global previous_vector
    blades = []

    for side, color in colors.items():
        if side == "right":
            wrist_raw = landmarks[16]
            elbow_raw = landmarks[14]
        else:
            wrist_raw = landmarks[15]
            elbow_raw = landmarks[13]

        wrist = (int(wrist_raw.x * width), int(wrist_raw.y * height))
        elbow = (int(elbow_raw.x * width), int(elbow_raw.y * height))

        dx, dy = wrist[0] - elbow[0], wrist[1] - elbow[1]
        distance = math.hypot(dx, dy)
        blade_length = int(distance * 2.5)  # Increased from 2 to 2.5

        if previous_vector[side] is not None:
            smoothed_dx, smoothed_dy = smooth_direction(previous_vector[side], (dx, dy))
        else:
            smoothed_dx, smoothed_dy = dx, dy

        previous_vector[side] = (dx, dy)
        length = math.hypot(smoothed_dx, smoothed_dy)
        if length == 0:
            continue

        smoothed_dx /= length
        smoothed_dy /= length

        x3 = int(wrist[0] + smoothed_dx * blade_length)
        y3 = int(wrist[1] + smoothed_dy * blade_length)

        cv2.line(frame, wrist, (x3, y3), color, 12)
        blades.append((wrist[0], wrist[1], x3, y3))

    return blades

def draw_shots(frame, shots):
    for shot in shots:
        color = (0, 255, 255) if shot['deflected'] else (0, 0, 255)
        cv2.line(frame, (shot['x'], shot['y']), (shot['x'], shot['y'] + 20), color, 10)

def check_block(shot, blades):
    sx, sy = shot['x'], shot['y'] + 10
    for blade in blades:
        x1, y1, x2, y2 = blade
        dist = point_to_line_distance((sx, sy), (x1, y1), (x2, y2))
        if dist < 40:  # Increased from 20 to 40
            return True
    return False

def point_to_line_distance(p, a, b):
    px, py = p
    ax, ay = a
    bx, by = b
    if ax == bx and ay == by:
        return np.hypot(px - ax, py - ay)
    length_squared = (bx - ax) ** 2 + (by - ay) ** 2
    if length_squared == 0:
        return np.hypot(px - ax, py - ay)
    t = max(0, min(1, ((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / length_squared))
    proj_x = ax + t * (bx - ax)
    proj_y = ay + t * (by - ay)
    return np.hypot(px - proj_x, py - proj_y)

# ========== MAIN GAME LOOP ==========

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(rgb)
    current_time = time.time()

    key = cv2.waitKey(1) & 0xFF

    if state == 'menu':
        draw_menu(frame)
        if key == ord('p'):
            state = 'play'
            score = 0
            new_high = False
            lives = 3
            shots.clear()
        elif key == ord('c'):
            state = 'customize'
            customizing_side = 'right'
            input_color = blade_colors[customizing_side][:]

    elif state == 'customize':
        draw_customization_menu(frame, customizing_side, input_color)

        if key == ord('r'):  # Red increase
            input_color[2] = min(255, input_color[2] + 5)
        elif key == ord('R'):  # Red decrease
            input_color[2] = max(0, input_color[2] - 5)
        elif key == ord('g'):  # Green increase
            input_color[1] = min(255, input_color[1] + 5)
        elif key == ord('G'):  # Green decrease
            input_color[1] = max(0, input_color[1] - 5)
        elif key == ord('b'):  # Blue increase
            input_color[0] = min(255, input_color[0] + 5)
        elif key == ord('B'):  # Blue decrease
            input_color[0] = max(0, input_color[0] - 5)
        elif key == 9:  # Tab
            customizing_side = 'left' if customizing_side == 'right' else 'right'
            input_color = blade_colors[customizing_side][:]
        elif key == 13:  # Enter
            blade_colors[customizing_side] = input_color[:]
            with open(CONFIG_FILE, 'r+') as f:
                data = json.load(f)
                data['blade_colors'][customizing_side] = input_color[:]
                f.seek(0)
                json.dump(data, f)
                f.truncate()
        elif key == ord('m'):
            state = 'menu'

    elif state == 'play':
        if key == ord('p'):  # Press 'p' to pause or unpause
            paused = not paused

        if paused:
            # Display "PAUSED" message when the game is paused
            cv2.putText(frame, "PAUSED", (w//2 - 100, h//2), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
        else:
            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                blades = detect_blades(frame, landmarks, w, h, blade_colors)

                if current_time - last_shot_time > shot_interval:
                    x_pos = random.randint(50, w - 50)
                    shots.append({'x': x_pos, 'y': 0, 'deflected': False, 'dir': random.choice([-1, 1])})
                    last_shot_time = current_time

                for shot in shots[:]:
                    if not shot['deflected']:
                        shot['y'] += 10
                        if check_block(shot, blades):
                            shot['deflected'] = True
                            score += 1
                            deflect_sound.play()

                    else:
                        shot['x'] += 10 * shot['dir']
                        shot['y'] -= 5

                    if shot['y'] > h or shot['x'] < 0 or shot['x'] > w or shot['y'] < -20:
                        if not shot['deflected']:
                            lives -= 1
                            if lives <= 0:
                                state = 'game_over'
                                if score > high_score:
                                    high_score = score
                                    new_high = True
                                    save_high_score(score)
                        shots.remove(shot)

            draw_shots(frame, shots)
            cv2.putText(frame, f'Score: {score}  Lives: {lives}', (20, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    elif state == 'game_over':
        draw_game_over(frame, score, high_score, new_high)
        if key == ord('m'):
            state = 'menu'

    cv2.imshow('Jedi Blade Game', frame)
    if key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
import cv2
import mediapipe as mp
import numpy as np
import random
import time
import json
import os
import math

# ========== CONFIG ==========
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "blade_colors": {
        "right": [0, 0, 255],
        "left": [0, 255, 0]
    },
    "high_score": 0
}

if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(DEFAULT_CONFIG, f)

with open(CONFIG_FILE, 'r') as f:
    config = json.load(f)

blade_colors = config['blade_colors']
high_score = config['high_score']

# ========== SETUP ==========
mp_pose = mp.solutions.pose
pose = mp_pose.Pose()
cap = cv2.VideoCapture(0)

state = 'menu'
score = 0
new_high = False
shots = []
shot_interval = 1.5
last_shot_time = time.time()
lives = 3

customizing_side = 'right'
input_color = blade_colors['right'][:]

previous_vector = {
    "left": None,
    "right": None
}

paused = False  # New variable to track if the game is paused

def smooth_direction(previous, current, alpha=0.7):
    if previous is None:
        return current
    angle_prev = math.atan2(previous[1], previous[0])
    angle_curr = math.atan2(current[1], current[0])
    smooth_angle = alpha * angle_curr + (1 - alpha) * angle_prev
    length = math.hypot(current[0], current[1])
    smooth_x = length * math.cos(smooth_angle)
    smooth_y = length * math.sin(smooth_angle)
    return smooth_x, smooth_y

def draw_menu(frame):
    cv2.putText(frame, "JEDI BLADE GAME", (100, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 0), 3)
    cv2.putText(frame, "Press P to Play", (120, 160), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)
    cv2.putText(frame, "Press C to Customize Blade Colors", (120, 210), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (100, 200, 255), 2)
    cv2.putText(frame, "Press Q to Quit", (120, 260), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 2)

def draw_customization_menu(frame, side, color):
    cv2.putText(frame, f"Customize {side.capitalize()} Blade Color", (50, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(frame, f"Current RGB: {color}", (80, 140),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (color[0], color[1], color[2]), 2)
    cv2.putText(frame, "Use keys R/G/B (up: +, down: -)", (80, 200),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
    cv2.putText(frame, "Press ENTER to save, TAB to switch blade, M for Menu", (40, 250),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 2)

def draw_game_over(frame, score, high_score, new_high):
    league = get_league(score)
    cv2.putText(frame, "GAME OVER", (150, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
    cv2.putText(frame, f"Score: {score}", (180, 180), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
    if new_high:
        cv2.putText(frame, "High Score!", (180, 230), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)
    cv2.putText(frame, f"League: {league}", (180, 280), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 200, 0), 2)
    cv2.putText(frame, "Press M to return to Menu", (100, 330), cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 200), 2)

def get_league(score):
    if score <= 20:
        return "Padawan"
    elif 20 < score <= 50:
        return "Master"
    else:
        return "Legend"

def save_high_score(score):
    with open(CONFIG_FILE, 'r+') as f:
        data = json.load(f)
        data['high_score'] = score
        f.seek(0)
        json.dump(data, f)
        f.truncate()

def detect_blades(frame, landmarks, width, height, colors):
    global previous_vector
    blades = []

    for side, color in colors.items():
        if side == "right":
            wrist_raw = landmarks[16]
            elbow_raw = landmarks[14]
        else:
            wrist_raw = landmarks[15]
            elbow_raw = landmarks[13]

        wrist = (int(wrist_raw.x * width), int(wrist_raw.y * height))
        elbow = (int(elbow_raw.x * width), int(elbow_raw.y * height))

        dx, dy = wrist[0] - elbow[0], wrist[1] - elbow[1]
        distance = math.hypot(dx, dy)
        blade_length = int(distance * 3)  # Increased from 2.5 to 3

        if previous_vector[side] is not None:
            smoothed_dx, smoothed_dy = smooth_direction(previous_vector[side], (dx, dy))
        else:
            smoothed_dx, smoothed_dy = dx, dy

        previous_vector[side] = (dx, dy)

        length = math.hypot(smoothed_dx, smoothed_dy)
        if length == 0:
            continue

        smoothed_dx /= length
        smoothed_dy /= length

        x3 = int(wrist[0] + smoothed_dx * blade_length)
        y3 = int(wrist[1] + smoothed_dy * blade_length)

        cv2.line(frame, wrist, (x3, y3), color, 12)
        blades.append((wrist[0], wrist[1], x3, y3))

    return blades

def draw_shots(frame, shots):
    for shot in shots:
        color = (0, 255, 255) if shot['deflected'] else (0, 0, 255)
        cv2.line(frame, (shot['x'], shot['y']), (shot['x'], shot['y'] + 20), color, 10)

def check_block(shot, blades):
    sx, sy = shot['x'], shot['y'] + 10
    for blade in blades:
        x1, y1, x2, y2 = blade
        dist = point_to_line_distance((sx, sy), (x1, y1), (x2, y2))
        if dist < 40:  # Increased from 20 to 40
            return True
    return False

def point_to_line_distance(p, a, b):
    px, py = p
    ax, ay = a
    bx, by = b
    if ax == bx and ay == by:
        return np.hypot(px - ax, py - ay)
    length_squared = (bx - ax) ** 2 + (by - ay) ** 2
    if length_squared == 0:
        return np.hypot(px - ax, py - ay)
    t = max(0, min(1, ((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / length_squared))
    proj_x = ax + t * (bx - ax)
    proj_y = ay + t * (by - ay)
    return np.hypot(px - proj_x, py - proj_y)

# ========== MAIN GAME LOOP ==========

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(rgb)
    current_time = time.time()

    key = cv2.waitKey(1) & 0xFF

    if state == 'menu':
        draw_menu(frame)
        if key == ord('p'):
            state = 'play'
            score = 0
            new_high = False
            lives = 3
            shots.clear()
        elif key == ord('c'):
            state = 'customize'
            customizing_side = 'right'
            input_color = blade_colors[customizing_side][:]

    elif state == 'customize':
        draw_customization_menu(frame, customizing_side, input_color)

        if key == ord('r'):
            input_color[0] = min(255, input_color[0] + 5)
        elif key == ord('g'):
            input_color[1] = min(255, input_color[1] + 5)
        elif key == ord('b'):
            input_color[2] = min(255, input_color[2] + 5)
        elif key == ord('R'):
            input_color[0] = max(0, input_color[0] - 5)
        elif key == ord('G'):
            input_color[1] = max(0, input_color[1] - 5)
        elif key == ord('B'):
            input_color[2] = max(0, input_color[2] - 5)
        elif key == 9:  # Tab
            customizing_side = 'left' if customizing_side == 'right' else 'right'
            input_color = blade_colors[customizing_side][:]
        elif key == 13:  # Enter
            blade_colors[customizing_side] = input_color[:]
            with open(CONFIG_FILE, 'r+') as f:
                data = json.load(f)
                data['blade_colors'][customizing_side] = input_color[:]
                f.seek(0)
                json.dump(data, f)
                f.truncate()
        elif key == ord('m'):
            state = 'menu'

    elif state == 'play':
        if key == ord('p'):  # Press 'p' to pause or unpause
            paused = not paused

        if paused:
            # Display "PAUSED" message when the game is paused
            cv2.putText(frame, "PAUSED", (w//2 - 100, h//2), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
        else:
            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                blades = detect_blades(frame, landmarks, w, h, blade_colors)

                if current_time - last_shot_time > shot_interval:
                    x_pos = random.randint(50, w - 50)
                    shots.append({'x': x_pos, 'y': 0, 'deflected': False, 'dir': random.choice([-1, 1])})
                    last_shot_time = current_time

                for shot in shots[:]:
                    if not shot['deflected']:
                        shot['y'] += 10
                        if check_block(shot, blades):
                            shot['deflected'] = True
                            score += 1
                    else:
                        shot['x'] += 10 * shot['dir']
                        shot['y'] -= 5

                    if shot['y'] > h or shot['x'] < 0 or shot['x'] > w or shot['y'] < -20:
                        if not shot['deflected']:
                            lives -= 1
                            if lives <= 0:
                                state = 'game_over'
                                if score > high_score:
                                    high_score = score
                                    new_high = True
                                    save_high_score(score)
                        shots.remove(shot)

            draw_shots(frame, shots)
            cv2.putText(frame, f'Score: {score}  Lives: {lives}', (20, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    elif state == 'game_over':
        draw_game_over(frame, score, high_score, new_high)
        if key == ord('m'):
            state = 'menu'

    cv2.imshow('Jedi Blade Game', frame)
    if key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()