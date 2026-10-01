"""stabilize student ownership and classify grade records

Revision ID: d14e6f2a9b31
Revises: c82d4e6f1a30
Create Date: 2026-10-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "d14e6f2a9b31"
down_revision = "c82d4e6f1a30"
branch_labels = None
depends_on = None


def upgrade():
    for table_name in ("study_activity_logs", "digital_twin_snapshots"):
        with op.batch_alter_table(table_name) as batch:
            batch.add_column(sa.Column("student_id", sa.Integer(), nullable=True))
            batch.create_foreign_key(
                f"fk_{table_name}_student_id_students",
                "students",
                ["student_id"],
                ["id"],
                ondelete="CASCADE",
            )
            batch.create_index(f"ix_{table_name}_student_id", ["student_id"])

    op.execute(
        "UPDATE attendance_records SET student_id = "
        "(SELECT student_id FROM student_academic_profiles "
        "WHERE id = attendance_records.academic_profile_id)"
    )
    op.execute(
        "UPDATE grade_records SET student_id = "
        "(SELECT student_id FROM student_academic_profiles "
        "WHERE id = grade_records.academic_profile_id)"
    )
    op.execute(
        "UPDATE deadline_items SET student_id = "
        "(SELECT student_id FROM student_academic_profiles "
        "WHERE id = deadline_items.academic_profile_id)"
    )
    op.execute(
        "UPDATE study_activity_logs SET student_id = "
        "(SELECT student_id FROM student_academic_profiles "
        "WHERE id = study_activity_logs.academic_profile_id)"
    )
    op.execute(
        "UPDATE digital_twin_snapshots SET student_id = "
        "(SELECT student_id FROM student_academic_profiles "
        "WHERE id = digital_twin_snapshots.academic_profile_id)"
    )
    op.add_column(
        "grade_records",
        sa.Column("grade_type", sa.String(length=10), nullable=True),
    )
    op.execute(
        "UPDATE grade_records SET grade_type = CASE "
        "WHEN semester IS NOT NULL AND credits IS NOT NULL AND grade_points IS NOT NULL "
        "THEN 'FINAL' ELSE 'COMPONENT' END"
    )
    op.execute("UPDATE grade_records SET grade_letter = COALESCE(grade, grade_letter)")

    for table_name in (
        "attendance_records",
        "grade_records",
        "deadline_items",
        "study_activity_logs",
        "digital_twin_snapshots",
    ):
        with op.batch_alter_table(table_name) as batch:
            if table_name == "grade_records":
                batch.drop_column("grade")
                batch.alter_column(
                    "grade_type",
                    existing_type=sa.String(length=10),
                    nullable=False,
                    server_default="COMPONENT",
                )
                batch.create_check_constraint(
                    "ck_grade_records_grade_type", "grade_type IN ('COMPONENT', 'FINAL')"
                )
                batch.create_check_constraint(
                    "ck_grade_records_credits_nonneg", "credits IS NULL OR credits >= 0"
                )
                batch.create_check_constraint(
                    "ck_grade_records_semester_positive", "semester IS NULL OR semester >= 1"
                )
                batch.create_check_constraint(
                    "ck_grade_records_grade_points_range",
                    "grade_points IS NULL OR (grade_points >= 0 AND grade_points <= 10)",
                )
            batch.alter_column(
                "student_id", existing_type=sa.Integer(), nullable=False
            )


def downgrade():
    for table_name in (
        "attendance_records",
        "grade_records",
        "deadline_items",
        "study_activity_logs",
        "digital_twin_snapshots",
    ):
        with op.batch_alter_table(table_name) as batch:
            if table_name == "grade_records":
                batch.add_column(sa.Column("grade", sa.String(length=5), nullable=True))
                batch.drop_constraint("ck_grade_records_grade_points_range", type_="check")
                batch.drop_constraint("ck_grade_records_semester_positive", type_="check")
                batch.drop_constraint("ck_grade_records_credits_nonneg", type_="check")
                batch.drop_constraint("ck_grade_records_grade_type", type_="check")
                batch.drop_column("grade_type")
            batch.alter_column(
                "student_id", existing_type=sa.Integer(), nullable=True
            )

    op.execute("UPDATE grade_records SET grade = grade_letter")

    for table_name in ("digital_twin_snapshots", "study_activity_logs"):
        with op.batch_alter_table(table_name) as batch:
            batch.drop_index(f"ix_{table_name}_student_id")
            batch.drop_constraint(f"fk_{table_name}_student_id_students", type_="foreignkey")
            batch.drop_column("student_id")
