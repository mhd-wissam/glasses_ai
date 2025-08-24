# face/kbs_engine1.py
from experta import *

class FaceData(Fact):
    face_shape = Field(str, mandatory=False)
    face_width_cm = Field(float, mandatory=False)
    skin_tone = Field(str, mandatory=False)


class GlassesRecommender(KnowledgeEngine):
    def __init__(self):
        super().__init__()
        self.recommended_shape = []
        self.recommended_size = None
        self.recommended_tone = None

    @Rule(FaceData(face_shape='Round'))
    def shape_for_round(self):
        self.recommended_shape = [
            'Square', 'Rectangle', 'Cat-Eye', 'Wayfarer', 'Clubmaster'
        ]

    @Rule(FaceData(face_shape='Oval'))
    def shape_for_oval(self):
        self.recommended_shape = [
            'Rectangle', 'Square', 'Geometric', 'Wayfarer', 'Butterfly'
        ]

    @Rule(FaceData(face_shape='Square'))
    def shape_for_square(self):
        self.recommended_shape = [
            'Round', 'Oval', 'Cat-Eye', 'Shield'
        ]

    @Rule(FaceData(face_shape='Heart'))
    def shape_for_heart(self):
        self.recommended_shape = [
            'Oval', 'Round', 'Cat-Eye', 'Browline', 'Rimless'
        ]

    @Rule(FaceData(face_shape='Triangle'))
    def shape_for_triangle(self):
        self.recommended_shape = [
            'Cat-Eye', 'Aviator', 'Butterfly', 'Clubmaster'
        ]

    @Rule(FaceData(face_shape='Diamond'))
    def shape_for_diamond(self):
        self.recommended_shape = [
            'Oval', 'Rimless', 'Hexagonal / Octagonal', 'Geometric'
        ]

    @Rule(FaceData(face_shape='Oblong'))
    def shape_for_oblong(self):
        self.recommended_shape = [
            'Round', 'Geometric', 'Aviator', 'Wayfarer', 'Shield'
        ]

    @Rule(FaceData(face_width_cm=P(lambda w: 12.6 <= w <= 13.2)))
    def size_medium(self):
        self.recommended_size = 'Medium'

    @Rule(FaceData(face_width_cm=P(lambda w: 13.3 <= w <= 14.0)))
    def size_large(self):
        self.recommended_size = 'Large'

    @Rule(FaceData(face_width_cm=P(lambda w: w > 14.0)))
    def size_xlarge(self):
        self.recommended_size = 'Extra Large'

    @Rule(FaceData(face_width_cm=P(lambda w: w < 12.6)))
    def size_small(self):
        self.recommended_size = 'Small'

    @Rule(FaceData(skin_tone='Dark'))
    def tone_dark(self):
        self.recommended_tone = 'Light'

    @Rule(FaceData(skin_tone='Medium'))
    def tone_medium(self):
        self.recommended_tone = 'Medium'

    @Rule(FaceData(skin_tone='Light'))
    def tone_light(self):
        self.recommended_tone = 'Dark'

    def run_engine(self, face_shape=None, face_width_cm=None, skin_tone=None):
        self.reset()
        fact_data = {}
        if face_shape is not None:
            fact_data["face_shape"] = face_shape
        if face_width_cm is not None:
            fact_data["face_width_cm"] = face_width_cm
        if skin_tone is not None:
            fact_data["skin_tone"] = skin_tone

        self.declare(FaceData(**fact_data))
        self.run()
        return {
            'recommended_shape': self.recommended_shape,
            'recommended_size': self.recommended_size,
            'recommended_tone': self.recommended_tone,
        }

