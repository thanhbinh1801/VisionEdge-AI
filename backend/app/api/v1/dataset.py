from fastapi import APIRouter

router = APIRouter()

@router.get("/labels")
def get_custom_labels():
    return {"custom_labels": ["person", "forklift", "truck", "container", "license_plate"]}
