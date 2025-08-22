import cv2
import mediapipe as mp
import numpy as np
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .kbs_engine import GlassesRecommender   # تأكد من وجوده


# ------------------------------
# Mediapipe FaceMesh (يفضل إنشاؤه مرّة واحدة)
# ------------------------------
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5
)


class FaceAnalysisView(APIView):
    def post(self, request, *args, **kwargs):
        file = request.FILES.get("image")
        if not file:
            return Response({"error": "No image uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        # قراءة الصورة
        npimg = np.frombuffer(file.read(), np.uint8)
        image_bgr = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        if image_bgr is None:
            return Response({"error": "Error reading image"}, status=status.HTTP_400_BAD_REQUEST)

        h, w, _ = image_bgr.shape
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

        # استخراج الملامح
        results = face_mesh.process(rgb)
        if not results.multi_face_landmarks:
            return Response({"error": "No face detected"}, status=status.HTTP_400_BAD_REQUEST)
        landmarks = results.multi_face_landmarks[0]

        # ------------------------------
        # Helpers (تحويل/دوران/مسافة)
        # ------------------------------
        def lm_to_px(lm):
            return np.array([lm.x * w, lm.y * h], dtype=np.float64)

        def rotate_point(point, center, angle_rad):
            R = np.array([[np.cos(angle_rad), -np.sin(angle_rad)],
                          [np.sin(angle_rad),  np.cos(angle_rad)]], dtype=np.float64)
            return (R @ (point - center)) + center

        def corrected_px(lm):
            p = lm_to_px(lm)
            return rotate_point(p, eye_center, -angle_rad)

        def euclidean(p1, p2):
            return float(np.linalg.norm(p1 - p2))

        # ------------------------------
        # تصحيح الميلان (من خط العينين)
        # ------------------------------
        left_eye_outer  = lm_to_px(landmarks.landmark[33])
        right_eye_outer = lm_to_px(landmarks.landmark[263])
        eye_center = (left_eye_outer + right_eye_outer) / 2.0

        dx = right_eye_outer[0] - left_eye_outer[0]
        dy = right_eye_outer[1] - left_eye_outer[1]
        angle_rad = np.arctan2(dy, dx)

        # ------------------------------
        # قطر الحدقة → scale (سم/بكسل)
        # ------------------------------
        pR1 = corrected_px(landmarks.landmark[469])
        pR2 = corrected_px(landmarks.landmark[471])
        pL1 = corrected_px(landmarks.landmark[474])
        pL2 = corrected_px(landmarks.landmark[476])

        pupil_d_right = euclidean(pR1, pR2)
        pupil_d_left  = euclidean(pL1, pL2)
        pupil_d_avg   = (pupil_d_right + pupil_d_left) / 2.0
        if pupil_d_avg < 1e-6:
            return Response({"error": "Iris not detected reliably"}, status=status.HTTP_400_BAD_REQUEST)

        scale = 1.3 / pupil_d_avg  # 1.3 cm مرجع قطر الحدقة

        # ------------------------------
        # قياسات الوجه (بعد التصحيح)
        # ------------------------------
        jaw_px         = euclidean(corrected_px(landmarks.landmark[135]), corrected_px(landmarks.landmark[364]))
        face_height_px = euclidean(corrected_px(landmarks.landmark[10]),  corrected_px(landmarks.landmark[152])) / 0.88
        forehead_px    = euclidean(corrected_px(landmarks.landmark[54]),  corrected_px(landmarks.landmark[284]))
        face_width_px  = euclidean(corrected_px(landmarks.landmark[123]), corrected_px(landmarks.landmark[352]))

        jaw_w         = jaw_px * scale
        face_height_cm= face_height_px * scale
        forehead_w    = forehead_px * scale
        face_width_cm = face_width_px * scale

        # =========================================================
        #              تحسين حساب لون البشرة (Skin Tone)
        # =========================================================
        # ❶ توازن أبيض بسيط (Gray-World) داخل كل ROI لمنع انحياز الإضاءة
        def gray_world_wb(bgr_roi):
            # نحافظ على السطوع العام ونوازن القنوات
            roi = bgr_roi.astype(np.float32)
            mean_b, mean_g, mean_r = roi[...,0].mean()+1e-6, roi[...,1].mean()+1e-6, roi[...,2].mean()+1e-6
            gray = (mean_b + mean_g + mean_r) / 3.0
            roi[...,0] *= (gray / mean_b)
            roi[...,1] *= (gray / mean_g)
            roi[...,2] *= (gray / mean_r)
            roi = np.clip(roi, 0, 255).astype(np.uint8)
            return roi

        # ❷ قناع الجلد في YCrCb (نطاقات شائعة للجلد البشري)
        def skin_mask_ycrcb(bgr_roi):
            ycrcb = cv2.cvtColor(bgr_roi, cv2.COLOR_BGR2YCrCb)
            Y, Cr, Cb = cv2.split(ycrcb)
            # حدود مرنة: Cb∈[77,127], Cr∈[133,173]
            mask = cv2.inRange(ycrcb, (0, 133, 77), (255, 173, 127))
            # تنظيف القناع
            kernel = np.ones((3,3), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
            return mask

        # ❸ أخذ عدّة رقع حول الخدين والجبهة (اعتمادًا على لاند ماركات ثابتة)
        def to_int_xy(idx):
            lm = landmarks.landmark[idx]
            return int(lm.x * w), int(lm.y * h)

        # نقاط آمنة: خد أيسر 234، خد أيمن 454، جبهة 10 (قد تحوي شعر؛ سنفلتره بالقناع)
        sample_indices = [234, 454, 10]
        L_vals, A_vals, B_vals = [], [], []

        # حجم الرقعة قابل للتعديل بحسب دقة الصورة
        patch = max(10, int(min(w, h) * 0.02))

        for idx in sample_indices:
            cx, cy = to_int_xy(idx)
            x0, x1 = max(0, cx - patch), min(w, cx + patch)
            y0, y1 = max(0, cy - patch), min(h, cy + patch)
            roi = image_bgr[y0:y1, x0:x1]
            if roi.size == 0:
                continue

            roi = gray_world_wb(roi)
            mask = skin_mask_ycrcb(roi)
            if mask.sum() < 50:   # عدد بكسلات الجلد قليل → تجاهل الرقعة
                continue

            lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)
            L, A, B = lab[...,0], lab[...,1], lab[...,2]

            # اجمع القيم داخل القناع فقط
            L_vals.extend(L[mask>0].flatten().tolist())
            A_vals.extend(A[mask>0].flatten().tolist())
            B_vals.extend(B[mask>0].flatten().tolist())

        # لو ما قدرنا نستخرج جلد كفاية، نرجع Unknown
        if len(L_vals) < 100:
            skin_tone = 'Unknown'
        else:
            # وسطي متين (Median) لمقاومة الضوضاء/الظلال
            L_med = float(np.median(L_vals))
            # تصنيف مبسّط على أساس L (OpenCV Lab: L ∈ [0..255])
            if L_med >= 170:
                skin_tone = 'Light'
            elif L_med >= 125:
                skin_tone = 'Medium'
            else:
                skin_tone = 'Dark'

        # =========================================================
        #                  Fuzzy face-shape scoring
        # =========================================================
        eps = 1e-6
        ar   = face_height_cm / max(face_width_cm, eps)
        jw_fw= jaw_w         / max(forehead_w, eps)
        cb_fw= face_width_cm / max(forehead_w, eps)
        cb_jw= face_width_cm / max(jaw_w, eps)

        def trapmf(x, a, b, c, d):
            if x <= a or x >= d: return 0.0
            if b <= x <= c: return 1.0
            if a < x < b: return (x - a) / max((b - a), eps)
            if c < x < d: return (d - x) / max((d - c), eps)
            return 0.0

        def gaussmf(x, mu, sigma):
            return float(np.exp(-0.5 * ((x - mu) / (sigma + eps)) ** 2))

        ar_short  = trapmf(ar, 0.80, 0.90, 1.05, 1.15)
        ar_medium = trapmf(ar, 1.05, 1.20, 1.35, 1.50)
        ar_tall   = trapmf(ar, 1.35, 1.55, 1.80, 2.10)

        jw_eq_fw  = gaussmf(jw_fw, 1.0, 0.08)
        jw_gt_fw  = trapmf(jw_fw, 1.05, 1.12, 1.40, 1.80)
        jw_lt_fw  = trapmf(jw_fw, 0.55, 0.70, 0.92, 0.98)

        cb_prom_over_fw = trapmf(cb_fw, 1.05, 1.12, 1.40, 1.80)
        cb_prom_over_jw = trapmf(cb_jw, 1.05, 1.12, 1.40, 1.80)

        score_square   = 0.45*ar_short + 0.35*jw_eq_fw + 0.20*(1.0 - cb_prom_over_fw)
        score_round    = 0.50*gaussmf(ar, 1.0, 0.06) + 0.25*jw_eq_fw + 0.25*cb_prom_over_fw
        score_oval     = 0.55*ar_medium + 0.25*jw_eq_fw + 0.20*cb_prom_over_fw
        score_oblong   = 0.70*ar_tall   + 0.15*jw_eq_fw + 0.15*(1.0 - cb_prom_over_fw)
        score_heart    = 0.45*ar_medium + 0.40*jw_lt_fw + 0.15*cb_prom_over_fw
        score_triangle = 0.45*ar_medium + 0.40*jw_gt_fw + 0.15*(1.0 - cb_prom_over_fw)
        score_diamond  = 0.40*ar_medium + 0.30*cb_prom_over_fw + 0.20*cb_prom_over_jw + 0.10*jw_eq_fw

        scores = {
            'Square':   float(score_square),
            'Round':    float(score_round),
            'Oval':     float(score_oval),
            'Oblong':   float(score_oblong),
            'Heart':    float(score_heart),
            'Triangle': float(score_triangle),
            'Diamond':  float(score_diamond),
        }
        ssum = sum(scores.values()) + eps
        scores = {k: v/ssum for k, v in scores.items()}
        face_shape = max(scores, key=scores.get)

        # ------------------------------
        # KBS توصيات النظارات
        # ------------------------------
        kbs = GlassesRecommender()
        recommendations = kbs.run_engine(face_shape, face_width_cm, skin_tone)

        # ------------------------------
        # Response
        # ------------------------------
        payload = {
            'face_width_cm': round(face_width_cm, 2),
            'face_shape': face_shape,
            'skin_tone': skin_tone,
            **recommendations
        }
        return Response(payload, status=status.HTTP_200_OK)
