from fastapi import APIRouter, HTTPException
from datasets import load_dataset
import pandas as pd
from typing import List, Dict, Any

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

@router.get("/cuad/samples")
async def get_cuad_samples(limit: int = 5):
    """
    Fetch sample contracts from the CUAD dataset.
    Used for benchmarking and demo purposes.
    """
    try:
        # Load a small portion of the dataset
        ds = load_dataset("theatticusproject/cuad", split="train", streaming=True, verification_mode="no_checks")
        
        samples = []
        count = 0
        for item in ds:
            if count >= limit:
                break
            
            pdf = item.get("pdf")
            if not pdf:
                continue
                
            # Extract text from first few pages for preview
            text = ""
            for i, page in enumerate(pdf.pages):
                if i > 2: break # Only first 3 pages for preview
                text += page.extract_text() or ""
            
            if not text.strip():
                continue

            samples.append({
                "id": str(count),
                "title": f"CUAD Sample {count + 1}",
                "content": text[:2000] + "...", 
                "full_content": text,
                "source": "theatticusproject/cuad"
            })
            count += 1
            
        return samples
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cuad/contract/{contract_id}")
async def get_cuad_contract(contract_id: str):
    """Fetch a specific contract from CUAD by ID."""
    try:
        ds = load_dataset("theatticusproject/cuad", split="train")
        df = pd.DataFrame(ds)
        contract = df[df["id"] == contract_id]
        
        if contract.empty:
            raise HTTPException(status_code=404, detail="Contract not found")
            
        row = contract.iloc[0]
        return {
            "id": row["id"],
            "title": f"CUAD Contract {row['id']}",
            "content": row["context"],
            "source": "theatticusproject/cuad"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
