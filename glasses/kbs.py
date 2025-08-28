# glasses/kbs.py
import collections, collections.abc, sys
from experta import KnowledgeEngine, Rule, Fact, Field, MATCH, AS, TEST, NOT

# إصلاح compat
if sys.version_info.major == 3 and sys.version_info.minor >= 10:
    collections.Mapping = collections.abc.Mapping
    collections.MutableMapping = collections.abc.MutableMapping

# ===== Facts =====
class AnalysisResult(Fact):
    recommended_shapes = Field(list)
    recommended_size = Field(str)
    recommended_tone = Field(str)

class UserPreference(Fact):
    category = Field(str, mandatory=True)
    value = Field(object, mandatory=True)

class GlassesFact(Fact):
    frame_id = Field(int, mandatory=True)
    shape = Field(str)
    material = Field(str)
    size = Field(str)
    gender = Field(str)
    tone = Field(str)
    color = Field(str)
    weight = Field(int)
    style_tags = Field(list, default=[])

class RecommendationScore(Fact):
    frame_id = Field(int, mandatory=True)
    score = Field(int, default=0)
    reasons = Field(list, default=[])

# ===== Rules =====
class SmartRecommenderKBS(KnowledgeEngine):
    def _update_score(self, score_fact, points, reason_key):
        reason_text = f"{reason_key} (+{points})"
        self.modify(score_fact,
            score=score_fact['score'] + points,
            reasons=list(score_fact['reasons']) + [reason_text]
        )

    @Rule(GlassesFact(frame_id=MATCH.fid),
          NOT(RecommendationScore(frame_id=MATCH.fid)), salience=1000)
    def initialize_score(self, fid):
        self.declare(RecommendationScore(frame_id=fid, score=0, reasons=[]))

    @Rule(AnalysisResult(recommended_shapes=MATCH.rec_shapes),
          GlassesFact(frame_id=MATCH.fid, shape=MATCH.g_shape),
          AS.score_fact << RecommendationScore(frame_id=MATCH.fid, reasons=MATCH.reasons),
          TEST(lambda g_shape, rec_shapes: g_shape in rec_shapes),
          TEST(lambda reasons: not any("Matches Face Shape Analysis" in r for r in reasons)),
          salience=100)
    def match_shape(self, score_fact):
        self._update_score(score_fact, 25, "Matches Face Shape Analysis")

    @Rule(AnalysisResult(recommended_size=MATCH.rec_size),
          GlassesFact(frame_id=MATCH.fid, size=MATCH.g_size),
          AS.score_fact << RecommendationScore(frame_id=MATCH.fid, reasons=MATCH.reasons),
          TEST(lambda g_size, rec_size: g_size == rec_size),
          TEST(lambda reasons: not any("Matches Face Size Analysis" in r for r in reasons)),
          salience=95)
    def match_size(self, score_fact):
        self._update_score(score_fact, 20, "Matches Face Size Analysis")

    @Rule(AnalysisResult(recommended_tone=MATCH.rec_tone),
          GlassesFact(frame_id=MATCH.fid, tone=MATCH.g_tone),
          AS.score_fact << RecommendationScore(frame_id=MATCH.fid, reasons=MATCH.reasons),
          TEST(lambda g_tone, rec_tone: g_tone == rec_tone),
          TEST(lambda reasons: not any("Matches Skin Tone Analysis" in r for r in reasons)),
          salience=90)
    def match_tone(self, score_fact):
        self._update_score(score_fact, 15, "Matches Skin Tone Analysis")

    @Rule(UserPreference(category='purpose', value=MATCH.user_purposes),
          GlassesFact(frame_id=MATCH.fid, style_tags=MATCH.g_tags),
          AS.score_fact << RecommendationScore(frame_id=MATCH.fid, reasons=MATCH.reasons),
          TEST(lambda user_purposes, g_tags: bool(
              {p.lower() for p in user_purposes} & {t.lower() for t in g_tags}
          )),
          TEST(lambda reasons: not any("Matches User's Purpose" in r for r in reasons)),
          salience=80)
    def match_purpose(self, score_fact):
        self._update_score(score_fact, 15, "Matches User's Purpose")

    @Rule(UserPreference(category='gender', value=MATCH.user_gender),
          GlassesFact(frame_id=MATCH.fid, gender=MATCH.g_gender),
          AS.score_fact << RecommendationScore(frame_id=MATCH.fid, reasons=MATCH.reasons),
          TEST(lambda user_gender, g_gender: user_gender.lower() == g_gender.lower()),
          TEST(lambda reasons: not any("Matches User's Gender" in r for r in reasons)),
          salience=75)
    def match_gender(self, score_fact):
        self._update_score(score_fact, 10, "Matches User's Gender")

    @Rule(UserPreference(category='material_pref', value=MATCH.user_material),
          GlassesFact(frame_id=MATCH.fid, material=MATCH.g_material),
          AS.score_fact << RecommendationScore(frame_id=MATCH.fid, reasons=MATCH.reasons),
          TEST(lambda user_material, g_material: user_material.lower() in g_material.lower()),
          TEST(lambda reasons: not any("Matches User's Material Preference" in r for r in reasons)),
          salience=70)
    def match_material(self, score_fact):
        self._update_score(score_fact, 10, "Matches User's Material Preference")

    @Rule(UserPreference(category='weight_pref', value='lightweight'),
          GlassesFact(frame_id=MATCH.fid, weight=MATCH.g_weight),
          AS.score_fact << RecommendationScore(frame_id=MATCH.fid, reasons=MATCH.reasons),
          TEST(lambda g_weight: g_weight is not None and g_weight <= 18),
          TEST(lambda reasons: not any("Matches User's Lightweight Preference" in r for r in reasons)),
          salience=60)
    def match_weight(self, score_fact):
        self._update_score(score_fact, 10, "Matches User's Lightweight Preference")


POINTS_MAP = {'shape':25,'size':20,'tone':15,'purpose':15,'gender':10,'material_pref':10,'weight_pref':10}

def compute_max_possible_score(user_prefs):
    cats = {'shape','size','tone'}
    for pref in user_prefs:
        if pref['category'] in POINTS_MAP:
            cats.add(pref['category'])
    return sum(POINTS_MAP[c] for c in cats)
