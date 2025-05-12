import argparse
import asyncio

from accuknox_sq_sast.sonarqube_fetcher import SonarQubeFetcher

def parse_args():
    parser = argparse.ArgumentParser(description="Fetch issues and hotspots from SonarQube")
    parser.add_argument("--url", required=True, help="SonarQube server URL")
    parser.add_argument("--token", required=True, help="SonarQube authentication token")
    parser.add_argument("--projects", default=".*", help="Regex for matching project keys")
    parser.add_argument("--org", default="", help="SonarQube organization key")
    parser.add_argument("--report-path", default="", help="Directory to save results")
    return parser.parse_args()

def main():
    args = parse_args()
    fetcher = SonarQubeFetcher(
        sq_url=args.url,
        auth_token=args.token,
        sq_projects=args.projects,
        sq_org=args.org,
        report_path=args.report_path
    )
    result = asyncio.run(fetcher.fetch_all())
    print(result)

if __name__ == "__main__":
    main()
