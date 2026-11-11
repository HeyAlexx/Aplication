"""Read the private scoped-release receipt; no Git command, provider or data collection."""
import argparse
import json
from pathlib import Path
from release_identity import status

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args();report=status(args.app.resolve());print(json.dumps(report,ensure_ascii=True))
    return 0 if report['status']=='VERIFIED_SCOPED_RELEASE' else 3 if report['status']=='UNRECORDED' else 1

if __name__=='__main__':raise SystemExit(main())
