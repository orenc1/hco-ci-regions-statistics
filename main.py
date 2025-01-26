import json
import os
import traceback

import requests as requests
from lxml import etree

PROW_BASE_URL = "https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com"
PROW_PRS_LIST = PROW_BASE_URL + "/gcs/test-platform-results/pr-logs/pull/kubevirt_hyperconverged-cluster-operator/"

platforms = [
    "gcp",
    "aws",
    "azure",
]

prow_jobs = []
pr_list = []

class ProwJob:
    build_id: str
    job_name : str
    job_url : str
    branch: str
    platform: str
    region: str
    timestamp: str
    result: str

    def __init__(self, build_id, job_name, job_url, platform, region, timestamp, result):
        self.build_id = build_id
        self.job_name = job_name
        self.job_url = job_url
        self.platform = platform
        self.region = region
        self.timestamp = timestamp
        self.result = result


def get_prs():
    html_response = requests.get(PROW_PRS_LIST).text
    tree = etree.HTML(html_response)
    all_elements = reversed(list(tree.iter()))
    for el in all_elements:
        if el.tag == 'a':
            pr_number = str(el.attrib).split('/')[-2]
            if pr_number.isdigit():
                pr_list.append(pr_number)


def get_prow_jobs():
    for pr in pr_list:
        html_response = requests.get(PROW_PRS_LIST + pr + "/").text
        tree = etree.HTML(html_response)
        all_elements = reversed(list(tree.iter()))
        for el in all_elements:
            if el.tag == 'a':
                lane_url = el.attrib['href']
                if any([p in lane_url for p in platforms]):
                    get_jobs_from_lane(lane_url)


def get_jobs_from_lane(lane_url):
    executions = []
    html_response = requests.get(PROW_BASE_URL + lane_url).text
    tree = etree.HTML(html_response)
    all_elements = reversed(list(tree.iter()))
    for el in all_elements:
        if el.tag == 'a' and el.attrib['href'].split('/')[-2].isdigit() and len(el.attrib['href'].split('/')[-2]) > 4:
            executions.append(PROW_BASE_URL + el.attrib['href'])


    for execution in executions:
        pj = get_pj_data(execution)
        if pj:
            prow_jobs.append(pj)


def get_pj_data(execution):
    prowjob_response = requests.get(execution + "prowjob.json").text
    prowjob = json.loads(prowjob_response)
    if "completionTime" not in prowjob["status"]:
        return None
    result = prowjob["status"]["state"]
    timestamp = prowjob["status"]["completionTime"]
    job_url = prowjob["status"]["url"] if "url" in prowjob["status"] else "N/A"
    job_fullname = prowjob["metadata"]["annotations"]["prow.k8s.io/job"]
    job_name = prowjob["metadata"]["labels"]["prow.k8s.io/context"]
    build_id = prowjob["status"]["build_id"]
    region, platform = get_job_region_and_platform(execution, job_name)
    if not region or not platform:
        return None

    pj = ProwJob(
        build_id=build_id,
        job_name=job_fullname,
        job_url=job_url,
        platform=platform,
        region=region,
        timestamp=timestamp,
        result=result,
    )

    print (f"{len(prow_jobs)}: ProwJob {job_name} from {pj.timestamp} ran at {pj.region } is {pj.result}")
    return pj

def get_job_region_and_platform(execution, job_name):
    nodes_json_response = requests.get(execution + "artifacts/" + job_name + "/gather-extra/artifacts/nodes.json").text
    try:
        nodes_json = json.loads(nodes_json_response)
    except Exception:
        return None, None
    if len(nodes_json["items"]) == 0:
        print(f"{execution} does not have any nodes. skipping")
        return None, None
    if "metadata" not in nodes_json["items"][0]:
        return None, None
    if "labels" not in nodes_json["items"][0]["metadata"]:
        return None, None
    if "topology.kubernetes.io/region" not in nodes_json["items"][0]["metadata"]["labels"]:
        return None, None
    region = nodes_json["items"][0]["metadata"]["labels"]["topology.kubernetes.io/region"]
    platform = nodes_json["items"][0]["spec"]["providerID"].split(':')[0]
    if platform == "gce":
        platform = "gcp"
    return region, platform


def analyze_data():
    jobs_results = {}
    for pj in prow_jobs:
        if pj.platform not in jobs_results:
            jobs_results[pj.platform] = {}
        if pj.region not in jobs_results[pj.platform]:
            jobs_results[pj.platform][pj.region] = {}

        if pj.result not in jobs_results[pj.platform][pj.region]:
            jobs_results[pj.platform][pj.region][pj.result] = 1
        else:
            jobs_results[pj.platform][pj.region][pj.result] += 1

    return jobs_results


def job_exists(job_id, test_name, test_jobs):
    for job in test_jobs[test_name]:
        if job["job_id"] == job_id.replace('/', '') and job["result"] != "pending":
            return True
    return False


def create_dirs_if_not_exists(dirs):
    for dir in dirs:
        if not os.path.exists(dir):
            os.makedirs(dir)


def save_results(job_results, job_results_file):
    with open(job_results_file, "w") as fh:
        json.dump(job_results, fh, indent=4)


def calculate_pass_rate_per_region(input_json_file, output_json_file):
    with open(input_json_file, 'r') as fh:
        json_contents = fh.read()
        jobs_results = json.loads(json_contents)

    if not jobs_results:
        return

    for pname, platform in jobs_results.items():
        for rname, region in platform.items():
            pass_rate = round(region["success"] / (region["success"] + region["failure"]) * 100, 2)
            jobs_results[pname][rname]["pass_rate"] = pass_rate

    print (jobs_results)
    save_results(jobs_results, output_json_file)


def main():
    get_prs()
    get_prow_jobs()
    job_results = {}
    try:
        job_results = analyze_data()
    except Exception as ex:
        print(f"Exception occurred: {ex}")
        traceback.print_exc()
    save_results(job_results, "results.json")
    calculate_pass_rate_per_region("results.json", "results_with_percent.json")
    print ("done")


if __name__ == '__main__':
    main()

