from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from workers.prepare import prepare_handler
from workers.submit import submit_share_handler, SubmitShareRequest
from workers.submit_proof import submit_proof_handler, SubmitProofRequest
from workers.reconstruct import reconstruct_handler, ReconstructRequest

app = FastAPI(title="KeyReconstruction Server")

@app.post("/prepare")
async def prepare_endpoint(threshold: int):
    return await prepare_handler(threshold)

@app.post("/submit-share")
async def submit_share_endpoint(data: SubmitShareRequest):
    return await submit_share_handler(data)

@app.post("/submit-proof")
async def submit_proof_endpoint(data: SubmitProofRequest):
    return await submit_proof_handler(data)

@app.post("/reconstruct")
async def reconstruct_endpoint(request: ReconstructRequest):
    return await reconstruct_handler(request)

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
