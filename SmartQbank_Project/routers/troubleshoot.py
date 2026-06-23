from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import Troubleshooting

router = APIRouter()

@router.get("/list")
async def get_troubleshooting(db: Session = Depends(get_db)):
    try:
        items = db.query(Troubleshooting).order_by(Troubleshooting.id.desc()).all()
        return [
            {
                "id": item.id,
                "category": item.category,
                "title": item.title,
                "description": item.description,
                "tags": item.tags
            } for item in items
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
