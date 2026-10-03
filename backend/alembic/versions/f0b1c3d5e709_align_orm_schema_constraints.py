"""align database check constraints with ORM models

Revision ID: f0b1c3d5e709
Revises: e7b4c1d9a260
Create Date: 2026-10-03 00:00:00.000000
"""

from alembic import op


revision = "f0b1c3d5e709"
down_revision = "e7b4c1d9a260"
branch_labels = None
depends_on = None


CHECK_CONSTRAINTS = (
    (
        "student_academic_profiles",
        "ck_academic_profiles_status",
        "academic_status IN ('ACTIVE', 'PROBATION', 'GRADUATED', 'SUSPENDED', 'DROPOUT')",
    ),
    (
        "student_academic_profiles",
        "ck_academic_profiles_cpi",
        "current_cpi IS NULL OR (current_cpi >= 0 AND current_cpi <= 10)",
    ),
    (
        "student_academic_profiles",
        "ck_academic_profiles_spi",
        "current_spi IS NULL OR (current_spi >= 0 AND current_spi <= 10)",
    ),
    ("attendance_records", "ck_attendance_attended_nonneg", "attended_classes >= 0"),
    ("attendance_records", "ck_attendance_total_nonneg", "total_classes >= 0"),
    (
        "attendance_records",
        "ck_attendance_percentage",
        "attendance_percentage IS NULL OR (attendance_percentage >= 0 AND attendance_percentage <= 100)",
    ),
    (
        "grade_records",
        "ck_grade_records_component_type",
        "component_type IN ('CT1', 'CT2', 'CT3', 'ASSIGNMENT', 'LAB', 'END_SEM', 'MID_SEM', 'VIVA', 'PROJECT', 'OTHER')",
    ),
    (
        "grade_records",
        "ck_grade_records_obtained_marks_nonneg",
        "obtained_marks IS NULL OR obtained_marks >= 0",
    ),
    ("grade_records", "ck_grade_records_max_marks_pos", "max_marks > 0"),
    (
        "deadline_items",
        "ck_deadline_items_type",
        "item_type IN ('EXAM', 'ASSIGNMENT', 'PROJECT', 'LAB_SUBMISSION', 'QUIZ', 'PRESENTATION', 'OTHER')",
    ),
    (
        "deadline_items",
        "ck_deadline_items_priority",
        "priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
    ),
    (
        "study_activity_logs",
        "ck_study_activity_type",
        "activity_type IN ('READING', 'FLASHCARD', 'QUIZ', 'PROBLEM_SOLVING', 'VIDEO', 'REVISION', 'GROUP_STUDY', 'OTHER')",
    ),
    (
        "study_activity_logs",
        "ck_study_activity_duration_nonneg",
        "duration_minutes >= 0",
    ),
    (
        "digital_twin_snapshots",
        "ck_snapshot_risk_level",
        "risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
    ),
    (
        "digital_twin_snapshots",
        "ck_snapshot_overall_readiness",
        "overall_readiness IS NULL OR (overall_readiness >= 0 AND overall_readiness <= 100)",
    ),
)


def upgrade() -> None:
    for table_name, constraint_name, condition in CHECK_CONSTRAINTS:
        op.create_check_constraint(constraint_name, table_name, condition)


def downgrade() -> None:
    for table_name, constraint_name, _ in reversed(CHECK_CONSTRAINTS):
        op.drop_constraint(constraint_name, table_name, type_="check")
