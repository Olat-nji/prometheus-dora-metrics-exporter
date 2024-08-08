
# Prometheus DORA Metrics Exporter 

This project configures and exposes DORA metrics for a GitHub repository using Prometheus. The metrics include Deployment Frequency, Lead Time for Changes, Change Failure Rate, and Mean Time to Recovery (MTTR).

## Prerequisites

- Python 3.x
- A GitHub repository
- A GitHub token with appropriate permissions
- Prometheus

## Setup

### Clone the Repository

Clone the repository to your local machine:

```bash
git clone https://github.com/olat-nji/prometheus-dora-metrics.git
cd dora-metrics
```

### Install Dependencies

Install the required Python dependencies:

```bash
pip install -r requirements.txt
```

### Configuration

1. **Create a `.env` File**

   Create a `.env` file in the project root with the following content:

    ```plaintext
    GITHUB_TOKEN=your_github_token
    GITHUB_OWNER=github_username_or_organization
    GITHUB_REPO=your_github_repo
    PORT=your_desired_port
    ```


### Script Details

The script fetches commits and workflow runs from a specified GitHub repository and exposes metrics useful for calculating various DORA metrics. Here’s a breakdown:

1. **Deployment Frequency**:
   - **Definition**: Measures how often deployments occur over a specific time period.
   - **Calculation**: 
   
      **Deployment Frequency** = Σ (Total Number of Deployments) / Number of Days

   - **Script Detail**: Counts the total number of successful and failed deployments and divides by the number of days in the analysis period.

2. **Lead Time for Changes**:
   - **Definition**: The average time it takes from when a commit is made to when it is deployed.
   - **Calculation**: 

     **Average Lead Time for Changes** = (Sum of Lead Times) / (Number of Lead Times)

     where Lead is the time difference between the commit time and deployment time.
   - **Script Detail**: Calculates lead time for each commit with a corresponding deployment and computes the average lead time.

3. **Change Failure Rate**:
   - **Definition**: The percentage of deployments that fail compared to the total number of deployments.
   - **Calculation**: 

     **Change Failure Rate** = (Number of Failed Deployments / Total Number of Deployments) × 100

   - **Script Detail**: Counts the number of failed deployments, divides by the total number of deployments, and multiplies by 100 to get the percentage.

4. **Mean Time to Recovery (MTTR)**:
   - **Definition**: The average time taken to recover from a failed deployment.
   - **Calculation**: 

     **MTTR** = Σ (Recovery Times) / Number of Recovery Times

     where \(\text{Recovery Time}\) is the duration between a failure being resolved and the next successful deployment.
   - **Script Detail**: Calculates recovery times for each successful deployment following a failure and computes the average.

### Running the Script

To start the Prometheus metrics server and update the metrics periodically, run:

```bash
python main.py
```

The server will start on port 5555 (or the specified port) and update the metrics every 10 minutes.

### Prometheus Configuration

Add the following job to your Prometheus configuration file (`prometheus.yml`):

```yaml
scrape_configs:
  - job_name: 'dora-metrics'
    static_configs:
      - targets: ['localhost:5555']
```

### `main.py` Script

The `main.py` script is responsible for fetching data from GitHub, calculating metrics, and exposing them via a Prometheus server. [View the script](main.py).

### Conclusion

This README provides step-by-step instructions to set up and configure DORA metrics for a GitHub repository, including fetching data from GitHub, calculating metrics, and exposing them via a Prometheus server. Ensure you replace placeholder values with your actual data and credentials.
```
