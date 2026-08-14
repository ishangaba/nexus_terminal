from fastapi import APIRouter

from db.models import get_directional_signals
from intelligence.evaluators import calibration, signal_evaluator

router = APIRouter(prefix="/api/signals")


@router.get("/performance")
def signals_performance():
    signals = get_directional_signals()
    return signal_evaluator.performance_summary(signals)


@router.get("/calibration")
def signals_calibration():
    signals = get_directional_signals()
    return calibration.confidence_calibration(signals)
