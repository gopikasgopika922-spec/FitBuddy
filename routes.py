from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .gemini_service import get_gemini_service
from .models import Plan, User, utc_now
from .schemas import FeedbackRequest, UserInput

router = APIRouter()
api_router = APIRouter(prefix="/api", tags=["api"])
security = HTTPBasic()
templates = Jinja2Templates(directory="templates")


def authenticate_admin(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    settings = get_settings()
    if (
        credentials.username != settings.admin_username
        or credentials.password != settings.admin_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def _get_user(db: Session, user_id: str) -> User | None:
    return db.scalar(select(User).where(User.user_id == user_id))


def _get_latest_plan(db: Session, user_id: str) -> Plan | None:
    return db.scalar(
        select(Plan)
        .where(Plan.user_id == user_id)
        .order_by(Plan.created_at.desc())
    )


def _save_generation(db: Session, data: UserInput, workout: str, tip: str) -> tuple[User, Plan]:
    user = _get_user(db, data.user_id)
    if user is None:
        user = User(
            user_id=data.user_id,
            username=data.username,
            age=data.age,
            weight=data.weight,
            goal=data.goal,
            intensity=data.intensity,
        )
        db.add(user)
    else:
        user.username = data.username
        user.age = data.age
        user.weight = data.weight
        user.goal = data.goal
        user.intensity = data.intensity

    plan = Plan(
        user_id=data.user_id,
        original_plan=workout,
        nutrition_tip=tip,
    )
    db.add(plan)
    db.commit()
    db.refresh(user)
    db.refresh(plan)
    return user, plan


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"error": None},
    )


@router.post("/generate-workout", response_class=HTMLResponse)
def generate_workout_form(
    request: Request,
    username: str = Form(...),
    user_id: str = Form(...),
    age: int = Form(...),
    weight: float = Form(...),
    goal: str = Form(...),
    intensity: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        data = UserInput(
            username=username,
            user_id=user_id,
            age=age,
            weight=weight,
            goal=goal,
            intensity=intensity,
        )
        service = get_gemini_service()
        workout = service.generate_workout(data)
        tip = service.generate_nutrition_tip(data)
        user, plan = _save_generation(db, data, workout, tip)
        return templates.TemplateResponse(
            request=request,
            name="result.html",
            context={
                "user": user,
                "plan": plan,
                "current_plan": plan.original_plan,
                "message": "Your 7-day plan has been generated.",
                "error": None,
            },
        )
    except Exception as exc:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"error": f"Could not generate the plan: {exc}"},
            status_code=400,
        )


@router.post("/submit-feedback", response_class=HTMLResponse)
def submit_feedback_form(
    request: Request,
    user_id: str = Form(...),
    feedback: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        data = FeedbackRequest(user_id=user_id, feedback=feedback)
        user = _get_user(db, data.user_id)
        plan = _get_latest_plan(db, data.user_id)
        if not user or not plan:
            raise ValueError("User or workout plan not found.")

        user_input = UserInput(
            username=user.username,
            user_id=user.user_id,
            age=user.age,
            weight=user.weight,
            goal=user.goal,
            intensity=user.intensity,
        )
        updated = get_gemini_service().update_workout(
            user_input, plan.original_plan, data.feedback
        )
        plan.updated_plan = updated
        plan.feedback = data.feedback
        plan.updated_at = utc_now()
        db.commit()
        db.refresh(plan)

        return templates.TemplateResponse(
            request=request,
            name="result.html",
            context={
                "user": user,
                "plan": plan,
                "current_plan": plan.updated_plan,
                "message": "Your plan was updated from the submitted feedback.",
                "error": None,
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/view-all-users", response_class=HTMLResponse)
def view_all_users(
    request: Request,
    _: str = Depends(authenticate_admin),
    db: Session = Depends(get_db),
):
    users = db.scalars(select(User).order_by(User.created_at.desc())).all()
    plans = db.scalars(select(Plan).order_by(Plan.created_at.desc())).all()
    latest_by_user: dict[str, Plan] = {}
    for plan in plans:
        latest_by_user.setdefault(plan.user_id, plan)

    rows = [{"user": user, "plan": latest_by_user.get(user.user_id)} for user in users]
    return templates.TemplateResponse(
        request=request,
        name="all_users.html",
        context={"rows": rows},
    )


@api_router.get("/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
        "ai_mode": "demo" if settings.demo_mode or not settings.gemini_api_key else "gemini",
    }


@api_router.post("/generate")
def generate_api(data: UserInput, db: Session = Depends(get_db)):
    try:
        service = get_gemini_service()
        workout = service.generate_workout(data)
        tip = service.generate_nutrition_tip(data)
        user, plan = _save_generation(db, data, workout, tip)
        return {
            "user": {
                "user_id": user.user_id,
                "username": user.username,
                "age": user.age,
                "weight": user.weight,
                "goal": user.goal,
                "intensity": user.intensity,
            },
            "plan_id": plan.id,
            "workout_plan": plan.original_plan,
            "nutrition_tip": plan.nutrition_tip,
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI generation failed: {exc}") from exc


@api_router.post("/feedback")
def feedback_api(data: FeedbackRequest, db: Session = Depends(get_db)):
    user = _get_user(db, data.user_id)
    plan = _get_latest_plan(db, data.user_id)
    if not user or not plan:
        raise HTTPException(status_code=404, detail="User or plan not found.")

    user_input = UserInput(
        username=user.username,
        user_id=user.user_id,
        age=user.age,
        weight=user.weight,
        goal=user.goal,
        intensity=user.intensity,
    )
    try:
        updated = get_gemini_service().update_workout(
            user_input, plan.original_plan, data.feedback
        )
        plan.updated_plan = updated
        plan.feedback = data.feedback
        plan.updated_at = utc_now()
        db.commit()
        return {"plan_id": plan.id, "updated_plan": updated, "feedback": data.feedback}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI update failed: {exc}") from exc


@api_router.get("/users/{user_id}")
def get_user_api(user_id: str, db: Session = Depends(get_db)):
    user = _get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    plan = _get_latest_plan(db, user_id)
    return {
        "user": {
            "user_id": user.user_id,
            "username": user.username,
            "age": user.age,
            "weight": user.weight,
            "goal": user.goal,
            "intensity": user.intensity,
        },
        "plan": None if not plan else {
            "id": plan.id,
            "original_plan": plan.original_plan,
            "updated_plan": plan.updated_plan,
            "nutrition_tip": plan.nutrition_tip,
            "feedback": plan.feedback,
        },
    }


@api_router.get("/users")
def list_users(
    _: str = Depends(authenticate_admin),
    db: Session = Depends(get_db),
):
    users = db.scalars(select(User).order_by(User.created_at.desc())).all()
    return [
        {
            "user_id": user.user_id,
            "username": user.username,
            "age": user.age,
            "weight": user.weight,
            "goal": user.goal,
            "intensity": user.intensity,
        }
        for user in users
    ]
