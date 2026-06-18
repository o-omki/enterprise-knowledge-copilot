import os
import random
import subprocess
import sys

from locust import HttpUser, between, task

# List of realistic RAG questions to rotate during the load test
QUESTIONS = [
    "What is middleware in FastAPI?",
    "How do I declare path parameters in FastAPI?",
    "What validation error does FastAPI return when a path parameter has the wrong type?",
    "How are FastAPI path parameters documented automatically?",
    "How does FastAPI's dependency injection system work?",
    "How do I set up global dependencies in FastAPI?",
    "What is the execution order when multiple middlewares are added?",
    "How do I declare the type of a path parameter in FastAPI?",
]


class RAGUser(HttpUser):
    """Simulates a client interacting with the Enterprise Knowledge Copilot API."""

    wait_time = between(1.0, 3.0)

    def on_start(self):
        # Retrieve the API key from environment variables or fallback to dev default
        self.api_key = os.getenv("DEFAULT_API_KEY", "ekc_dev_key_12345")
        self.headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        self.session_id = None

    @task(1)
    def health_check(self):
        """Task simulating standard health check probes."""
        self.client.get("/health")

    @task(3)
    def search_query(self):
        """Task simulating a search lookup without text generation."""
        query = random.choice(QUESTIONS)
        payload = {"query": query, "limit": 3, "rerank": True, "method": "hybrid"}
        self.client.post("/api/v1/search", json=payload, headers=self.headers)

    @task(6)
    def ask_query(self):
        """Task simulating a full RAG ask invocation."""
        query = random.choice(QUESTIONS)
        payload = {"query": query, "limit": 3, "rerank": True, "method": "hybrid"}

        # Reuse existing chat session to simulate a realistic conversational flow
        if self.session_id:
            payload["session_id"] = self.session_id

        with self.client.post(
            "/api/v1/ask", json=payload, headers=self.headers, catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "session_id" in data:
                        self.session_id = data["session_id"]
                    response.success()
                except Exception as e:
                    response.failure(f"Failed to parse JSON response: {e}")
            else:
                response.failure(f"HTTP {response.status_code}: {response.text}")


def main():
    """Runs Locust headlessly for a fixed duration and generates reports."""
    print("==================================================")
    print("Starting Headless Locust Load Test...")
    print("==================================================")

    # Set paths for reports
    report_dir = "data/eval/reports"
    os.makedirs(report_dir, exist_ok=True)

    html_report = os.path.join(report_dir, "load_test_report.html")
    csv_prefix = os.path.join(report_dir, "load_test")

    # Command parameters: 5 concurrent users, spawn rate of 1 user/sec, run for 30 seconds
    users = os.getenv("LOAD_TEST_USERS", "5")
    spawn_rate = os.getenv("LOAD_TEST_SPAWN_RATE", "1")
    run_time = os.getenv("LOAD_TEST_DURATION", "30s")
    host = os.getenv("API_HOST_URL", "http://localhost:8000")

    # Locate the locust binary (dynamically check virtualenv bin directory first)
    locust_bin = "locust"
    py_dir = os.path.dirname(sys.executable)
    local_locust = os.path.join(py_dir, "locust")
    if os.path.exists(local_locust):
        locust_bin = local_locust

    cmd = [
        locust_bin,
        "-f",
        __file__,
        "--headless",
        "-u",
        users,
        "-r",
        spawn_rate,
        "-t",
        run_time,
        "--html",
        html_report,
        "--csv",
        csv_prefix,
        "--host",
        host,
    ]

    print(f"Executing: {' '.join(cmd)}")
    try:
        # Run Locust CLI as a subprocess
        result = subprocess.run(cmd, check=True)
        print("\n==================================================")
        print("Load Test Completed Successfully!")
        print(f"HTML Dashboard: {html_report}")
        print(f"CSV Summary:    {csv_prefix}_stats.csv")
        print("==================================================")
        sys.exit(result.returncode)
    except subprocess.CalledProcessError as e:
        print(f"\nLocust execution failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
