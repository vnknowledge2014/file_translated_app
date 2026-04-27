"""Glossary routes — GET, POST (upload CSV), DELETE.

Supports multilingual glossaries with configurable source/target language pairs.
"""

import csv
from io import StringIO
from fastapi import APIRouter, File, Request, UploadFile, HTTPException, Form, Query

from app.config import settings
from app.database import get_all_glossary_terms, add_glossary_terms, delete_glossary_term
from app.languages import list_languages

router = APIRouter()


@router.get("/glossary")
async def get_glossary(
    request: Request,
    source_lang: str = Query(None),
    target_lang: str = Query(None),
    domain: str = Query(None),
):
    """Get all glossary terms, optionally filtered by language pair and domain."""
    sl = source_lang or settings.SOURCE_LANG
    tl = target_lang or settings.TARGET_LANG
    dom = domain or settings.DEFAULT_DOMAIN

    async with request.app.state.db_session_factory() as session:
        terms = await get_all_glossary_terms(session, source_lang=sl, target_lang=tl, domain=dom)
        return {
            "source_lang": sl,
            "target_lang": tl,
            "terms": [
                {
                    "id": t.id,
                    "source_text": t.source_text,
                    "target_text": t.target_text,
                    # Backward-compatible aliases
                    "jp": t.source_text,
                    "vi": t.target_text,
                    "context": t.context,
                    "source_lang": t.source_lang,
                    "target_lang": t.target_lang,
                    "domain": t.domain,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in terms
            ],
        }


@router.get("/languages")
async def get_languages():
    """List all supported languages for the UI language selector."""
    return {
        "languages": list_languages(),
        "current": {
            "source": settings.SOURCE_LANG,
            "target": settings.TARGET_LANG,
        },
    }


@router.post("/glossary/upload")
async def upload_glossary(
    request: Request,
    file: UploadFile = File(...),
    replace: bool = Form(True),
    source_lang: str = Form(None),
    target_lang: str = Form(None),
    domain: str = Form(None),
):
    """Upload a CSV file containing glossary terms.
    
    Expected CSV columns (header row is optional but recommended):
    source_text, target_text, context (optional)
    
    Also accepts legacy format: jp, vi, context
    """
    sl = source_lang or settings.SOURCE_LANG
    tl = target_lang or settings.TARGET_LANG
    dom = domain or settings.DEFAULT_DOMAIN

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported.")

    content = await file.read()
    try:
        text_content = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text_content = content.decode("shift_jis")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File must be UTF-8 or Shift-JIS encoded.")

    f = StringIO(text_content)
    reader = csv.reader(f)
    
    terms = []
    headers_skipped = False
    
    for row in reader:
        if not row or not any(row):
            continue
            
        # Try to detect and skip header row
        if not headers_skipped and len(row) >= 2:
            first_lower = row[0].strip().lower()
            header_keywords = {
                "jp", "japanese", "tiếng nhật", "nguồn", "source",
                "source_text", "原文", "원문", "source text",
            }
            if first_lower in header_keywords:
                headers_skipped = True
                continue
            headers_skipped = True
            
        if len(row) >= 2:
            terms.append({
                "source_text": row[0],
                "target_text": row[1],
                "context": row[2] if len(row) > 2 else "",
            })

    if not terms:
        raise HTTPException(status_code=400, detail="No valid terms found in CSV.")

    async with request.app.state.db_session_factory() as session:
        added = await add_glossary_terms(
            session, terms, replace=replace,
            source_lang=sl, target_lang=tl, domain=dom,
        )
        return {
            "status": "success",
            "added": added,
            "replaced": replace,
            "source_lang": sl,
            "target_lang": tl,
            "domain": dom,
        }


@router.delete("/glossary/{term_id}")
async def delete_term(request: Request, term_id: int):
    """Delete a specific glossary term."""
    async with request.app.state.db_session_factory() as session:
        success = await delete_glossary_term(session, term_id)
        if not success:
            raise HTTPException(status_code=404, detail="Term not found")
        return {"status": "success"}
