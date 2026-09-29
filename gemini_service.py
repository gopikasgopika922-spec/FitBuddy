from __future__ import annotations

from dataclasses import dataclass

from .config import get_settings
from .schemas import UserInput


@dataclass
class GeminiService:
    """Gemini adapter with a deterministic demo fallback."""

    def __post_init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.client = None
        if settings.gemini_api_key and not settings.demo_mode:
            from google import genai
            self.client = genai.Client(api_key=settings.gemini_api_key)

    def _generate(self, model: str, prompt: str, system_instruction: str, max_tokens: int = 5000) -> str:
        if self.settings.demo_mode or self.client is None:
            raise RuntimeError("demo-fallback")

        from google.genai import types

        response = self.client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
                max_output_tokens=max_tokens,
            ),
        )
        text = getattr(response, "text", None)
        if not text:
            raise RuntimeError("Gemini returned an empty response.")
        return text.strip()

    @staticmethod
    def _is_quota_error(exc: Exception) -> bool:
        return (
            getattr(exc, "code", None) == 429
            or getattr(exc, "status", None) == "RESOURCE_EXHAUSTED"
        )

    @staticmethod
    def _demo_plan(user: UserInput) -> str:
        goal = user.goal.title()
        intensity = user.intensity.title()
        return f"""# FitBuddy 7-Day Plan

**Profile:** {user.username} | Age {user.age} | {user.weight:g} kg
**Goal:** {goal} | **Intensity:** {intensity}

## Day 1 — Full Body
- Warm-up: 8 minutes brisk walking and dynamic mobility
- Main: Squats 3×10, push-ups 3×8–12, rows 3×10, glute bridges 3×12
- Cooldown: 5 minutes easy stretching

## Day 2 — Cardio + Core
- Warm-up: 5 minutes easy cardio
- Main: 20–30 minutes moderate cardio; plank 3×30–45 sec; dead bug 3×10/side
- Cooldown: 5 minutes relaxed walking

## Day 3 — Recovery
- 20–30 minutes easy walking
- 10 minutes mobility or gentle stretching
- Keep effort comfortable

## Day 4 — Strength
- Warm-up: 8 minutes
- Main: Lunges 3×10/side, incline push-ups 3×10, hip hinge 3×10, shoulder press 3×10
- Cooldown: 5–8 minutes

## Day 5 — Cardio + Mobility
- 25–35 minutes low-to-moderate cardio
- 10 minutes full-body mobility
- Cooldown: relaxed breathing

## Day 6 — Full Body
- Warm-up: 8 minutes
- Main: Step-ups 3×10/side, rows 3×10, squats 3×10, plank 3×30 sec
- Cooldown: 5 minutes

## Day 7 — Rest / Active Recovery
- Optional easy walk for 20–30 minutes
- Gentle stretching
- Prioritize hydration and sleep

**Progression:** Start conservatively and increase volume gradually only if recovery is good.
**Safety:** Stop if you experience sharp pain, dizziness, chest pain, or unusual shortness of breath, and seek appropriate professional care.
"""

    @staticmethod
    def _demo_tip(user: UserInput) -> str:
        tips = {
            "weight loss": "Build meals around protein, vegetables, whole-food carbohydrates, and adequate water. Aim for sustainable portions rather than extreme restriction.",
            "muscle gain": "Include a protein-rich food at each main meal and eat enough overall energy to support training and recovery.",
            "general wellness": "Prioritize regular hydration, balanced meals, daily movement, and a consistent sleep routine.",
            "flexibility": "Hydrate well and include a variety of fruits, vegetables, protein, and healthy fats while practicing mobility consistently.",
            "endurance": "Pair regular carbohydrate-rich whole foods with protein and fluids so training sessions have adequate fuel and recovery support.",
        }
        return tips[user.goal]

    def generate_workout(self, user: UserInput) -> str:
        prompt = f"""
Create a personalized 7-day general-fitness workout plan.

User:
- Name: {user.username}
- Age: {user.age}
- Weight: {user.weight} kg
- Goal: {user.goal}
- Preferred intensity: {user.intensity}

Requirements:
- Exactly seven labeled days.
- For every day provide a warm-up, main workout, and cooldown/recovery.
- Include exercises with sets/reps or duration and rest guidance.
- Include at least one recovery/rest-oriented day.
- Keep the plan practical and progressive.
- Do not diagnose, treat, or claim to prevent disease.
- Do not prescribe extreme calorie restriction or unsafe training.
- If a movement is unsuitable, offer a safer general alternative.
- Return clean Markdown only.
"""
        system = (
            "You are FitBuddy's workout-planning assistant. "
            "Create general wellness and fitness guidance. "
            "Be conservative with safety and clearly avoid medical claims."
        )
        try:
            return self._generate(self.settings.workout_model, prompt, system)
        except RuntimeError as exc:
            if str(exc) == "demo-fallback":
                return self._demo_plan(user)
            raise
        except Exception as exc:
            if self._is_quota_error(exc):
                return (
                    self._demo_plan(user)
                    + "\n\n> Gemini quota unavailable; showing a demo fallback. "
                    "Check your API project quota or billing to restore AI generation."
                )
            raise

    def generate_nutrition_tip(self, user: UserInput) -> str:
        prompt = f"""
Give one concise nutrition or recovery tip for this fitness profile:
goal={user.goal}, intensity={user.intensity}, age={user.age}, weight={user.weight} kg.
Keep it practical, non-diagnostic, and under 100 words.
"""
        system = "You provide concise general wellness nutrition and recovery guidance, not medical advice."
        try:
            return self._generate(self.settings.nutrition_model, prompt, system, max_tokens=300)
        except RuntimeError as exc:
            if str(exc) == "demo-fallback":
                return self._demo_tip(user)
            raise
        except Exception as exc:
            if self._is_quota_error(exc):
                return (
                    self._demo_tip(user)
                    + " (Demo fallback: Gemini quota unavailable.)"
                )
            raise

    def update_workout(self, user: UserInput, original_plan: str, feedback: str) -> str:
        prompt = f"""
Revise this existing 7-day general-fitness plan using the user's feedback.

User:
- Name: {user.username}
- Age: {user.age}
- Weight: {user.weight} kg
- Goal: {user.goal}
- Intensity: {user.intensity}

Original plan:
---BEGIN PLAN---
{original_plan}
---END PLAN---

Feedback:
---BEGIN FEEDBACK---
{feedback}
---END FEEDBACK---

Requirements:
- Preserve the seven-day structure.
- Implement reasonable requested changes.
- Keep at least one recovery/rest-oriented day unless the feedback explicitly requests otherwise.
- Keep exercises, volume, and progression appropriate to the selected intensity.
- Avoid medical claims and unsafe extremes.
- Return the complete revised plan in Markdown, not a discussion of the changes.
"""
        system = "You revise general fitness plans conservatively and transparently, without providing medical treatment."
        try:
            return self._generate(self.settings.workout_model, prompt, system)
        except RuntimeError as exc:
            if str(exc) == "demo-fallback":
                return (
                    original_plan
                    + "\n\n## AI Feedback Update — Demo Mode\n"
                    + f"Applied feedback: **{feedback}**\n\n"
                    "For a live Gemini revision, set `GEMINI_API_KEY` and `DEMO_MODE=false`."
                )
            raise


_service: GeminiService | None = None


def get_gemini_service() -> GeminiService:
    global _service
    if _service is None:
        _service = GeminiService()
    return _service
