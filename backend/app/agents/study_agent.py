import re
from datetime import datetime, timedelta, timezone

from app.agents.base import BaseAgent, execute_agent_tool


def rank_topics_for_study(db, student_id, subject_id):
    return execute_agent_tool("study_plan", {"db": db, "student_id": student_id, "subject_id": subject_id, "action": "rank_topics"})


def generate_study_plan(db, student_id, subject_id, exam_date, hours_per_day):
    return execute_agent_tool("study_plan", {"db": db, "student_id": student_id, "subject_id": subject_id, "action": "generate", "exam_date": exam_date, "hours_per_day": hours_per_day})


def get_study_plan(db, plan_id=None, student_id=None, subject_id=None, exam_date=None):
    action = "get" if plan_id is not None else "get_latest"
    return execute_agent_tool("study_plan", {"db": db, "student_id": student_id, "subject_id": subject_id, "plan_id": plan_id, "exam_date": exam_date, "action": action})


def find_study_plan(db, student_id, subject_id, exam_date=None):
    return execute_agent_tool("study_plan", {"db": db, "student_id": student_id, "subject_id": subject_id, "exam_date": exam_date, "action": "get_latest"})


class StudyAgent(BaseAgent):
    name = "study"

    def execute(self, context: dict) -> dict:
        db = context["db"]
        student_id = context["student_id"]
        goal = context.get("goal", "")
        subjects = self.invoke_tool("student_subjects", context)

        deadline = re.search(r"\b(?:in|within)\s+(\d+)\s+days?\b", goal, re.IGNORECASE)
        plans = []
        workloads = []
        for subject in subjects:
            topics = rank_topics_for_study(db, student_id, subject.id)
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
                plan = find_study_plan(db, student_id, subject.id, exam_date)
                if plan is None:
                    plan = generate_study_plan(
                        db,
                        student_id=student_id,
                        subject_id=subject.id,
                        exam_date=exam_date,
                        hours_per_day=context.get("hours_per_day") or 2.0,
                    )
            else:
                plan = find_study_plan(db, student_id, subject.id)
            if plan is not None:
                plans.append(get_study_plan(db, plan.id, student_id=student_id) if getattr(plan, "id", None) else plan)
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