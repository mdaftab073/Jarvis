import importlib.util
import unittest
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import Session

from app.db.database import Base
from app.db.models import Course, Student, StudyMaterial, Subject


class DatabaseIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_student_delete_cascades_courses_subjects_and_materials(self):
        student = Student(name="Cascade", email="cascade@example.com")
        subject = Subject(name="DBMS", course=Course(name="CS", student=student))
        material = StudyMaterial(
            title="Notes",
            file_path="notes.pdf",
            subject=subject,
        )
        self.db.add(material)
        self.db.commit()

        self.db.delete(student)
        self.db.commit()

        inspector = inspect(self.engine)
        for table in ("courses", "subjects", "study_materials"):
            self.assertEqual(inspector.get_table_names().count(table), 1)
        self.assertEqual(self.db.query(Course).count(), 0)
        self.assertEqual(self.db.query(Subject).count(), 0)
        self.assertEqual(self.db.query(StudyMaterial).count(), 0)

    def test_new_migration_upgrade_and_downgrade_roll_back_tables(self):
        migration_engine = create_engine("sqlite:///:memory:")
        connection = migration_engine.connect()
        connection.exec_driver_sql("CREATE TABLE students (id INTEGER PRIMARY KEY)")
        connection.exec_driver_sql("CREATE TABLE subjects (id INTEGER PRIMARY KEY)")
        migration_path = (
            Path(__file__).resolve().parents[2]
            / "alembic"
            / "versions"
            / "f2c8a4d1b709_add_semester_copilot.py"
        )
        spec = importlib.util.spec_from_file_location("semester_migration", migration_path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            migration.upgrade()
        self.assertTrue(
            {"semesters", "semester_subjects", "semester_milestones"}
            <= set(inspect(connection).get_table_names())
        )

        with Operations.context(context):
            migration.downgrade()
        self.assertFalse(
            {"semesters", "semester_subjects", "semester_milestones"}
            & set(inspect(connection).get_table_names())
        )
        connection.close()
        migration_engine.dispose()


if __name__ == "__main__":
    unittest.main()