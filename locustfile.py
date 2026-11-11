import random
import string
from locust import FastHttpUser, task, between

def get_random_ip():
    return f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"

class URLShortenerUser(FastHttpUser):
    wait_time = between(0.1, 0.5)

    def on_start(self):
        self.created_short_codes = []
        self.create_url()

    @task(1)
    def create_url(self):
        # Inject fake IP
        headers = {"X-Forwarded-For": get_random_ip()}
        response = self.client.post(
            "/api/v1/urls",
            json={"url": "https://fastapi.tiangolo.com/"},
            headers=headers,
            name="Create URL"
        )
        if response.status_code == 201:
            self.created_short_codes.append(response.json()["short_code"])

    @task(8)
    def redirect_url(self):
        if not self.created_short_codes:
            return
            
        short_code = random.choice(self.created_short_codes)
        headers = {"X-Forwarded-For": get_random_ip()}
        
        with self.client.get(f"/{short_code}", headers=headers, allow_redirects=False, catch_response=True, name="Valid Redirect") as response:
            if response.status_code == 307:
                response.success()
            else:
                response.failure(f"Expected 307, got {response.status_code}")

    @task(1)
    def malicious_cache_penetration(self):
        fake_code = "".join(random.choices(string.ascii_letters + string.digits, k=8))
        headers = {"X-Forwarded-For": get_random_ip()}
        
        with self.client.get(f"/{fake_code}", headers=headers, allow_redirects=False, catch_response=True, name="Bloom Filter Block (Fake URL)") as response:
            if response.status_code == 404:
                response.success()
            else:
                response.failure(f"Expected 404, got {response.status_code}") 