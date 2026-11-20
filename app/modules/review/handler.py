from fastapi import APIRouter, Response
from app.inputs import Review
from .bundle import bundle
from .decisions import decide, timeline
from .rolls import rolls_csv
from app.modules.runs.service import get

router = APIRouter()


@router.get('/api/review/{run_id}')
def reviews(run_id: str):
    return timeline(run_id)


@router.post('/api/review/{run_id}')
def commit(run_id: str, review: Review):
    return decide(run_id, review.version, review.decision, review.note)


@router.get('/api/export/{run_id}')
def export(run_id: str):
    return Response(bundle(run_id), media_type='application/json',
                    headers={'Content-Disposition': f'attachment; filename="evidence-{run_id}.json"'})


@router.get('/api/export/{run_id}/rolls.csv')
def export_rolls(run_id: str):
    payload = rolls_csv(get(run_id))
    return Response(payload.encode('utf-8'), media_type='text/csv; charset=utf-8',
                    headers={'Content-Disposition': f'attachment; filename="rolls-{run_id}.csv"'})
