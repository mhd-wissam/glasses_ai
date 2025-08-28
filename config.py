# -*- coding: utf-8 -*-
"""
نظام التوصية الذكي بالنظارات (نسخة موحّدة، دعم Gender TextChoices + JSON).

- يدعم دخل JSON بالشكل:
  {
    "gender": "Female",
    "shapes": ["Square"],
    "size": "Medium",
    "tone": "Dark",
    "colors": ["Red"],
    "weight_preference": "Light",
    "materials": ["Plastic"],
    "purposes": ["Office"]
  }

- يحسب max_possible_score بشكل صحيح (كل فئة مرة واحدة فقط)
- يطابق Gender مع: Male / Female / Unisex / Kids
"""

# ======================================================================
# القسم 0: الإعدادات والمكتبات
# ======================================================================
import collections
import collections.abc
import sys
import json
import os
import pandas as pd

if sys.version_info.major == 3 and sys.version_info.minor >= 10:
    collections.Mapping = collections.abc.Mapping
    collections.MutableMapping = collections.abc.MutableMapping

from experta import KnowledgeEngine, Rule, Fact, Field, MATCH, AS, TEST, NOT

# ======================================================================
# القسم 1: تصميم الحقائق (Facts)
# ======================================================================

class AnalysisResult(Fact):
    recommended_shapes = Field(list)
    recommended_size = Field(str)
    recommended_tone = Field(str)

class UserPreference(Fact):
    category = Field(str, mandatory=True)
    value = Field(object, mandatory=True)

class Glasses(Fact):
    frame_id = Field(int, mandatory=True)
    shape = Field(str)
    material = Field(str)
    size = Field(str)
    gender = Field(str)   # Male / Female / Unisex / Kids
    tone = Field(str)
    color = Field(str)
    weight = Field(int)
    style_tags = Field(list, default=[])

class RecommendationScore(Fact):
    frame_id = Field(int, mandatory=True)
    score = Field(int, default=0)
    reasons = Field(list, default=[])

# ======================================================================
# القسم 2: محرك القواعد
# ======================================================================

class SmartRecommenderKBS(KnowledgeEngine):
    def _update_score(self, score_fact, points, reason_key):
        reason_text = f"{reason_key} (+{points})"
        reasons = list(score_fact['reasons'])
        reasons.append(reason_text)
        self.modify(score_fact, score=score_fact['score'] + points, reasons=reasons)

    @Rule(
        Glasses(frame_id=MATCH.fid),
        NOT(RecommendationScore(frame_id=MATCH.fid)),
        salience=1000
    )
    def initialize_score(self, fid):
        self.declare(RecommendationScore(frame_id=fid, score=0, reasons=[]))

    # Face analysis matches
    @Rule(
        AnalysisResult(recommended_shapes=MATCH.rec_shapes),
        Glasses(frame_id=MATCH.fid, shape=MATCH.g_shape),
        AS.score_fact << RecommendationScore(frame_id=MATCH.fid, reasons=MATCH.reasons),
        TEST(lambda g_shape, rec_shapes: g_shape in rec_shapes),
        TEST(lambda reasons: not any("Matches Face Shape Analysis" in r for r in reasons)),
        salience=100
    )
    def match_recommended_shape(self, score_fact):
        self._update_score(score_fact, 25, "Matches Face Shape Analysis")

    @Rule(
        AnalysisResult(recommended_size=MATCH.rec_size),
        Glasses(frame_id=MATCH.fid, size=MATCH.g_size),
        AS.score_fact << RecommendationScore(frame_id=MATCH.fid, reasons=MATCH.reasons),
        TEST(lambda g_size, rec_size: g_size == rec_size),
        TEST(lambda reasons: not any("Matches Face Size Analysis" in r for r in reasons)),
        salience=95
    )
    def match_recommended_size(self, score_fact):
        self._update_score(score_fact, 20, "Matches Face Size Analysis")

    @Rule(
        AnalysisResult(recommended_tone=MATCH.rec_tone),
        Glasses(frame_id=MATCH.fid, tone=MATCH.g_tone),
        AS.score_fact << RecommendationScore(frame_id=MATCH.fid, reasons=MATCH.reasons),
        TEST(lambda g_tone, rec_tone: g_tone == rec_tone),
        TEST(lambda reasons: not any("Matches Skin Tone Analysis" in r for r in reasons)),
        salience=90
    )
    def match_recommended_tone(self, score_fact):
        self._update_score(score_fact, 15, "Matches Skin Tone Analysis")

    # User prefs matches
    @Rule(
        UserPreference(category='purpose', value=MATCH.user_purposes),
        Glasses(frame_id=MATCH.fid, style_tags=MATCH.g_tags),
        AS.score_fact << RecommendationScore(frame_id=MATCH.fid, reasons=MATCH.reasons),
        TEST(lambda user_purposes, g_tags: any(p in g_tags for p in user_purposes)),
        TEST(lambda reasons: not any("Matches User's Purpose" in r for r in reasons)),
        salience=80
    )
    def match_user_purpose(self, score_fact):
        self._update_score(score_fact, 15, "Matches User's Purpose")

    @Rule(
        UserPreference(category='gender', value=MATCH.user_gender),
        Glasses(frame_id=MATCH.fid, gender=MATCH.g_gender),
        AS.score_fact << RecommendationScore(frame_id=MATCH.fid, reasons=MATCH.reasons),
        TEST(lambda user_gender, g_gender: user_gender.strip().lower() == g_gender.strip().lower()),
        TEST(lambda reasons: not any("Matches User's Gender" in r for r in reasons)),
        salience=75
    )
    def match_user_gender(self, score_fact):
        self._update_score(score_fact, 10, "Matches User's Gender")

    @Rule(
        UserPreference(category='material_pref', value=MATCH.user_material),
        Glasses(frame_id=MATCH.fid, material=MATCH.g_material),
        AS.score_fact << RecommendationScore(frame_id=MATCH.fid, reasons=MATCH.reasons),
        TEST(lambda user_material, g_material: user_material.strip().lower() in g_material.strip().lower()),
        TEST(lambda reasons: not any("Matches User's Material Preference" in r for r in reasons)),
        salience=70
    )
    def match_user_material(self, score_fact):
        self._update_score(score_fact, 10, "Matches User's Material Preference")

    @Rule(
        UserPreference(category='weight_pref', value='lightweight'),
        Glasses(frame_id=MATCH.fid, weight=MATCH.g_weight),
        AS.score_fact << RecommendationScore(frame_id=MATCH.fid, reasons=MATCH.reasons),
        TEST(lambda g_weight: g_weight <= 18),
        TEST(lambda reasons: not any("Matches User's Lightweight Preference" in r for r in reasons)),
        salience=60
    )
    def match_lightweight_pref(self, score_fact):
        self._update_score(score_fact, 10, "Matches User's Lightweight Preference")

# ======================================================================
# القسم 3: أدوات الإدخال/الإخراج + التطبيع
# ======================================================================

GENDER_ALLOWED = {"male": "Male", "female": "Female", "unisex": "Unisex", "kids": "Kids"}

def normalize_gender(value: str) -> str:
    if not value:
        return "Unisex"  # اختيار منطقي افتراضي
    v = str(value).strip().lower()
    return GENDER_ALLOWED.get(v, value)  # إن لم نجدها نعيدها كما هي

def normalize_weight_pref(value: str):
    if not value:
        return None
    v = str(value).strip().lower()
    # نعالج "Light", "Lightweight", "خفيف"
    return "lightweight" if v in ("light", "lightweight", "خفيف") else None

def normalize_purposes(purposes_list):
    """
    نحول النصوص العامة إلى style_tags التي يولّدها اللودر:
    Sports / Office / Fashion / Daily / Classic / General
    """
    mapping = {
        'sports or activity': ['Sports'],
        'sports': ['Sports'],
        'office': ['Office'],
        'fashion': ['Fashion'],
        'daily': ['Daily'],
        'classic': ['Classic'],
        'general': ['General'],
    }
    out = []
    for p in purposes_list or []:
        p_low = str(p).strip().lower()
        if p_low in mapping:
            out.extend(mapping[p_low])
        else:
            if 'sport' in p_low: out.append('Sports')
            elif 'office' in p_low: out.append('Office')
            elif 'fashion' in p_low: out.append('Fashion')
            elif 'daily' in p_low: out.append('Daily')
            elif 'classic' in p_low: out.append('Classic')
    return list(dict.fromkeys(out)) or ['General']

def load_user_input_from_json(path="user_input.json"):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    # افتراضي إن لم يوجد الملف
    return {
        "gender": "Female",
        "shapes": ["Square"],
        "size": "Medium",
        "tone": "Dark",
        "colors": ["Red"],
        "weight_preference": "Light",
        "materials": ["Plastic"],
        "purposes": ["Office"]
    }

def parse_inputs(user_input: dict):
    # تحليل الوجه يُؤخذ من الحقول الأساسية
    analysis_results = {
        "recommended_shapes": user_input.get("shapes", []) or [],
        "recommended_size": user_input.get("size", "N/A"),
        "recommended_tone": user_input.get("tone", "N/A"),
    }

    user_preferences = []

    # gender (يتم التطبيع لواحد من Male/Female/Unisex/Kids)
    g = normalize_gender(user_input.get("gender"))
    if g:
        user_preferences.append({"category": "gender", "value": g})

    # purposes -> style_tags
    purp = normalize_purposes(user_input.get("purposes", []))
    if purp:
        user_preferences.append({"category": "purpose", "value": purp})

    # weight preference
    w = normalize_weight_pref(user_input.get("weight_preference"))
    if w:
        user_preferences.append({"category": "weight_pref", "value": w})

    # materials (قد تكون متعددة — المحرك سيحسبها مرة واحدة بسبب فحص السبب)
    for mat in user_input.get("materials", []) or []:
        if mat:
            user_preferences.append({"category": "material_pref", "value": str(mat)})

    # تفضيلات إضافية مستقبلية
    if user_input.get("shapes"):
        user_preferences.append({"category": "shape", "value": user_input["shapes"]})
    if user_input.get("colors"):
        user_preferences.append({"category": "color", "value": user_input["colors"]})

    return analysis_results, user_preferences

def load_glasses_from_excel(file_path="glasses_export.xlsx"):
    """قراءة وتنظيف بيانات النظارات من إكسل وإرجاع list[dict] متوافقة مع القواعد."""
    try:
        df = pd.read_excel(file_path)
    except FileNotFoundError:
        print(f"!!! خطأ: الملف '{file_path}' غير موجود.")
        return []

    # توحيد أسماء الأعمدة
    df.rename(columns={
        'ID': 'frame_id', 'Shape': 'shape', 'Material': 'material', 'Size': 'size',
        'Gender': 'gender', 'Tone': 'tone', 'Color': 'color', 'Weight': 'weight'
    }, inplace=True)

    # تطبيع القيم
    for col in ['shape', 'material', 'size', 'gender', 'tone', 'color']:
        df[col] = df[col].fillna('N/A').astype(str)

    # تطبيع Gender إلى TextChoices الصحيحة
    df['gender'] = df['gender'].apply(normalize_gender)

    # وزن رقمي
    df['weight'] = pd.to_numeric(df['weight'], errors='coerce').fillna(999).astype(int)

    # style_tags اعتمادًا على الشكل/المادة
    def assign_style_tags(row):
        tags = set()
        shape = str(row.get('shape', '')).lower()
        material = str(row.get('material', '')).lower()
        if shape in ['cat-eye', 'butterfly', 'aviator']: tags.add('Fashion')
        if shape in ['square', 'rectangle', 'round', 'oval', 'browline']: tags.update({'Daily','Classic'})
        if 'plastic' in material: tags.add('Sports')
        if shape in ['rectangle', 'rimless', 'square']: tags.add('Office')
        if not tags: tags.add('General')
        return list(tags)

    df['style_tags'] = df.apply(assign_style_tags, axis=1)

    return df.to_dict(orient='records')

# ======================================================================
# القسم 4: السكور + الشرح
# ======================================================================

POINTS_MAP = {
    'shape': 25, 'size': 20, 'tone': 15,
    'purpose': 15, 'gender': 10, 'material_pref': 10, 'weight_pref': 10
}

def compute_max_possible_score(user_prefs):
    """
    يحسب الحد الأقصى الفعلي للنقاط وفق الفئات الموجودة في الدخل،
    مع احتساب كل فئة مرة واحدة فقط (حتى لو تعددت مواد/أغراض).
    """
    categories = {'shape', 'size', 'tone'}  # من تحليل الوجه دائمًا
    for pref in user_prefs:
        cat = pref.get('category')
        if cat in POINTS_MAP:
            categories.add(cat)
    return sum(POINTS_MAP[c] for c in categories)

def explain_percentage(pct):
    if pct >= 90: return "Excellent Match"
    if pct >= 75: return "Great Match"
    if pct >= 60: return "Good Match"
    return "Partial Match"

# ======================================================================
# القسم 5: التشغيل
# ======================================================================

def run_recommender_system():
    # 1) تحميل قاعدة النظارات
    glasses_db = load_glasses_from_excel("glasses_export.xlsx")
    if not glasses_db: 
        return

    # 2) قراءة JSON + تحويله
    user_input = load_user_input_from_json("user_input.json")
    analysis, user_prefs = parse_inputs(user_input)

    # 3) حساب الحد الأقصى الصحيح
    max_possible_score = compute_max_possible_score(user_prefs)

    # 4) تشغيل المحرك
    engine = SmartRecommenderKBS()
    engine.reset()

    print("="*60)
    print("⚙️  System Inputs (from JSON)")
    print(f"(Maximum possible score for these inputs is: {max_possible_score})")
    print("="*60)

    engine.declare(AnalysisResult(**analysis))
    print("--- Face Analysis Results ---")
    print(f"  - Recommended Shapes: {analysis['recommended_shapes']}")
    print(f"  - Recommended Size: {analysis['recommended_size']}")
    print(f"  - Recommended Tone: {analysis['recommended_tone']}")

    print("\n--- User Preferences ---")
    for pref in user_prefs:
        engine.declare(UserPreference(**pref))
        print(f"  - {pref['category']}: {pref['value']}")

    for g in glasses_db:
        engine.declare(Glasses(**g))

    print("\n🚀 ... Running Knowledge Engine ... 🚀\n")
    engine.run()

    # 5) جمع النتائج
    final_scores = []
    for fact in engine.facts.values():
        if isinstance(fact, RecommendationScore) and fact['score'] > 0:
            original = next((x for x in glasses_db if x['frame_id'] == fact['frame_id']), None)
            if original:
                rec = fact.as_dict()
                rec['details'] = original
                final_scores.append(rec)

    final_scores.sort(key=lambda x: x['score'], reverse=True)

    print("="*60)
    print("🏆 Top Final Recommendations")
    print("="*60)
    if not final_scores:
        print("No suitable recommendations found based on the criteria.")
        return

    for i, rec in enumerate(final_scores[:10], 1):
        d = rec['details']
        score = rec['score']
        pct = (score / max_possible_score) * 100 if max_possible_score > 0 else 0
        print(f"\n{i}. 👓 Frame ID: {d['frame_id']} | 🌟 Final Score: {score} / {max_possible_score}")
        print(f"   - Match: {pct:.1f}% ({explain_percentage(pct)})")
        print(f"   - Details: {d['shape']}, {d['size']}, {d['material']} (Gender: {d['gender']}, Tone: {d['tone']}, W:{d['weight']})")
        print(f"   - Reasons for Recommendation:")
        for reason in rec['reasons']:
            print(f"     - {reason}")

# ======================================================================
# القسم 6: نقطة الانطلاق
# ======================================================================
if __name__ == "__main__":
    run_recommender_system()
