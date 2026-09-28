import re
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.agents.base import BaseAgent
from app.db.models import Course, StudyPlan, Student, Subject
from app.services.study_plan_service import (
    generate_study_plan,
    get_study_plan,
    rank_topics_for_study,
)


class StudyAgent(BaseAgent):
    name = "study"

    def execute(self, context: dict) -> dict:
        db: Session = context["db"]
        student_id = context["student_id"]
        if db.query(Student.id).filter(Student.id == student_id).first() is None:
            raise ValueError("Student not found")
        goal = context.get("goal", "")
        subjects = (
            db.query(Subject)
            .join(Course, Subject.course_id == Course.id)
            .filter(Course.student_id == student_id)
            .order_by(Subject.name.asc())
            .all()
        )
        matched = [subject for subject in subjects if subject.name.casefold() in goal.casefold()]
        if matched:
            subjects = matched
        elif context.get("subject_id") is not None:
            subjects = [subject for subject in subjects if subject.id == context["subject_id"]]

        deadline = re.search(r"\b(?:in|within)\s+(\d+)\s+days?\b", goal, re.IGNORECASE)
        plans = []
        workloads = []
        for subject in subjects:
            topics = rank_topics_for_study(db, subject.id)
            workloads.append(
                {
                    "subject_id": subject.id,
                    "subject_name": subject.name,
                    "ranked_topics": topics[:5],
                }
            )
            plan = None
            if deadline and int(deadline.group(1)) > 0:
                exam_date = datetime.now(timezone.utc).date() + timedelta(
                    days=int(deadline.group(1))
                )
                plan = (
                    db.query(StudyPlan)
                    .filter(
                        StudyPlan.student_id == student_id,
                        StudyPlan.subject_id == subject.id,
                        StudyPlan.exam_date == exam_date,
                    )
                    .order_by(StudyPlan.created_at.desc(), StudyPlan.id.desc())
                    .first()
                )
                if plan is None:
                    plan = generate_study_plan(
                        db,
                        student_id=student_id,
                        subject_id=subject.id,
                        exam_date=exam_date,
                        hours_per_day=context.get("hours_per_day") or 2.0,
                    )
            else:
                plan = (
                    db.query(StudyPlan)
                    .filter(
                        StudyPlan.student_id == student_id,
                        StudyPlan.subject_id == subject.id,
                    )
                    .order_by(StudyPlan.created_at.desc(), StudyPlan.id.desc())
                    .first()
                )
            if plan is not None:
                plans.append(get_study_plan(db, plan.id))
        recommendations = [
            f"Prioritize {item['ranked_topics'][0]['topic']} for {item['subject_name']}."
            for item in workloads
            if item["ranked_topics"]
        ]
        summary = f"Prepared study guidance for {len(subjects)} subject(s)."
        return self.response(
            summary,
            recommendations,
            data={"plans": plans, "workloads": workloads},
        )