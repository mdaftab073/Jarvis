from app.jobs.registry import register_job
from app.services.study_material_processing import process_pdf_material


@register_job("process_pdf_material", "Extract, chunk, embed, and index an uploaded PDF.")
def process_pdf_job(payload: dict) -> dict:
    material_id = int(payload["material_id"])
    return process_pdf_material(material_id)