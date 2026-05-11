from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any


# =========================================================
# Predictive Astrology Engine
# Built from the user's Predictive Astrology AI Training Manual
# =========================================================
# Design goal:
# - Preserve the interpretation hierarchy from the manual
# - Prevent prediction without natal promise
# - Score repeated symbolism across methods
# - Separate topic activation, quality, timing, and manifestation level
# - Produce structured, explainable outputs
#
# This is a rule engine skeleton, not an ephemeris calculator.
# It assumes chart data and detected activations are provided as inputs.
# =========================================================


class PredictiveMethod(str, Enum):
    NATAL = "natal"
    TRANSIT = "transit"
    PROGRESSION = "progression"
    PROFECTION = "profection"
    SOLAR_RETURN = "solar_return"
    LUNAR_RETURN = "lunar_return"
    ECLIPSE = "eclipse"
    NODE = "node"
    FAST_TRIGGER = "fast_trigger"


class AspectType(str, Enum):
    CONJUNCTION = "conjunction"
    SEXTILE = "sextile"
    SQUARE = "square"
    TRINE = "trine"
    OPPOSITION = "opposition"


class PeriodTone(str, Enum):
    EASY = "easy"
    PRESSURED = "pressured"
    UNSTABLE = "unstable"
    TRANSFORMATIVE = "transformative"
    CONFUSING = "confusing"
    MIXED = "mixed"


class ManifestationLevel(str, Enum):
    LOW = "internal_feeling"
    MEDIUM = "situational_development"
    HIGH = "visible_event"


class Topic(str, Enum):
    RELATIONSHIPS = "relationships"
    CAREER = "career"
    MONEY = "money"
    HEALTH = "health"
    HOME = "home"
    CHILDREN = "children"
    IDENTITY = "identity"
    EDUCATION_TRAVEL = "education_travel"
    SOCIAL = "social"
    INNER_LIFE = "inner_life"


PLANET_MEANINGS: Dict[str, List[str]] = {
    "Sun": ["visibility", "vitality", "identity", "recognition", "purpose"],
    "Moon": ["mood", "daily life", "body", "family rhythms", "public response"],
    "Mercury": ["news", "decisions", "paperwork", "communication", "movement"],
    "Venus": ["love", "pleasure", "money flow", "beauty", "social ease", "attraction"],
    "Mars": ["action", "conflict", "surgery", "sex", "initiative", "rupture"],
    "Jupiter": ["growth", "luck", "relief", "expansion", "opportunity", "travel", "education"],
    "Saturn": ["pressure", "commitment", "delay", "endings", "maturity", "responsibility", "structure"],
    "Uranus": ["sudden change", "surprise", "breaks", "freedom", "unpredictability"],
    "Neptune": ["blur", "surrender", "spirituality", "illusion", "disappointment", "confusion"],
    "Pluto": ["power", "compulsion", "elimination", "deep transformation", "obsession", "irreversible change"],
    "North Node": ["growth direction", "openings", "fated development"],
    "South Node": ["release", "karmic repetition", "depletion", "familiarity"],
    "Chiron": ["wound activation", "healing process"],
}


HOUSE_LIBRARY: Dict[int, List[str]] = {
    1: ["self", "body", "identity", "direction", "appearance", "autonomy"],
    2: ["money", "resources", "value", "confidence", "possessions"],
    3: ["communication", "siblings", "short travel", "paperwork", "learning", "messaging"],
    4: ["home", "family", "roots", "real estate", "emotional foundation"],
    5: ["romance", "dating", "pleasure", "creativity", "children", "risk"],
    6: ["work routine", "health maintenance", "service", "habits", "stress management"],
    7: ["relationships", "commitment", "contracts", "open opponents"],
    8: ["sex", "crisis", "debt", "fear", "shared resources", "psychological transformation"],
    9: ["travel", "study", "worldview", "law", "religion", "publishing"],
    10: ["career", "status", "public life", "reputation", "ambition"],
    11: ["friends", "networks", "audience", "long-term goals"],
    12: ["retreat", "secrets", "endings", "hidden matters", "isolation", "subconscious material"],
}


TOPIC_HOUSE_MAP: Dict[Topic, List[int]] = {
    Topic.RELATIONSHIPS: [5, 7, 8],
    Topic.CAREER: [2, 6, 10],
    Topic.MONEY: [2, 8],
    Topic.HEALTH: [1, 6, 12],
    Topic.HOME: [4],
    Topic.CHILDREN: [5],
    Topic.IDENTITY: [1],
    Topic.EDUCATION_TRAVEL: [9, 3],
    Topic.SOCIAL: [11, 3],
    Topic.INNER_LIFE: [8, 12, 4],
}


TOPIC_PLANET_MAP: Dict[Topic, List[str]] = {
    Topic.RELATIONSHIPS: ["Venus", "Moon", "Mars"],
    Topic.CAREER: ["Sun", "Saturn", "Jupiter"],
    Topic.MONEY: ["Venus", "Jupiter", "Saturn", "Pluto"],
    Topic.HEALTH: ["Moon", "Mars", "Saturn", "Neptune"],
    Topic.HOME: ["Moon"],
    Topic.CHILDREN: ["Moon", "Venus", "Jupiter"],
    Topic.IDENTITY: ["Sun", "Mars", "Saturn", "Pluto"],
    Topic.EDUCATION_TRAVEL: ["Jupiter", "Mercury"],
    Topic.SOCIAL: ["Venus", "Mercury", "Jupiter"],
    Topic.INNER_LIFE: ["Moon", "Neptune", "Pluto", "Chiron"],
}


TOPIC_KEYWORDS: Dict[Topic, List[str]] = {
    Topic.RELATIONSHIPS: ["love", "dating", "commitment", "marriage", "partner", "breakup"],
    Topic.CAREER: ["career", "job", "promotion", "status", "recognition", "boss"],
    Topic.MONEY: ["money", "income", "debt", "resources", "finances"],
    Topic.HEALTH: ["health", "stress", "recovery", "body", "maintenance"],
    Topic.HOME: ["home", "family", "move", "relocation", "property"],
    Topic.CHILDREN: ["children", "fertility", "pregnancy", "creative offspring"],
    Topic.IDENTITY: ["identity", "self", "image", "direction"],
    Topic.EDUCATION_TRAVEL: ["travel", "study", "publishing", "worldview", "law"],
    Topic.SOCIAL: ["friends", "networks", "audience", "community"],
    Topic.INNER_LIFE: ["healing", "retreat", "inner process", "subconscious", "closure"],
}


METHOD_WEIGHTS: Dict[PredictiveMethod, float] = {
    PredictiveMethod.NATAL: 3.0,
    PredictiveMethod.TRANSIT: 2.8,
    PredictiveMethod.PROFECTION: 2.6,
    PredictiveMethod.SOLAR_RETURN: 2.4,
    PredictiveMethod.PROGRESSION: 2.2,
    PredictiveMethod.ECLIPSE: 2.0,
    PredictiveMethod.NODE: 1.8,
    PredictiveMethod.LUNAR_RETURN: 1.2,
    PredictiveMethod.FAST_TRIGGER: 1.0,
}


TRANSIT_PLANET_PRIORITY: Dict[str, int] = {
    "Pluto": 1,
    "Neptune": 1,
    "Uranus": 1,
    "Saturn": 2,
    "Jupiter": 2,
    "North Node": 3,
    "South Node": 3,
    "Mars": 4,
    "Venus": 5,
    "Mercury": 5,
    "Sun": 5,
    "Moon": 6,
}


@dataclass
class NatalPlanet:
    planet: str
    sign: str
    house: int
    strength: float
    dignified: bool = False
    angular: bool = False
    retrograde: bool = False
    afflicted: bool = False
    houses_ruled: List[int] = field(default_factory=list)


@dataclass
class NatalPromise:
    """Represents baseline topic potential in the natal chart."""

    topic_scores: Dict[Topic, float]
    notes: Dict[Topic, List[str]] = field(default_factory=dict)

    def score(self, topic: Topic) -> float:
        return self.topic_scores.get(topic, 0.0)


@dataclass
class Activation:
    method: PredictiveMethod
    topic: Topic
    activating_planet: Optional[str] = None
    target_planet: Optional[str] = None
    activated_house: Optional[int] = None
    aspect: Optional[AspectType] = None
    orb: Optional[float] = None
    exact: bool = False
    retrograde_phase: Optional[str] = None
    angular: bool = False
    notes: List[str] = field(default_factory=list)

    def base_weight(self) -> float:
        return METHOD_WEIGHTS[self.method]


@dataclass
class ChartContext:
    natal_planets: Dict[str, NatalPlanet]
    natal_promise: NatalPromise
    profected_house: Optional[int] = None
    time_lord: Optional[str] = None
    solar_return_emphasis: List[int] = field(default_factory=list)
    lunar_return_emphasis: List[int] = field(default_factory=list)


@dataclass
class TopicAssessment:
    topic: Topic
    natal_promise_score: float
    activation_score: float
    repeated_methods: List[PredictiveMethod]
    activated_houses: List[int]
    activated_planets: List[str]
    tone: PeriodTone
    manifestation_level: ManifestationLevel
    strongest_window: str
    likely_manifestation: str
    competing_interpretations: List[str]
    reasoning: List[str]


@dataclass
class PredictionOutput:
    main_topic: Topic
    why_active: List[str]
    tone: PeriodTone
    process_or_event: str
    strongest_window: str
    likely_manifestation: str
    competing_interpretations: List[str]
    topic_assessments: List[TopicAssessment]


class PredictiveAstrologyEngine:
    """
    Master decision engine following the user's manual.

    Mandatory order:
    1. Natal promise
    2. Timing tool
    3. Activated planet
    4. Activated house
    5. Aspect quality
    6. Repetition across methods
    7. Outcome interpretation
    """

    def __init__(self, chart: ChartContext):
        self.chart = chart

    def predict(self, activations: List[Activation], requested_topic: Optional[Topic] = None) -> PredictionOutput:
        assessments = self._assess_all_topics(activations)
        if requested_topic is not None:
            assessments = [a for a in assessments if a.topic == requested_topic]
            if not assessments:
                raise ValueError(f"No assessment generated for topic {requested_topic}.")

        main = max(assessments, key=lambda a: (a.activation_score + a.natal_promise_score))
        why_active = list(main.reasoning)
        process_or_event = self._classify_process_or_event(main)

        return PredictionOutput(
            main_topic=main.topic,
            why_active=why_active,
            tone=main.tone,
            process_or_event=process_or_event,
            strongest_window=main.strongest_window,
            likely_manifestation=main.likely_manifestation,
            competing_interpretations=main.competing_interpretations,
            topic_assessments=assessments,
        )

    def _assess_all_topics(self, activations: List[Activation]) -> List[TopicAssessment]:
        assessments: List[TopicAssessment] = []
        for topic in Topic:
            assessments.append(self._assess_topic(topic, activations))
        assessments.sort(key=lambda a: (a.activation_score + a.natal_promise_score), reverse=True)
        return assessments

    def _assess_topic(self, topic: Topic, activations: List[Activation]) -> TopicAssessment:
        natal_score = self.chart.natal_promise.score(topic)
        relevant_acts = [a for a in activations if a.topic == topic or self._activation_supports_topic(a, topic)]

        weighted_activation = 0.0
        reasoning: List[str] = []
        activated_houses: List[int] = []
        activated_planets: List[str] = []
        repeated_methods: List[PredictiveMethod] = []

        for act in relevant_acts:
            score, notes = self._score_activation(topic, act)
            weighted_activation += score
            reasoning.extend(notes)
            if act.activated_house is not None:
                activated_houses.append(act.activated_house)
            if act.activating_planet:
                activated_planets.append(act.activating_planet)
            repeated_methods.append(act.method)

        method_bonus = self._method_repetition_bonus(repeated_methods)
        house_bonus = self._cluster_bonus(activated_houses)
        planet_bonus = self._cluster_bonus(activated_planets)
        weighted_activation += method_bonus + house_bonus + planet_bonus

        reasoning.append(f"Repetition bonus from methods: {method_bonus:.2f}.")
        reasoning.append(f"House cluster bonus: {house_bonus:.2f}.")
        reasoning.append(f"Planet cluster bonus: {planet_bonus:.2f}.")

        tone = self._derive_tone(relevant_acts)
        manifestation = self._derive_manifestation(natal_score, weighted_activation, relevant_acts)
        strongest_window = self._derive_window(relevant_acts)
        likely_manifestation = self._derive_manifestation_text(topic, natal_score, relevant_acts, tone, manifestation)
        competing = self._derive_competing_interpretations(topic, natal_score, relevant_acts, tone)

        if natal_score < 0.25 and manifestation == ManifestationLevel.HIGH:
            manifestation = ManifestationLevel.MEDIUM
            reasoning.append(
                "Natal promise is weak for this topic, so symbolism is downgraded from visible event to situational development."
            )

        if natal_score < 0.10 and weighted_activation > 0:
            likely_manifestation = (
                f"{topic.value.title()} symbolism is active, but with limited natal promise it may manifest more "
                "psychologically or indirectly than as a major external event."
            )
            reasoning.append(
                "Absolute core rule applied: timing cannot invent a topic unsupported by the natal chart."
            )

        unique_methods = sorted(set(repeated_methods), key=lambda x: x.value)
        return TopicAssessment(
            topic=topic,
            natal_promise_score=round(natal_score, 2),
            activation_score=round(weighted_activation, 2),
            repeated_methods=unique_methods,
            activated_houses=sorted(set(activated_houses)),
            activated_planets=sorted(set(activated_planets)),
            tone=tone,
            manifestation_level=manifestation,
            strongest_window=strongest_window,
            likely_manifestation=likely_manifestation,
            competing_interpretations=competing,
            reasoning=reasoning,
        )

    def _score_activation(self, topic: Topic, act: Activation) -> Tuple[float, List[str]]:
        score = act.base_weight()
        notes: List[str] = [f"{act.method.value} activation contributes base weight {score:.2f}."]

        if act.method == PredictiveMethod.TRANSIT and act.activating_planet:
            priority = TRANSIT_PLANET_PRIORITY.get(act.activating_planet, 6)
            boost = {1: 1.4, 2: 1.15, 3: 0.95, 4: 0.8, 5: 0.55, 6: 0.3}[priority]
            score += boost
            notes.append(f"Transit priority boost from {act.activating_planet}: +{boost:.2f}.")

        if act.exact:
            score += 0.8
            notes.append("Exact hit boost: +0.80.")
        elif act.orb is not None:
            if act.orb <= 1.0:
                score += 0.55
                notes.append("Tight orb boost (<=1°): +0.55.")
            elif act.orb <= 2.0:
                score += 0.35
                notes.append("Moderately tight orb boost (<=2°): +0.35.")
            elif act.orb <= 3.0:
                score += 0.15
                notes.append("Useful orb boost (<=3°): +0.15.")

        if act.aspect is not None:
            aspect_mod = {
                AspectType.CONJUNCTION: 0.8,
                AspectType.SEXTILE: 0.35,
                AspectType.SQUARE: 0.65,
                AspectType.TRINE: 0.45,
                AspectType.OPPOSITION: 0.7,
            }[act.aspect]
            score += aspect_mod
            notes.append(f"Aspect {act.aspect.value} adds +{aspect_mod:.2f}.")

        if act.angular:
            score += 0.9
            notes.append("Angular amplifier: +0.90.")

        if act.activated_house in TOPIC_HOUSE_MAP[topic]:
            score += 0.8
            notes.append(f"Activated house {act.activated_house} is topic-relevant: +0.80.")

        if act.activating_planet in TOPIC_PLANET_MAP[topic]:
            score += 0.6
            notes.append(f"Activating planet {act.activating_planet} is topic-relevant: +0.60.")

        if self.chart.time_lord and (act.activating_planet == self.chart.time_lord or act.target_planet == self.chart.time_lord):
            score += 1.1
            notes.append(f"Time Lord {self.chart.time_lord} is activated: +1.10.")

        if self.chart.profected_house is not None and act.activated_house == self.chart.profected_house:
            score += 1.0
            notes.append(f"Activated house matches annual profection house {self.chart.profected_house}: +1.00.")

        if act.activated_house is not None and act.activated_house in self.chart.solar_return_emphasis:
            score += 0.9
            notes.append(f"House {act.activated_house} repeated in solar return: +0.90.")

        if act.activated_house is not None and act.activated_house in self.chart.lunar_return_emphasis:
            score += 0.35
            notes.append(f"House {act.activated_house} repeated in lunar return: +0.35.")

        if act.target_planet and act.target_planet in self.chart.natal_planets:
            natal = self.chart.natal_planets[act.target_planet]
            strength_mod = (natal.strength - 0.5) * 1.2
            score += strength_mod
            notes.append(f"Natal condition of target planet {act.target_planet} modifies score by {strength_mod:.2f}.")
            if natal.afflicted:
                notes.append(f"Natal {act.target_planet} is afflicted, so manifestation may be more difficult or strained.")
            if natal.dignified:
                notes.append(f"Natal {act.target_planet} is dignified, so activation may manifest more constructively.")

        if act.retrograde_phase:
            phase_boost = {
                "first_hit": 0.10,
                "retrograde_hit": 0.20,
                "final_hit": 0.35,
            }.get(act.retrograde_phase, 0.0)
            score += phase_boost
            notes.append(f"Retrograde phase {act.retrograde_phase} adds +{phase_boost:.2f}.")

        notes.extend(act.notes)
        return score, notes

    def _method_repetition_bonus(self, methods: List[PredictiveMethod]) -> float:
        unique_count = len(set(methods))
        if unique_count <= 1:
            return 0.0
        return min(2.5, 0.55 * (unique_count - 1))

    def _cluster_bonus(self, items: List[Any]) -> float:
        if not items:
            return 0.0
        counts: Dict[Any, int] = {}
        for item in items:
            counts[item] = counts.get(item, 0) + 1
        max_repeat = max(counts.values())
        if max_repeat <= 1:
            return 0.0
        return min(1.5, 0.35 * (max_repeat - 1))

    def _activation_supports_topic(self, act: Activation, topic: Topic) -> bool:
        if act.activated_house in TOPIC_HOUSE_MAP[topic]:
            return True
        if act.activating_planet in TOPIC_PLANET_MAP[topic]:
            return True
        if act.target_planet in TOPIC_PLANET_MAP[topic]:
            return True

        if act.target_planet and act.target_planet in self.chart.natal_planets:
            ruled = self.chart.natal_planets[act.target_planet].houses_ruled
            if any(h in TOPIC_HOUSE_MAP[topic] for h in ruled):
                return True

        return False

    def _derive_tone(self, acts: List[Activation]) -> PeriodTone:
        if not acts:
            return PeriodTone.MIXED

        pressure = 0
        ease = 0
        instability = 0
        transformation = 0
        confusion = 0

        for act in acts:
            p = act.activating_planet
            if p == "Saturn":
                pressure += 2
            elif p == "Jupiter":
                ease += 2
            elif p == "Uranus":
                instability += 2
            elif p == "Pluto":
                transformation += 2
            elif p == "Neptune":
                confusion += 2
            elif p == "Venus":
                ease += 1
            elif p == "Mars":
                pressure += 1
                instability += 1

            if act.aspect in {AspectType.SQUARE, AspectType.OPPOSITION}:
                pressure += 1
            elif act.aspect in {AspectType.TRINE, AspectType.SEXTILE}:
                ease += 1
            elif act.aspect == AspectType.CONJUNCTION:
                transformation += 1

        scores = {
            PeriodTone.PRESSURED: pressure,
            PeriodTone.EASY: ease,
            PeriodTone.UNSTABLE: instability,
            PeriodTone.TRANSFORMATIVE: transformation,
            PeriodTone.CONFUSING: confusion,
        }
        best = max(scores, key=scores.get)
        top_two = sorted(scores.values(), reverse=True)[:2]
        if len(top_two) == 2 and top_two[0] - top_two[1] <= 1:
            return PeriodTone.MIXED
        return best

    def _derive_manifestation(
        self,
        natal_score: float,
        activation_score: float,
        acts: List[Activation],
    ) -> ManifestationLevel:
        repeated_methods = len(set(a.method for a in acts))
        angular = any(a.angular for a in acts)
        if natal_score >= 0.65 and activation_score >= 8 and repeated_methods >= 3 and angular:
            return ManifestationLevel.HIGH
        if natal_score >= 0.35 and activation_score >= 4:
            return ManifestationLevel.MEDIUM
        return ManifestationLevel.LOW

    def _derive_window(self, acts: List[Activation]) -> str:
        if not acts:
            return "No strong timing window identified."

        outer = [a for a in acts if a.activating_planet in {"Pluto", "Neptune", "Uranus", "Saturn", "Jupiter"}]
        triggers = [
            a for a in acts
            if a.method in {PredictiveMethod.FAST_TRIGGER, PredictiveMethod.LUNAR_RETURN}
            or a.activating_planet in {"Mars", "Venus", "Mercury", "Sun", "Moon"}
        ]

        if outer and triggers:
            return "The strongest window is when fast planets trigger the already active slower background pattern."
        if outer:
            return "This is a longer life chapter rather than a narrow one-day event window."
        if triggers:
            return "This is a short-term timing window, likely days to weeks."
        return "Timing appears moderate rather than sharply event-specific."

    def _derive_manifestation_text(
        self,
        topic: Topic,
        natal_score: float,
        acts: List[Activation],
        tone: PeriodTone,
        manifestation: ManifestationLevel,
    ) -> str:
        tone_text = {
            PeriodTone.EASY: "supportive and opening",
            PeriodTone.PRESSURED: "serious, demanding, or tested",
            PeriodTone.UNSTABLE: "changeable, surprising, or disruptive",
            PeriodTone.TRANSFORMATIVE: "deep, intense, and life-altering",
            PeriodTone.CONFUSING: "blurred, idealized, or uncertain",
            PeriodTone.MIXED: "mixed, layered, and non-linear",
        }[tone]

        if manifestation == ManifestationLevel.HIGH:
            return f"{topic.value.title()} is strongly activated and likely to manifest externally in a {tone_text} way."
        if manifestation == ManifestationLevel.MEDIUM:
            return f"{topic.value.title()} is active and likely to show through concrete developments, with a {tone_text} tone."
        return f"{topic.value.title()} is active mainly as an internal or low-visibility process, with a {tone_text} tone."

    def _derive_competing_interpretations(
        self,
        topic: Topic,
        natal_score: float,
        acts: List[Activation],
        tone: PeriodTone,
    ) -> List[str]:
        competing: List[str] = []
        planets = {a.activating_planet for a in acts if a.activating_planet}

        if "Jupiter" in planets and "Saturn" in planets:
            competing.append(
                f"{topic.value.title()} may involve opportunity and growth, but only through discipline, realism, or delay."
            )
        if "Uranus" in planets and "Saturn" in planets:
            competing.append(
                f"{topic.value.title()} may oscillate between the need for stability and the need for freedom or rupture."
            )
        if "Neptune" in planets and "Venus" in planets and topic == Topic.RELATIONSHIPS:
            competing.append("Relationship symbolism may look romantic and magnetic but also idealized, vague, or disappointing.")
        if "Pluto" in planets and topic in {Topic.RELATIONSHIPS, Topic.IDENTITY, Topic.MONEY}:
            competing.append(
                f"The period may not simply bring change in {topic.value}; it may demand elimination, truth exposure, or irreversible restructuring."
            )
        if natal_score < 0.25:
            competing.append(
                "Because natal promise is modest, this may remain more psychological, symbolic, or indirect than fully external."
            )
        if tone == PeriodTone.MIXED:
            competing.append("Multiple contradictory symbols are active, so the period may unfold in phases rather than one simple outcome.")

        return competing

    def _classify_process_or_event(self, assessment: TopicAssessment) -> str:
        if assessment.manifestation_level == ManifestationLevel.HIGH and len(assessment.repeated_methods) >= 3:
            return "This period is ripe for a visible event, although it may still unfold through a process before peaking."
        if assessment.manifestation_level == ManifestationLevel.MEDIUM:
            return "This looks more like an unfolding process with concrete developments than a single isolated event."
        return "This appears primarily as an internal process, mood, or early-stage activation rather than a decisive event by itself."


if __name__ == "__main__":
    chart = ChartContext(
        natal_planets={
            "Venus": NatalPlanet(
                planet="Venus",
                sign="Taurus",
                house=7,
                strength=0.82,
                dignified=True,
                angular=True,
                houses_ruled=[5, 12],
            ),
            "Saturn": NatalPlanet(
                planet="Saturn",
                sign="Cancer",
                house=10,
                strength=0.48,
                afflicted=True,
                angular=True,
                houses_ruled=[9, 10],
            ),
            "Moon": NatalPlanet(
                planet="Moon",
                sign="Pisces",
                house=5,
                strength=0.70,
                houses_ruled=[8],
            ),
        },
        natal_promise=NatalPromise(
            topic_scores={
                Topic.RELATIONSHIPS: 0.82,
                Topic.CAREER: 0.60,
                Topic.MONEY: 0.44,
                Topic.HEALTH: 0.35,
                Topic.HOME: 0.30,
                Topic.CHILDREN: 0.65,
                Topic.IDENTITY: 0.55,
                Topic.EDUCATION_TRAVEL: 0.42,
                Topic.SOCIAL: 0.58,
                Topic.INNER_LIFE: 0.61,
            },
            notes={
                Topic.RELATIONSHIPS: ["Natal Venus is strong and angular in the 7th house."],
                Topic.CAREER: ["Saturn is angular and rules the 10th house."],
            },
        ),
        profected_house=7,
        time_lord="Venus",
        solar_return_emphasis=[5, 7, 10],
        lunar_return_emphasis=[7],
    )

    activations = [
        Activation(
            method=PredictiveMethod.TRANSIT,
            topic=Topic.RELATIONSHIPS,
            activating_planet="Saturn",
            target_planet="Venus",
            activated_house=7,
            aspect=AspectType.CONJUNCTION,
            orb=0.4,
            exact=True,
            angular=True,
            notes=["Serious relationship test or commitment threshold."],
        ),
        Activation(
            method=PredictiveMethod.PROFECTION,
            topic=Topic.RELATIONSHIPS,
            activating_planet="Venus",
            activated_house=7,
            notes=["7th house profection year makes relationships central."],
        ),
        Activation(
            method=PredictiveMethod.SOLAR_RETURN,
            topic=Topic.RELATIONSHIPS,
            activating_planet="Venus",
            activated_house=7,
            angular=True,
            notes=["Solar return Venus angular in relationship house."],
        ),
        Activation(
            method=PredictiveMethod.FAST_TRIGGER,
            topic=Topic.RELATIONSHIPS,
            activating_planet="Mars",
            target_planet="Venus",
            activated_house=7,
            aspect=AspectType.CONJUNCTION,
            orb=0.2,
            exact=True,
            notes=["Fast trigger for event peak."],
        ),
    ]

    engine = PredictiveAstrologyEngine(chart)
    result = engine.predict(activations, requested_topic=Topic.RELATIONSHIPS)

    print("MAIN TOPIC:", result.main_topic.value)
    print("TONE:", result.tone.value)
    print("PROCESS OR EVENT:", result.process_or_event)
    print("WINDOW:", result.strongest_window)
    print("LIKELY MANIFESTATION:", result.likely_manifestation)
    print("WHY ACTIVE:")
    for line in result.why_active:
        print("-", line)
    print("COMPETING INTERPRETATIONS:")
    for line in result.competing_interpretations:
        print("-", line)
