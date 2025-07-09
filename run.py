import subprocess
from app import create_app

# Run safety sync before app starts
subprocess.run(["python", "scripts/safe_sync.py"])

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)

