import asyncio
import re
import aiohttp
from tqdm import tqdm
import json
import urllib.parse
import os
import traceback
import logging

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class SonarQubeFetcher:
    def __init__(self, sq_url, auth_token, sq_projects=".*", sq_org="", report_path=""):
        self.sq_url = sq_url.rstrip('/')
        self.auth_token = auth_token
        self.sq_projects = sq_projects
        self.sq_org = sq_org
        self.report_path = report_path
        self.pbar = None

    async def _async_sq_api(self, session, api, params):
        if self.pbar is None:
            self.pbar = tqdm(desc="API Calls")
        self.pbar.update(1)

        auth = aiohttp.BasicAuth(self.auth_token, '')
        async with session.get(api, params=params, auth=auth) as response:
            if response.status == 401:
                log.error("SonarQube authentication error")
                return None
            if response.status != 200:
                log.error(f"SonarQube API error: {response.status}")
                return None
            data = await response.json()
            if "errors" in data:
                log.error(f"SonarQube API error: {data['errors'][0]['msg']}")
                return None
            return data

    async def _get_issues_batch(self, session, api, params):
        data = await self._async_sq_api(session, api, params)
        return data.get("issues", []) if data else []

    async def _get_hotspots_batch(self, session, api, params):
        data = await self._async_sq_api(session, api, params)
        return data.get("hotspots", []) if data else []

    async def _get_issue_details(self, session, issue, is_hotspot=False):
        if is_hotspot:
            params = {"hotspot": issue["key"]}
            api = f"{self.sq_url}/api/hotspots/show"
        else:
            params = {"key": issue["rule"]}
            if self.sq_org:
                params["organization"] = self.sq_org
            api = f"{self.sq_url}/api/rules/show"

        max_retries = 3
        for attempt in range(max_retries):
            try:
                data = await self._async_sq_api(session, api, params)
                if is_hotspot and "rule" in data:
                    rule = data["rule"]
                    issue.update({
                        "name": rule.get("name", "None"),
                        "riskDescription": rule.get("riskDescription", "None"),
                        "vulnerabilityDescription": rule.get("vulnerabilityDescription", "None"),
                        "fixRecommendations": rule.get("fixRecommendations", "None"),
                        "comments": data.get("comment", [])
                    })
                elif not is_hotspot and "rule" in data:
                    desc = data["rule"].get("htmlDesc") or data["rule"].get("descriptionSections", "No Description Available.")
                    issue["description"] = desc
                break
            except Exception:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(5)

        return issue

    async def _get_snippet(self, session, issue):
        if "line" not in issue and "textRange" not in issue:
            return issue

        api = f"{self.sq_url}/api/sources/issue_snippets"
        params = {"issueKey": issue["key"]}
        try:
            data = await self._async_sq_api(session, api, params)
            component_data = data.get(issue.get("component"), {})
            fullSnippet = []
            for source in component_data.get("sources", []):
                try:
                    line = source.get("line")
                    code = source.get("code")
                    if line and code:
                        space_count = len(code) - len(code.lstrip())
                        fullSnippet.append({"line": line, "code": " " * space_count + code})
                except Exception:
                    log.error(traceback.format_exc())
            if fullSnippet:
                issue["snippet"] = fullSnippet
        except Exception:
            log.error(traceback.format_exc())
        return issue

    async def _process_issues(self, session, issues, is_hotspots=False):
        detail_tasks = [self._get_issue_details(session, i, is_hotspots) for i in issues]
        details_results = await asyncio.gather(*detail_tasks)
        snippet_tasks = [self._get_snippet(session, i) for i in details_results]
        return await asyncio.gather(*snippet_tasks)

    async def _get_results_async(self, key, branch=None):
        async with aiohttp.ClientSession() as session:
            api = f"{self.sq_url}/api/issues/search"
            params = {"componentKeys": key, "ps": 500, "p": 1, "additionalFields": "comments", "resolved": "false"}
            if branch:
                params["branch"] = branch

            try:
                initial_response = await self._async_sq_api(session, api, params)
                all_issues = initial_response.get("issues", []) if initial_response else []
                total = initial_response.get("total", 0)

                if total > 500:
                    pages = min((total - 1) // 500, 19)
                    tasks = [self._get_issues_batch(session, api, {**params, "p": p}) for p in range(2, pages + 2)]
                    for r in await asyncio.gather(*tasks):
                        all_issues.extend(r)

                processed_issues = await self._process_issues(session, all_issues)

                # Hotspots
                hotspots_api = f"{self.sq_url}/api/hotspots/search"
                hotspot_params = {"projectKey": key, "ps": 500, "p": 1, "status": "TO_REVIEW"}
                if branch:
                    hotspot_params["branch"] = branch
                hotspots_response = await self._async_sq_api(session, hotspots_api, hotspot_params)
                if not hotspots_response:
                    return False, None, "Failed to fetch hotspots"

                all_hotspots = hotspots_response.get("hotspots", [])
                total_hotspots = hotspots_response.get("paging", {}).get("total", 0)

                if total_hotspots > 500:
                    pages = min((total_hotspots - 1) // 500, 19)
                    tasks = [self._get_hotspots_batch(session, hotspots_api, {**hotspot_params, "p": p}) for p in range(2, pages + 2)]
                    for r in await asyncio.gather(*tasks):
                        all_hotspots.extend(r)

                processed_hotspots = await self._process_issues(session, all_hotspots, is_hotspots=True)

                # Save results
                branch_suffix = f"-{branch.replace('/', '_')}" if branch else ""
                issues_file = os.path.join(self.report_path, f"SQ-{key}{branch_suffix}.json")
                with open(issues_file, "w") as f:
                    json.dump({"branch": branch, "issues": processed_issues, "hotspots": processed_hotspots}, f, indent=2)

                return True, issues_file, "Success."
            except Exception as e:
                log.error(f"Error fetching project {key}: {str(e)}")
                return False, None, str(e)

    async def process_project(self, key):
        branch_api = f"{self.sq_url}/api/project_branches/list"
        async with aiohttp.ClientSession() as session:
            try:
                response = await self._async_sq_api(session, branch_api, {"project": key})
                branches = [b["name"] for b in response.get("branches", [])]
                results = []
                for branch in branches:
                    result = await self._get_results_async(key, branch)
                    if result[0]:
                        results.append(result[1])
                    else:
                        raise Exception(result[2])
                return results
            except Exception as e:
                log.error(f"Error processing project {key}: {str(e)}")
                raise

    async def fetch_all(self):
        components_api = f"{self.sq_url}/api/components/search"
        params = {"qualifiers": "TRK", "ps": 500, "p": 1}
        if self.sq_org:
            params["organization"] = self.sq_org

        async with aiohttp.ClientSession() as session:
            try:
                response = await self._async_sq_api(session, components_api, params)
                total = response.get("paging", {}).get("total", 0)
                components = response.get("components", [])

                keys = [c["key"] for c in components if re.search(self.sq_projects, c["key"])]

                for p in range(2, (total // 500) + 2):
                    params["p"] = p
                    response = await self._async_sq_api(session, components_api, params)
                    for c in response.get("components", []):
                        if re.search(self.sq_projects, c["key"]):
                            keys.append(c["key"])

                if not keys:
                    return "No matching projects found."

                tasks = [asyncio.create_task(self.process_project(k)) for k in keys]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                all_files = []
                for res in results:
                    if isinstance(res, list):
                        all_files.extend(res)
                    else:
                        log.error(f"Project processing failed: {res}")
                        return f"Project processing failed: {res}"
                return f"Success! Data saved to {all_files}"
            except Exception as e:
                return f"An error occurred: {str(e)}"