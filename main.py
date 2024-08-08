import requests
from datetime import datetime
from prometheus_client import start_http_server, Gauge, Counter
import time
import logging
from dotenv import load_dotenv
from statistics import mean
import os
import tempfile

# Load environment variables from .env file
load_dotenv()

# Configuration for logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# GitHub repository details
OWNER = os.getenv('GITHUB_OWNER')
REPO = os.getenv('GITHUB_REPO')
TOKEN = os.getenv('GITHUB_TOKEN')

# Headers for GitHub API authentication
HEADERS = {'Authorization': f'token {TOKEN}'}

# Prometheus metrics
DEPLOYMENT_GAUGE = Gauge(
    'github_deployments_total',
    'Total number of GitHub deployments',
    ['branch', 'repo', 'status']
)

LEAD_TIME_GAUGE = Gauge(
    'github_deployments_lead_time',
    'Lead time for changes in seconds',
    ['branch', 'repo']
)

MTTR_GAUGE = Gauge(
    'github_deployments_mttr',
    'Mean Time to Recovery (MTTR) in seconds',
    ['branch', 'repo']
)

def fetch_data_in_chunks(url, params=None):
    """
    Fetch data from GitHub API in chunks to handle large datasets.
    """
    while url:
        try:
            response = requests.get(url, headers=HEADERS, params=params)
            response.raise_for_status()
            yield response.json()
            url = response.links.get('next', {}).get('url')
        except requests.RequestException as e:
            logger.error(f'Error fetching data: {e}')
            break

def fetch_commits():
    """
    Fetch commits in chunks.
    """
    logger.info('Fetching commits from GitHub repository')
    url = f'https://api.github.com/repos/{OWNER}/{REPO}/commits'
    params = {'per_page': 100}

    for data in fetch_data_in_chunks(url, params):
        yield from data

def fetch_workflow_runs():
    """
    Fetch workflow runs in chunks.
    """
    logger.info('Fetching workflow runs from GitHub repository')
    url = f'https://api.github.com/repos/{OWNER}/{REPO}/actions/runs'
    params = {'status': 'completed', 'per_page': 100, 'event': 'push'}

    for data in fetch_data_in_chunks(url, params):
        yield from data['workflow_runs']

def calculate_deployment_counter(deployments):
    """
    Increment the deployment counter based on the deployment status.
    """
    logger.info('Calculating deployment counters')

    deployment_stats = {
        'dev': {'success': 0, 'failure': 0},
        'staging': {'success': 0, 'failure': 0},
        'prod': {'success': 0, 'failure': 0}
    }

    for deployment in deployments:
        if deployment['path'] in ['.github/workflows/dev.yml', '.github/workflows/staging.yml', '.github/workflows/prod.yml']:
            branch = deployment['head_branch']
            status = deployment['conclusion']

            if branch in deployment_stats and status in deployment_stats[branch]:
                deployment_stats[branch][status] += 1
                logger.debug(f'Incremented deployment counter for {branch}, status: {status}')

    for branch, statuses in deployment_stats.items():
        for status, count in statuses.items():
            DEPLOYMENT_GAUGE.labels(branch=branch, repo=REPO, status=status).set(count)

    logger.info('Deployment counters updated successfully')

def calculate_lead_time_for_changes(commits, deployments):
    """
    Calculate lead time for changes for different branches and update the gauge.
    """
    logger.info('Calculating lead time for changes')
    branch_lead_times = {'dev': [], 'staging': [], 'prod': []}

    branch_paths = {
        '.github/workflows/dev.yml': 'dev',
        '.github/workflows/staging.yml': 'staging',
        '.github/workflows/prod.yml': 'prod'
    }

    for commit in commits:
        commit_sha = commit['sha']
        commit_time = datetime.strptime(commit['commit']['author']['date'], '%Y-%m-%dT%H:%M:%SZ')

        for deployment in deployments:
            deployment_sha = deployment['head_sha']
            deployment_path = deployment['path']
            deployment_conclusion = deployment['conclusion']

            if deployment_conclusion == 'success' and deployment_path in branch_paths:
                if commit_sha == deployment_sha:
                    deployment_time = datetime.strptime(deployment['updated_at'], '%Y-%m-%dT%H:%M:%SZ')
                    lead_time = (deployment_time - commit_time).total_seconds()

                    branch = branch_paths[deployment_path]
                    branch_lead_times[branch].append(lead_time)
                    logger.debug(f'Calculated lead time for commit {commit_sha} on branch {branch}: {lead_time} seconds')
                    break

    for branch, times in branch_lead_times.items():
        if times:
            average_lead_time = mean(times)
            LEAD_TIME_GAUGE.labels(branch=branch, repo=REPO).set(average_lead_time)
            logger.info(f'Updated lead time gauge for branch {branch}, average lead time: {average_lead_time} seconds')
        else:
            LEAD_TIME_GAUGE.labels(branch=branch, repo=REPO).set(0)
            logger.info(f'No lead times recorded for branch {branch}, set to 0 seconds')

def calculate_mttr(runs):
    """
    Calculate Mean Time to Recovery (MTTR) for different branches and update the gauge.
    """
    logger.info('Calculating MTTR')
    branch_recovery_times = {'dev': [], 'staging': [], 'prod': []}

    for run in runs:
        if run['conclusion'] == 'success':
            branch = run['head_branch']
            valid_branches = {'dev', 'staging', 'prod'}
            if branch not in valid_branches:
                continue

            previous_failures = [r for r in runs if r['updated_at'] < run['updated_at'] and r['conclusion'] == 'failure' and r['head_branch'] == branch]

            if previous_failures:
                last_failure = max(previous_failures, key=lambda r: r['updated_at'])
                recovery_time = (datetime.strptime(run['updated_at'], '%Y-%m-%dT%H:%M:%SZ') - datetime.strptime(last_failure['updated_at'], '%Y-%m-%dT%H:%M:%SZ')).total_seconds()
                branch_recovery_times[branch].append(recovery_time)
                logger.debug(f'Calculated MTTR for branch {branch}: {recovery_time} seconds')

    for branch, times in branch_recovery_times.items():
        if times:
            average_mttr = sum(times) / len(times)
            MTTR_GAUGE.labels(branch=branch, repo=REPO).set(average_mttr)
            logger.info(f'Updated MTTR gauge for branch {branch}, average MTTR: {average_mttr} seconds')
        else:
            MTTR_GAUGE.labels(branch=branch, repo=REPO).set(0)
            logger.info(f'No recovery times recorded for branch {branch}, set to 0 seconds')

def update_metrics():
    """
    Fetch data and update Prometheus metrics.
    """
    deployments = list(fetch_workflow_runs())
    commits = list(fetch_commits())

    calculate_deployment_counter(deployments)
    calculate_lead_time_for_changes(commits, deployments)
    calculate_mttr(deployments)

# Main execution
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5555))
    start_http_server(port)
    logger.info("Prometheus metrics server started on port {port}")

    while True:
        try:
            update_metrics()
            logger.info('Metrics updated successfully')
        except Exception as e:
            logger.error(f'Error updating metrics: {e}')

        time.sleep(600)
