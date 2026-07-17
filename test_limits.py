import urllib.request
import urllib.error
import json
import time
import subprocess
import threading
import sys

def start_server():
    print("Starting local server...")
    return subprocess.Popen(
        ["python", "-m", "uvicorn", "app.main:app", "--port", "8888"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def test_payload(num_resumes):
    url = "http://127.0.0.1:8888/rank"
    
    # Generate dummy resumes
    resumes = [f"Dummy candidate {i} - Python developer with {i} years of experience." for i in range(num_resumes)]
    
    payload = {
        "job_description": "We need a Python developer with 5+ years of experience.",
        "resumes": resumes
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    
    start_time = time.time()
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            elapsed = time.time() - start_time
            print(f"[{num_resumes} resumes] SUCCESS! Processed in {elapsed:.2f}s. Pipeline status: {data.get('pipeline_status')}")
            return True
    except urllib.error.HTTPError as e:
        print(f"[{num_resumes} resumes] FAILED! HTTP Error: {e.code} - {e.read().decode('utf-8')}")
        return False
    except Exception as e:
        print(f"[{num_resumes} resumes] FAILED! {e}")
        return False

if __name__ == "__main__":
    proc = start_server()
    time.sleep(3) # Wait for startup
    
    print("\n--- Running Tests ---")
    try:
        # Should succeed
        test_payload(2)
        test_payload(10)
        test_payload(20)
        
        # Should fail validation (1 resume)
        test_payload(1)
        
        # Should fail validation (21 resumes)
        test_payload(21)
    finally:
        print("\nShutting down server...")
        proc.terminate()
        proc.wait()
