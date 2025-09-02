import os
import subprocess
import time
import yaml
import requests
import json
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv
from pathlib import Path
import sys
import io
import random

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# --- Load .env from grandparent directory ---
grandparent_dir = Path(__file__).resolve().parent.parent.parent
dotenv_path = grandparent_dir / ".env"
load_dotenv(dotenv_path=dotenv_path)

# --- Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set.")

CONFIG_PATH = "tests/evals/config.yaml"
FLASK_APP_URL = "http://localhost:5000"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"
REPORT_FILE = "evaluation_report.html"

# Rate limiting configuration
GEMINI_RATE_LIMIT = 15  # requests per minute
GEMINI_LAST_REQUEST = 0
GEMINI_REQUEST_INTERVAL = 60 / GEMINI_RATE_LIMIT  # seconds between requests

def run_command(command, cwd=None, suppress_output=False):
    """Runs a shell command and optionally prints its output."""
    if not suppress_output:
        print(f"🚀 Running command: {' '.join(command)}")
    
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=cwd
    )

    if not suppress_output:
        for line in process.stdout: # type: ignore
            print(line, end='')
    else:
        # Just consume the output without printing
        process.communicate()

    if process.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {process.returncode}")

def start_services():
    """Starts Docker services quietly."""
    run_command(["docker-compose", "up", "--build", "-d"], suppress_output=True)
    print("🔧 Starting services...")
    time.sleep(15)

def stop_services():
    """Stops Docker services quietly."""
    # run_command(["docker-compose", "down", "-v"], suppress_output=True)
    pass

def cleanup_database(phone_number=None):
    """Calls the Flask cleanup endpoint."""
    try:
        if phone_number:
            url = f"{FLASK_APP_URL}/testing/cleanup?phone_number={phone_number}"
        else:
            url = f"{FLASK_APP_URL}/testing/cleanup"
            
        response = requests.delete(url, timeout=10)
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"❌ Cleanup failed: {e}")
        return False

def call_gemini_with_retry(prompt, max_retries=3, base_delay=1.0):
    """
    Calls the Gemini API with retry logic and rate limiting.
    
    Args:
        prompt: The prompt to send
        max_retries: Maximum number of retry attempts
        base_delay: Base delay for exponential backoff (seconds)
    """
    global GEMINI_LAST_REQUEST
    
    for attempt in range(max_retries + 1):
        try:
            # Rate limiting: ensure we don't exceed the rate limit
            current_time = time.time()
            time_since_last_request = current_time - GEMINI_LAST_REQUEST
            
            if time_since_last_request < GEMINI_REQUEST_INTERVAL:
                sleep_time = GEMINI_REQUEST_INTERVAL - time_since_last_request
                print(f"⏱️  Rate limiting: waiting {sleep_time:.1f}s...")
                time.sleep(sleep_time)
            
            GEMINI_LAST_REQUEST = time.time()
            
            # Make the API call
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "response_mime_type": "application/json",
                }
            }
            
            response = requests.post(GEMINI_API_URL, json=payload, timeout=30)
            
            # Check for rate limit error specifically
            if response.status_code == 429:
                if attempt < max_retries:
                    # Exponential backoff with jitter
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    print(f"🔄 Rate limited (attempt {attempt + 1}/{max_retries + 1}), retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    continue
                else:
                    print(f"❌ Rate limited after {max_retries + 1} attempts, giving up")
                    raise requests.exceptions.HTTPError("Rate limit exceeded after all retries")
            
            # Check for other HTTP errors
            response.raise_for_status()
            
            # Parse response
            response_text = response.json()['candidates'][0]['content']['parts'][0]['text']
            return json.loads(response_text)
            
        except requests.exceptions.HTTPError as e:
            if attempt < max_retries and "429" in str(e):
                # This is a retry-able error
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                print(f"🔄 HTTP error (attempt {attempt + 1}/{max_retries + 1}), retrying in {delay:.1f}s...")
                time.sleep(delay)
                continue
            else:
                # Non-retryable error or max retries exceeded
                raise
        except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError) as e:
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                print(f"🔄 Request error (attempt {attempt + 1}/{max_retries + 1}): {e}")
                print(f"    Retrying in {delay:.1f}s...")
                time.sleep(delay)
                continue
            else:
                print(f"❌ Failed after {max_retries + 1} attempts: {e}")
                # Return a fallback response
                return {
                    "next_user_message": "I'm having trouble continuing this conversation.",
                    "rating": 5,
                    "reasoning": "Unable to evaluate due to API error"
                }

def call_gemini(prompt):
    """Wrapper for backwards compatibility."""
    return call_gemini_with_retry(prompt)

def run_conversation_turn(config, conversation_history, last_agent_response):
    """Runs a single turn of the conversation using Gemini."""
    persona = config['persona']
    intent = config['intent']
    
    history_str = "\n".join([f"You: {t['user_message']}\nAgent: {t['agent_response']}" for t in conversation_history])
    
    prompt = f"""
    You are an AI user testing a chatbot. Your name is {persona['name']} and your persona is: "{persona['description']}".
    Your overall goal is: "{intent['goal']}".

    ## Conversation History
    {history_str}

    ## Chatbot's Last Message
    "{last_agent_response}"

    ## Your Task
    Based on the chatbot's last message, your persona, and your goal, provide your next message.
    Also, rate the chatbot's last response on a scale of 1-10 for helpfulness and quality, and provide a brief reason.

    Output ONLY the following JSON object:
    {{
        "next_user_message": "Your next message to the chatbot.",
        "rating": <an integer from 1 to 10>,
        "reasoning": "A brief explanation for your rating."
    }}
    """
    return call_gemini(prompt)

def send_message_to_app(phone_number, message, timeout=15):
    """
    Sends a message to the Flask app and waits for the actual AI response.
    """
    payload = {
        'From': phone_number,
        'Body': message
    }
    
    try:
        # Clear any previous responses for this phone number
        clear_previous_responses(phone_number)
        
        # Send the webhook message
        response = requests.post(f"{FLASK_APP_URL}/message", data=payload, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ HTTP {response.status_code} error from /message endpoint")
            response.raise_for_status()
        
        # Get the immediate response (usually "thinking...")
        try:
            immediate_response = response.text.split('<Message>')[1].split('</Message>')[0].strip()
            print(f"📱 Immediate: {immediate_response}")
        except IndexError:
            immediate_response = "[Could not parse immediate response]"
        
        # Wait for the actual AI response
        ai_response = wait_for_ai_response(phone_number, timeout)
        
        return ai_response if ai_response else immediate_response
            
    except requests.exceptions.RequestException as e:
        return f"[Error: {str(e)}]"

def wait_for_ai_response(phone_number, timeout=15):
    """Wait for the AI response to be processed and stored."""
    import time
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        # Check if response is available
        try:
            response = requests.get(f"{FLASK_APP_URL}/testing/get-response/{phone_number}")
            if response.status_code == 200:
                data = response.json()
                if data.get('has_response'):
                    print(f"✅ Got AI response: {data.get('response')[:100]}...")
                    return data.get('response')
        except:
            pass
        
        time.sleep(0.5)  # Poll every 500ms
    
    print(f"⏰ Timeout waiting for AI response from {phone_number}")
    return None

def clear_previous_responses(phone_number):
    """Clear any stored responses before sending new message."""
    try:
        requests.delete(f"{FLASK_APP_URL}/testing/clear-responses/{phone_number}")
    except:
        pass

def generate_report(all_test_results):
    """Generates the final HTML report for all tests."""
    print("📊 Generating comprehensive report...")
    
    template_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Flight Agent Evaluation Report</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 2em; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1, h2, h3 { color: #333; }
        .summary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2em; border-radius: 12px; margin-bottom: 2em; }
        .test-card { background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 2em; overflow: hidden; }
        .test-header { background: #f8f9fa; padding: 1.5em; border-bottom: 1px solid #dee2e6; }
        .test-content { padding: 1.5em; }
        .convo { border-left: 4px solid #007bff; }
        .turn { padding: 1em; border-bottom: 1px solid #eee; }
        .turn:last-child { border-bottom: none; }
        .user { color: #0066cc; margin-bottom: 0.5em; }
        .agent { color: #28a745; margin-bottom: 0.5em; }
        .rating { background: #fff3cd; margin-top: 0.5em; padding: 1em; border-radius: 8px; border-left: 4px solid #ffc107; }
        .rating strong { color: #856404; }
        .score-good { color: #28a745; font-weight: bold; }
        .score-fair { color: #ffc107; font-weight: bold; }
        .score-poor { color: #dc3545; font-weight: bold; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1em; margin: 1em 0; }
        .stat-card { background: white; padding: 1em; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-number { font-size: 2em; font-weight: bold; color: #007bff; }
    </style>
</head>
<body>
    <div class="container">
        <div class="summary">
            <h1>🛫 Flight Agent Evaluation Report</h1>
            <p><strong>Generated:</strong> {{ timestamp }}</p>
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number">{{ total_tests }}</div>
                    <div style="color: black;">Total Tests</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ "%.1f"|format(overall_avg_score) }}</div>
                    <div style="color: black;">Overall Average Score</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ total_turns }}</div>
                    <div style="color: black;">Total Conversation Turns</div>
                </div>
            </div>
        </div>
        
        {% for test in tests %}
        <div class="test-card">
            <div class="test-header">
                <h2>{{ test.test_name }}</h2>
                <p><strong>Persona:</strong> {{ test.persona_name }} - {{ test.persona_description }}</p>
                <p><strong>Goal:</strong> {{ test.goal }}</p>
                <p><strong>Average Score:</strong> 
                    <span class="{% if test.avg_score >= 7 %}score-good{% elif test.avg_score >= 5 %}score-fair{% else %}score-poor{% endif %}">
                        {{ "%.1f"|format(test.avg_score) }}/10
                    </span>
                </p>
            </div>
            <div class="test-content">
                <div class="convo">
                    {% for turn in test.conversation %}
                    <div class="turn">
                        <p class="user"><strong>{{ test.persona_name }}:</strong> {{ turn.user_message }}</p>
                        <p class="agent"><strong>Flight Agent:</strong> {{ turn.agent_response }}</p>
                        <div class="rating">
                            <p><strong>Quality Score:</strong> {{ turn.rating }} / 10</p>
                            <p><strong>Reasoning:</strong> {{ turn.reasoning }}</p>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
</body>
</html>"""
    
    env = Environment(loader=FileSystemLoader('.'))
    template = env.from_string(template_content)
    
    # Calculate overall stats
    total_tests = len(all_test_results)
    total_turns = sum(len(test['conversation']) for test in all_test_results)
    overall_avg_score = sum(test['avg_score'] for test in all_test_results) / total_tests if total_tests > 0 else 0
    
    html_content = template.render(
        tests=all_test_results,
        total_tests=total_tests,
        total_turns=total_turns,
        overall_avg_score=overall_avg_score,
        timestamp=time.strftime('%Y-%m-%d %H:%M:%S')
    )

    with open(REPORT_FILE, "w", encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Report saved to {os.path.abspath(REPORT_FILE)}")

def run_single_test(test_config):
    """Runs a single test scenario and returns the results."""
    conversation_log = []
    user_message = test_config['intent']['initial_message']
    
    # Clear any previous responses for this phone number
    clear_previous_responses(test_config['phone_number'])
    
    for i in range(test_config['max_turns']):
        agent_response = send_message_to_app(test_config['phone_number'], user_message)
        
        # If we got an error response, break early
        if agent_response.startswith("[Error:") or agent_response.startswith("[Timeout:"):
            conversation_log.append({
                "user_message": user_message,
                "agent_response": agent_response,
                "rating": 1,
                "reasoning": "System error or timeout occurred"
            })
            break

        eval_result = run_conversation_turn(test_config, conversation_log, agent_response)
        
        current_turn = {
            "user_message": user_message,
            "agent_response": agent_response,
            "rating": eval_result.get('rating', 1), # type: ignore
            "reasoning": eval_result.get('reasoning', 'No reasoning provided') # type: ignore
        }
        conversation_log.append(current_turn)

        user_message = eval_result.get('next_user_message') # type: ignore
        if not user_message:
            break

    # Calculate test results and return them
    total_score = sum(turn['rating'] for turn in conversation_log if 'rating' in turn)
    avg_score = total_score / len(conversation_log) if conversation_log else 0
    
    return {
        "test_name": test_config['test_name'],
        "persona_name": test_config['persona']['name'],
        "persona_description": test_config['persona']['description'],
        "goal": test_config['intent']['goal'],
        "conversation": conversation_log,
        "avg_score": avg_score,
        "total_turns": len(conversation_log)
    }

def main():
    """Main evaluation script orchestrator."""
    all_test_results = []
    
    try:
        # 1. Setup
        start_services()
        
        if not cleanup_database():
            print("❌ Database cleanup failed, continuing anyway...")

        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)

        # Handle both single test and multiple tests
        test_configs = config if isinstance(config, list) else [config]
        
        print(f"🧪 Running {len(test_configs)} test scenario(s)...")
        print(f"⚡ Rate limit: {GEMINI_RATE_LIMIT} requests/minute to Gemini API\n")
        
        # 2. Run each test
        for i, test_config in enumerate(test_configs, 1):
            print(f"[{i}/{len(test_configs)}] Running: {test_config['test_name']}")
            
            # Clean up between tests
            cleanup_database(test_config['phone_number'])
            
            test_result = run_single_test(test_config)
            all_test_results.append(test_result)
            
            score_emoji = "🟢" if test_result['avg_score'] >= 7 else "🟡" if test_result['avg_score'] >= 5 else "🔴"
            print(f"    {score_emoji} Completed - Average Score: {test_result['avg_score']:.1f}/10\n")

        # 3. Generate comprehensive report
        generate_report(all_test_results)
        
        print(f"\n🎉 All tests completed! Check {REPORT_FILE} for detailed results.")

    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 4. Teardown
        print("\n🧹 Cleaning up...")
        stop_services()

if __name__ == "__main__":
    main()