from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from .serializers import GlassesSerializer, GlassesDetailSerializer, GlassesUpdateSerializer, GlassesRecommendationSerializer, GlassesCreateSerializer
from rest_framework.generics import ListAPIView, RetrieveAPIView
from django.db.models import Q, Count
from typing import List, Tuple, Optional
from django.db import transaction
from glasses.models import Glasses, Purpose, GlassesPurpose, GlassesImage
import json
from rest_framework.exceptions import PermissionDenied
from face.kbs_engine import GlassesRecommender
from rest_framework import generics, permissions, status


WEIGHT_RANGES = {
    "Light": (None, 20.0),
    "Medium": (20.0, 35.0),
}


class Upload3DModelView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [permissions.IsAuthenticated]  # 🔒 لازم توكن

    def post(self, request):
        frame_id = request.data.get('frame_id')
        model_file = request.FILES.get('model_3d')
        if not frame_id or not model_file:
            return Response({'error': 'frame_id and model_3d are required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            glasses = Glasses.objects.get(frame_id=frame_id)
            glasses.model_3d = model_file
            glasses.save()
            return Response({'success': 'Model uploaded successfully', 'frame_id': frame_id})
        except Glasses.DoesNotExist:
            return Response({'error': 'Glasses not found with this frame_id'}, status=status.HTTP_404_NOT_FOUND)


class AddGlassesView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # 🔒 لازم توكن

    def post(self, request):
        data = request.data.copy()
        purposes = data.getlist('purposes')
        if purposes:
            data.setlist('purposes', purposes)
        serializer = GlassesSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({'success': 'Glasses saved successfully', 'data': serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UploadGlassesImagesView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [permissions.IsAuthenticated]  # 🔒 لازم توكن

    def post(self, request):
        glasses_id = request.data.get('id')
        images = request.FILES.getlist('images')
        if not glasses_id or not images:
            return Response({'error': 'id and images are required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            glasses = Glasses.objects.get(id=glasses_id)
            for image in images:
                GlassesImage.objects.create(glasses=glasses, image=image)
            return Response({'success': 'Images uploaded successfully', 'glasses_id': glasses_id, 'uploaded': len(images)})
        except Glasses.DoesNotExist:
            return Response({'error': 'Glasses not found with this id'}, status=status.HTTP_404_NOT_FOUND)
        

class AddGlassesWithImagesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = GlassesCreateSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            glasses = serializer.save()
            return Response({
                "success": "Glasses with images added successfully",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GlassesDetailView(RetrieveAPIView):
    queryset = Glasses.objects.all()
    serializer_class = GlassesDetailSerializer
    permission_classes = [permissions.IsAuthenticated]  # 🔒 لازم توكن
    lookup_field = "id"
    lookup_url_kwarg = "glasses_id"

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        similar_glasses = Glasses.objects.filter(
            shape=instance.shape,
            gender=instance.gender,
            size=instance.size
        ).exclude(id=instance.id)[:5]

        similar_serializer = GlassesSerializer(similar_glasses, many=True, context={"request": request})

        return Response({
            "glasses": serializer.data,
            "similar_glasses": similar_serializer.data
        })


class ListGlassesView(ListAPIView):
    queryset = Glasses.objects.all()
    serializer_class = GlassesSerializer
    permission_classes = [permissions.IsAuthenticated]  # 🔒 لازم توكن


class RetrieveGlassesView(RetrieveAPIView):
    queryset = Glasses.objects.all()
    serializer_class = GlassesSerializer
    lookup_field = 'id'
    permission_classes = [permissions.IsAuthenticated]  # 🔒 لازم توكن


class GlassesByMaterialFormDataView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # 🔒 لازم توكن

    def post(self, request, *args, **kwargs):
        materials = request.data.getlist('materials[]')
        if not materials:
            return Response({"error": "No materials provided"}, status=status.HTTP_400_BAD_REQUEST)
        queryset = Glasses.objects.filter(material__in=materials)
        serializer = GlassesSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class GlassesSmartFilterView(APIView):
    parser_classes = (JSONParser, FormParser, MultiPartParser)
    permission_classes = [permissions.IsAuthenticated]  # 🔒 لازم توكن

    def _qgetlist(self, obj, key: str) -> List[str]:
        if hasattr(obj, "getlist"):
            return obj.getlist(key)
        v = obj.get(key) if isinstance(obj, dict) else None
        if isinstance(v, list): return v
        if isinstance(v, str):  return [v]
        return []

    def _extract_list(self, request, key: str) -> List[str]:
        vals: List[str] = []
        v = request.data.get(key, None)
        if isinstance(v, list):
            vals += v
        elif isinstance(v, str):
            s = v.strip()
            if s:
                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, list): vals += parsed
                    elif isinstance(parsed, str): vals.append(parsed)
                except Exception:
                    vals += [p.strip() for p in s.split(",") if p.strip()]
        vals += self._qgetlist(request.data, key)
        vals += self._qgetlist(request.data, f"{key}[]")
        vals += self._qgetlist(request.query_params, key)
        joined = request.query_params.get(f"{key}s")
        if isinstance(joined, str):
            vals += [p.strip() for p in joined.split(",") if p.strip()]
        out, seen = [], set()
        for x in vals:
            s = str(x).strip()
            if s and s not in seen:
                seen.add(s)
                out.append(s)
        return out

    def _extract_str(self, request, key: str) -> str:
        v = request.data.get(key, "")
        return v.strip() if isinstance(v, str) else ""

    def _gender_values(self, g: str):
        if not g: return None
        g = g.strip()
        if g == "Male":   return ["Male", "Unisex"]
        if g == "Female": return ["Female", "Unisex"]
        if g == "Unisex": return ["Unisex"]
        if g == "Kids":   return ["Kids"]
        return None

    def _weight_range(self, pref: str) -> Optional[Tuple[Optional[float], Optional[float]]]:
        pref = pref.strip() if pref else ""
        if not pref or pref == "Doesn't matter":
            return None
        return WEIGHT_RANGES.get(pref)

    def post(self, request, *args, **kwargs):
        gender        = self._extract_str(request, "gender")
        shapes        = self._extract_list(request, "shapes")
        size          = self._extract_str(request, "size")
        tone          = self._extract_str(request, "tone")
        colors        = self._extract_list(request, "colors")
        weight_pref   = self._extract_str(request, "weight_preference")
        materials     = self._extract_list(request, "materials")
        purpose_names = self._extract_list(request, "purposes")
        purpose_ids   = [int(x) for x in self._extract_list(request, "purpose_ids") if str(x).isdigit()]

        qs = Glasses.objects.all()
        g_vals = self._gender_values(gender)
        if g_vals:
            qs = qs.filter(gender__in=g_vals)
        if shapes:
            qs = qs.filter(shape__in=shapes)
        if size:
            qs = qs.filter(size__iexact=size)
        if tone:
            qs = qs.filter(tone__iexact=tone)
        if colors:
            qs = qs.filter(color__in=colors)
        w_range = self._weight_range(weight_pref)
        if w_range:
            lo, hi = w_range
            if lo is not None: qs = qs.filter(weight__gt=lo)
            if hi is not None: qs = qs.filter(weight__lte=hi)
        if weight_pref not in ("", "Doesn't matter") and materials:
            qs = qs.filter(material__in=materials)
        if purpose_names and not purpose_ids:
            purpose_ids = list(Purpose.objects.filter(name__in=purpose_names).values_list("id", flat=True))
        if purpose_ids:
            qs = (qs.filter(purposes__in=purpose_ids)
                    .annotate(purpose_match_count=Count("purposes", filter=Q(purposes__in=purpose_ids), distinct=True))
                    .filter(purpose_match_count=len(set(purpose_ids))))

        data = GlassesSerializer(qs, many=True, context={"request": request}).data
        return Response({"count": len(data), "results": data}, status=status.HTTP_200_OK)

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

class GlassesByStoreView(ListAPIView):
    permission_classes = [permissions.IsAuthenticated]   # غيّرها لـ AllowAny لو بدكها عامة
    serializer_class = GlassesSerializer

    def get_queryset(self):
        store_id = self.kwargs.get("store_id")
        return (
            Glasses.objects
            .filter(store_id=store_id)
            .select_related("store")
            .prefetch_related("images", "purposes")
            .order_by("-id")
        )
    
class MyStoreGlassesView(ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = GlassesSerializer

    def get_queryset(self):
        user = self.request.user
        # تأكد أن لديه متجر
        if not hasattr(user, "store"):
            raise PermissionDenied("Only store owners can list their store glasses.")
        return (
            Glasses.objects
            .filter(store=user.store)
            .select_related("store")
            .prefetch_related("images", "purposes")
            .order_by("-id")
        )

class RecommendGlassesByFaceShapeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        face_shape = request.data.get("face_shape")
        if not face_shape:
            return Response({"error": "face_shape is required"}, status=status.HTTP_400_BAD_REQUEST)

        # 🧠 شغل الـ Expert System فقط بالـ face_shape
        engine = GlassesRecommender()
        rec = engine.run_engine(face_shape=face_shape)


        recommended_shapes = rec.get("recommended_shape", [])
        if not recommended_shapes:
            return Response({
                "message": f"No recommendations available for face shape '{face_shape}'.",
                "results": []
            }, status=status.HTTP_200_OK)

        # 🕶️ استعلام النظارات المناسبة
        qs = Glasses.objects.filter(shape__in=recommended_shapes)
        serializer = GlassesSerializer(qs, many=True, context={"request": request})

        return Response({
            "face_shape": face_shape,
            "recommended_shapes": recommended_shapes,
            "count": qs.count(),
            "results": serializer.data
        }, status=status.HTTP_200_OK)

# glasses/views.py

class UpdateGlassesView(generics.UpdateAPIView):
    queryset = Glasses.objects.all()
    serializer_class = GlassesUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"
    lookup_url_kwarg = "glasses_id"

    def update(self, request, *args, **kwargs):
        glasses = self.get_object()
        user = request.user

        # ✅ تحقق من الصلاحيات
        if user.role == "admin":
            pass
        elif user.role == "store_owner" and hasattr(user, "store") and glasses.store == user.store:
            pass
        else:
            raise PermissionDenied("⚠️ You are not allowed to update this glasses.")

        serializer = self.get_serializer(glasses, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response({
            "message": "✅ Glasses updated successfully",
            "glasses": GlassesSerializer(glasses, context={"request": request}).data
        }, status=status.HTTP_200_OK)

class DeleteGlassesView(generics.DestroyAPIView):
    queryset = Glasses.objects.all()
    serializer_class = GlassesSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"
    lookup_url_kwarg = "glasses_id"

    def destroy(self, request, *args, **kwargs):
        glasses = self.get_object()
        user = request.user

        if user.role == "admin":
            pass
        elif user.role == "store_owner" and hasattr(user, "store") and glasses.store == user.store:
            pass
        else:
            raise PermissionDenied("⚠️ You are not allowed to delete this glasses.")

        self.perform_destroy(glasses)
        return Response({"message": "✅ Glasses deleted successfully"}, status=status.HTTP_200_OK)
    
# glasses/views.py
from .serializers import GlassesSerializer
from .kbs import SmartRecommenderKBS, GlassesFact, AnalysisResult, UserPreference, RecommendationScore, compute_max_possible_score

class IsCustomer(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "customer"
    
class SmartRecommendEndpoint(APIView):
    permission_classes = [IsCustomer]

    def post(self, request):
        try:
            user_input = request.data
            analysis = {
                "recommended_shapes": user_input.get("shapes", []),
                "recommended_size": user_input.get("size","N/A"),
                "recommended_tone": user_input.get("tone","N/A"),
            }
            user_prefs = []
            if user_input.get("gender"):
                user_prefs.append({"category":"gender","value":user_input["gender"]})
            if user_input.get("purposes"):
                user_prefs.append({"category":"purpose","value":user_input["purposes"]})
            if user_input.get("weight_preference"):
                user_prefs.append({"category":"weight_pref","value":"lightweight"})
            for m in user_input.get("materials",[]):
                user_prefs.append({"category":"material_pref","value":m})

            max_score = compute_max_possible_score(user_prefs)

            # ORM query
            glasses_qs = Glasses.objects.select_related("store").prefetch_related("purposes","images")

            # Run engine
            engine = SmartRecommenderKBS()
            engine.reset()
            engine.declare(AnalysisResult(**analysis))
            for pref in user_prefs: engine.declare(UserPreference(**pref))
            for g in glasses_qs:
                tags = list(g.purposes.values_list("name", flat=True))
                weight_val = int(round(float(g.weight))) if g.weight else 999
                engine.declare(GlassesFact(
                    frame_id=g.id, shape=g.shape, material=g.material,
                    size=g.size, gender=g.gender, tone=g.tone,
                    color=g.color, weight=weight_val, style_tags=tags
                ))
            engine.run()

            # Collect
            enriched = []
            for fact in engine.facts.values():
                if isinstance(fact, RecommendationScore) and fact['score'] > 0:
                    g = glasses_qs.get(id=fact['frame_id'])
                    g.score = fact['score']
                    g.match_percentage = round((fact['score']/max_score)*100,1) if max_score else 0
                    g.reasons = list(fact['reasons'])
                    enriched.append(g)

            enriched.sort(key=lambda x: x.score, reverse=True)
            serializer = GlassesRecommendationSerializer(enriched[:100], many=True, context={"request": request})
            return Response({
                "max_possible_score": max_score,
                "count": len(enriched),
                "results": serializer.data
            })
        except Exception as e:
            return Response({"detail":f"Internal error: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
