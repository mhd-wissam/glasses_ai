from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import cv2
import numpy as np
import mediapipe as mp
from math import sqrt

from glasses.models import Glasses
from .kbs_engine import GlassesRecommender 

class FaceAnalysisView(APIView):
    def post(self, request):
        if 'image' not in request.FILES:
            return Response({'error': 'No image was sent.'}, status=400)

        # Read image
        image_file = request.FILES['image']
        image_bytes = image_file.read()
        image_np = np.frombuffer(image_bytes, np.uint8)
        image_bgr = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
        if image_bgr is None:
            return Response({'error': 'Error reading the image.'}, status=400)

        h, w, _ = image_bgr.shape
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

        mp_face_mesh = mp.solutions.face_mesh
        with mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=True) as face_mesh:
            results = face_mesh.process(image_rgb)
            if not results.multi_face_landmarks:
                return Response({'error': 'No face detected.'}, status=400)

            landmarks = results.multi_face_landmarks[0].landmark
            def to_px(landmark): return int(landmark.x * w), int(landmark.y * h)
            def euclidean(p1, p2): return sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

            scale_mm_per_px = 13 / (euclidean(to_px(landmarks[473]), to_px(landmarks[476])) * 2)
            face_width_px = euclidean(to_px(landmarks[135]), to_px(landmarks[352]))
            face_height_px = euclidean(to_px(landmarks[10]), to_px(landmarks[152])) / 0.88
            forehead_width_px = euclidean(to_px(landmarks[54]), to_px(landmarks[284]))
            jaw_width_px = euclidean(to_px(landmarks[123]), to_px(landmarks[352]))

            face_width_cm = face_width_px * scale_mm_per_px / 10
            face_height_cm = face_height_px * scale_mm_per_px / 10
            forehead_width_cm = forehead_width_px * scale_mm_per_px / 10
            jaw_width_cm = jaw_width_px * scale_mm_per_px / 10

            skin_point = to_px(landmarks[234]) 
            patch_size = 10
            x, y = skin_point
            x_start = max(0, x - patch_size)
            y_start = max(0, y - patch_size)
            x_end = min(w, x + patch_size)
            y_end = min(h, y + patch_size)
            patch = image_bgr[y_start:y_end, x_start:x_end]

            if patch.shape[0] > 0 and patch.shape[1] > 0:
                avg_color_bgr = patch.mean(axis=(0, 1))
                avg_color_hsv = cv2.cvtColor(np.uint8([[avg_color_bgr]]), cv2.COLOR_BGR2HSV)[0][0]
                _, _, v = avg_color_hsv

                if v < 70:
                    skin_tone = 'Dark'
                elif 70 <= v < 160:
                    skin_tone = 'Medium'
                else:
                    skin_tone = 'Light'
            else:
                skin_tone = 'Unknown'

            aspect_ratio = face_height_cm / face_width_cm
            face_shape = "Undefined"

            if abs(face_height_cm - face_width_cm) <= 1 and abs(face_height_cm - jaw_width_cm) <= 1 and abs(face_height_cm - forehead_width_cm) <= 1:
                face_shape = 'Square'
            elif face_height_cm > forehead_width_cm and abs(forehead_width_cm - jaw_width_cm) <= 1 and abs(jaw_width_cm - face_width_cm) <= 1:
                face_shape = 'Oblong'
            elif abs(face_height_cm - face_width_cm) <= 1 and abs(forehead_width_cm - jaw_width_cm) <= 1 and forehead_width_cm < face_height_cm:
                face_shape = 'Round'
            elif face_height_cm > face_width_cm > forehead_width_cm > jaw_width_cm:
                face_shape = 'Oval'
            elif forehead_width_cm < face_width_cm and face_width_cm < jaw_width_cm:
                face_shape = 'Triangle'
            elif forehead_width_cm > face_width_cm and face_width_cm > jaw_width_cm:
                face_shape = 'Heart'
            elif face_width_cm > forehead_width_cm and abs(forehead_width_cm - jaw_width_cm) <= 1:
                face_shape = 'Diamond'
            else:
                face_shape = 'Undefined'

        kbs = GlassesRecommender()
        recommendations = kbs.run_engine(face_shape, face_width_cm, skin_tone)

        return Response({
            'face_width_cm': round(face_width_cm, 2),
            # 'face_height_cm': round(face_height_cm, 2),
            # 'forehead_width_cm': round(forehead_width_cm, 2),
            # 'jaw_width_cm': round(jaw_width_cm, 2),
            'face_shape': face_shape,
            'skin_tone': skin_tone,
            **recommendations
        })
