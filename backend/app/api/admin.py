from fastapi import APIRouter, HTTPException
from app.services.k8s import k8s_manager
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/scale-to-zero")
def scale_to_zero():
    try:
        scaled = k8s_manager.scale_down_idle_workstations()
        return {"status": "ok", "scaled_namespaces": scaled}
    except Exception as e:
        logger.error(f"Error in scale-to-zero admin endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
