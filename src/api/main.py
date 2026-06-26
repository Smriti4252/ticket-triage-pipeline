# main.py
# FastAPI REST API for Ticket Triage System
# Exposes endpoints to query, update, and get stats on tickets

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from storage.db import (
    get_all_tickets,
    get_ticket_by_id,
    update_ticket_status,
    get_stats
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Ticket Triage API",
    description="AI-powered customer support ticket triage system",
    version="1.0.0"
)


# ── Request/Response Models ──────────────────────────────────────────
class StatusUpdate(BaseModel):
    """Request body for updating ticket status."""
    status: str  # new | in_review | assigned | resolved


# ── Health Check ─────────────────────────────────────────────────────
@app.get("/")
def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Ticket Triage API is running"}


# ── Get All Tickets ───────────────────────────────────────────────────
@app.get("/tickets")
def list_tickets(
    status: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None
):
    """Get all tickets with optional filters.
    
    Query params:
    - status: new | in_review | assigned | resolved
    - category: billing | bug | feature_request | account_issue | general
    - priority: HIGH | MEDIUM | LOW
    
    Example: GET /tickets?priority=HIGH&category=billing
    """
    df = get_all_tickets(status=status)

    # Apply additional filters
    if category:
        df = df[df['category'] == category]
    if priority:
        df = df[df['priority'] == priority]

    return {
        "total": len(df),
        "tickets": df.to_dict('records')
    }


# ── Get Single Ticket ─────────────────────────────────────────────────
@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str):
    """Get a single ticket by ID.
    
    Example: GET /tickets/TKT-1000
    """
    ticket = get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    return ticket


# ── Update Ticket Status ──────────────────────────────────────────────
@app.patch("/tickets/{ticket_id}/status")
def update_status(ticket_id: str, body: StatusUpdate):
    """Update ticket status.
    
    Valid flow: new -> in_review -> assigned -> resolved
    
    Example: PATCH /tickets/TKT-1000/status
    Body: {"status": "in_review"}
    """
    # Check ticket exists first
    ticket = get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")

    success = update_ticket_status(ticket_id, body.status)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{body.status}'. Must be: new, in_review, assigned, resolved"
        )

    return {
        "ticket_id": ticket_id,
        "status": body.status,
        "message": f"Status updated to {body.status}"
    }


# ── Stats ─────────────────────────────────────────────────────────────
@app.get("/stats")
def ticket_stats():
    """Get aggregated ticket statistics.
    
    Returns counts by category, priority, and status.
    Used by Streamlit dashboard.
    """
    return get_stats()


# ── High Priority Tickets ─────────────────────────────────────────────
@app.get("/tickets/priority/high")
def high_priority_tickets():
    """Get all HIGH priority tickets that are still open (not resolved).
    
    Useful for support team to see urgent tickets quickly.
    """
    df = get_all_tickets()
    high = df[(df['priority'] == 'HIGH') & (df['status'] != 'resolved')]
    return {
        "total": len(high),
        "tickets": high.to_dict('records')
    }