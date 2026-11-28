"""Run the independent expanded evidence diagnostic's deterministic fixtures."""
import subprocess
import sys
from pathlib import Path


def main():
    script=Path(__file__).resolve().parents[2]/".github"/"scripts"/"native_detector_expanded_diagnosis.py"
    subprocess.run([sys.executable,str(script),"--self-test"],check=True)


if __name__=="__main__":
    main()
