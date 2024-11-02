import os
import agentql
from playwright.sync_api import sync_playwright
from pyairtable import Api
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get USERNAME and PASSWORD from environment variables
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
os.environ["AGENTQL_API_KEY"] = os.getenv("AGENTQL_API_KEY")

INITIAL_URL = "https://www.idealist.org/"


EMAIL_INPUT_QUERY = """
{
    login_form {
        email_input
        continue_btn
    }
}
"""


VERIFY_QUERY = """
{
    login_form {
        verify_not_robot_checkbox
    }
}
"""

PASSWORD_INPUT_QUERY = """
{
    login_form {
        password_input
        continue_btn
    }
}
"""


with sync_playwright() as playwright, playwright.chromium.launch(
    headless=False
) as browser:

    page = agentql.wrap(browser.new_page())

    page.goto(INITIAL_URL)

    # Use query_elements() method to locate "Log In" button on the page
    response = page.query_elements(EMAIL_INPUT_QUERY)
    response.login_form.email_input.fill(EMAIL)
    page.wait_for_timeout(1000)

    # Verify Human
    verify_response = page.query_elements(VERIFY_QUERY)
    verify_response.login_form.verify_not_robot_checkbox.click()
    page.wait_for_timeout(1000)

    # Continue Next Step
    response.login_form.continue_btn.click()

    # Input Password
    password_response = page.query_elements(PASSWORD_INPUT_QUERY)
    password_response.login_form.password_input.fill(PASSWORD)
    page.wait_for_timeout(1000)

    password_response.login_form.continue_btn.click()

    page.wait_for_page_ready_state()

    browser.contexts[0].storage_state(path="idealist_login.json")

URL = "https://www.idealist.org/jobs"

JOB_POSTS_QUERY = """
{
    job_posts[] {
        org_name
        job_title
        salary
        location
        contract_type(Contract or Full time)
        location_type(remote or on-site or hybrid)
        date_posted
    }
}
"""

PAGINATION_QUERY = """
{
    pagination {
        next_page_btn    
    }
}
"""

with sync_playwright() as playwright, playwright.chromium.launch(
    headless=False
) as browser:
    if not os.path.exists("idealist_login.json"):
        print("no login state found, logging in...")
        login()

    context = browser.new_context(storage_state="idealist_login.json")
    page = agentql.wrap(context.new_page())
    page.goto(URL)

    # Use query.data() method to fetch the data from the page
    status = True

    while status:
        current_url = page.url

    job_posts_response = page.query_elements(JOB_POSTS_QUERY)
    job_posts = job_posts_response.job_posts
    job_posts_data = job_posts.to_data()

    print(f"Total number of job posts: {len(job_posts_data)}")
    print(job_posts_data)
    push_to_airtable(job_posts_data)

    # Write job posts data to CSV
    paginations = page.query_elements(PAGINATION_QUERY)
    next_page_btn = paginations.pagination.next_page_btn

    next_page_btn.click()
    # Wait for page to settle
    page.wait_for_page_ready_state()

    if current_url == page.url:
        status = False


def push_to_airtable(job_posts_data):
    airtable = Api(AIRTABLE_API_KEY)
    table = airtable.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)

    # Push to airtable
    for job in job_posts_data:
        table.create(job)

    print(f"{len(job_posts_data)} records pushed to Airtable")


if __name__ == "__main__":
    main()
