import cv2
import mediapipe as mp
import numpy as np

# ------------------------------
# إعداد MediaPipe FaceMesh
# ------------------------------
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=True,
                                  max_num_faces=1,
                                  refine_landmarks=True,
                                  min_detection_confidence=0.5)

# ------------------------------
# تحميل الصورة
# ------------------------------
image_path = "photo1.jpg"  # غيّرها لمسارك
image = cv2.imread(image_path)
h, w, _ = image.shape
rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
results = face_mesh.process(rgb)

if not results.multi_face_landmarks:
    print("No face detected")
    exit()

landmarks = results.multi_face_landmarks[0]

# ------------------------------
# دالة تحويل النقطة إلى إحداثيات بيكسل
# ------------------------------
def lm_to_px(lm):
    return np.array([lm.x * w, lm.y * h])

# ------------------------------
# دالة تدوير نقطة حول مركز معين
# ------------------------------
def rotate_point(point, center, angle_rad):
    R = np.array([[np.cos(angle_rad), -np.sin(angle_rad)],
                  [np.sin(angle_rad),  np.cos(angle_rad)]])
    return np.dot(R, point - center) + center

# ------------------------------
# حساب زاوية الميلان من خط العينين
# ------------------------------
left_eye_outer = lm_to_px(landmarks.landmark[33])   # زاوية العين اليسرى
right_eye_outer = lm_to_px(landmarks.landmark[263]) # زاوية العين اليمنى
eye_center = (left_eye_outer + right_eye_outer) / 2.0

dx = right_eye_outer[0] - left_eye_outer[0]
dy = right_eye_outer[1] - left_eye_outer[1]
angle_rad = np.arctan2(dy, dx)  # زاوية الميلان بالراديان

# ------------------------------
# إعادة تموضع النقاط بعد التصحيح
# ------------------------------
def corrected_px(lm):
    p = lm_to_px(lm)
    return rotate_point(p, eye_center, -angle_rad)

def euclidean(p1, p2):
    return np.linalg.norm(p1 - p2)

# ------------------------------
# حساب قطر الحدقة (للمعايرة)
# ------------------------------
pR1 = corrected_px(landmarks.landmark[469])
pR2 = corrected_px(landmarks.landmark[471])
pL1 = corrected_px(landmarks.landmark[474])
pL2 = corrected_px(landmarks.landmark[476])

pupil_d_right = euclidean(pR1, pR2)
pupil_d_left  = euclidean(pL1, pL2)
pupil_d_avg   = (pupil_d_right + pupil_d_left) / 2.0

scale = 1.3 / pupil_d_avg  # 1.3 cm = 13mm

print(f"Average pupil diameter (reference ~1.3 cm): {pupil_d_avg*scale:.2f} cm")

# ------------------------------
# الحسابات المطلوبة
# ------------------------------
jaw_px        = euclidean(corrected_px(landmarks.landmark[135]), corrected_px(landmarks.landmark[364]))
face_height_px= euclidean(corrected_px(landmarks.landmark[10]),  corrected_px(landmarks.landmark[152])) / 0.88
forehead_px   = euclidean(corrected_px(landmarks.landmark[54]),  corrected_px(landmarks.landmark[284]))
face_width_px = euclidean(corrected_px(landmarks.landmark[123]), corrected_px(landmarks.landmark[352]))

print(f"Jaw width:       {jaw_px*scale:.2f} cm")
print(f"Face height:     {face_height_px*scale:.2f} cm")
print(f"Forehead width:  {forehead_px*scale:.2f} cm")
print(f"Face width:      {face_width_px*scale:.2f} cm")

