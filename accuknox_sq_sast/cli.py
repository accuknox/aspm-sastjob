import argparse
import asyncio
import os
from accuknox_sq_sast.sonarqube_fetcher import SonarQubeFetcher

from colorama import Fore, init
init(autoreset=True)

def parse_args():
    parser = argparse.ArgumentParser(description="Fetch issues and hotspots from SonarQube")
    parser.add_argument("--url", default=os.getenv("SQ_URL"), help="SonarQube server URL (or set SQ_URL)")
    parser.add_argument("--token", default=os.getenv("SQ_AUTH_TOKEN"), help="SonarQube authentication token (or set SQ_AUTH_TOKEN)")
    parser.add_argument("--projects", default=os.getenv("SQ_PROJECTS", ".*"), help="Regex for matching project keys (or set SQ_PROJECTS)")
    parser.add_argument("--org", default=os.getenv("SQ_ORG", ""), help="SonarQube organization key (or set SQ_ORG)")
    parser.add_argument("--report-path", default="", help="Directory to save results, default=current path")
    return parser.parse_args()

def main():
    args = parse_args()

    if not args.url or not args.token:
        print("Error: SQ_URL and SQ_AUTH_TOKEN must be provided either as arguments or environment variables.")
        return

    fetcher = SonarQubeFetcher(
        sq_url=args.url,
        auth_token=args.token,
        sq_projects=args.projects,
        sq_org=args.org,
        report_path=args.report_path
    )
    result = asyncio.run(fetcher.fetch_all())

if __name__ == "__main__":
    main()