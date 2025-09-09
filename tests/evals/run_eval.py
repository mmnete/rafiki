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

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)


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

# Ultra-conservative rate limiting for Gemini free tier
GEMINI_RATE_LIMIT = 10  # 10 requests per minute
GEMINI_LAST_REQUEST = 0
GEMINI_REQUEST_INTERVAL = 60 / GEMINI_RATE_LIMIT  # 6 seconds between requests
MAX_RETRIES = 8
BASE_DELAY = 1.0

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
        process.communicate()

    if process.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {process.returncode}")

def start_services():
    """Starts Docker services with immediate feedback."""
    print("🔧 Starting Docker services...")
    print("   - Building and starting containers...")
    run_command(["docker-compose", "up", "--build", "-d"], suppress_output=True)
    print("   - Waiting for services to initialize...")
    for i in range(60):
        print(f"   - Services starting... ({i+1}/60 seconds)")
        time.sleep(1)
    print("✅ Docker services should be ready!")

def stop_services():
    """Stops Docker services with comprehensive cleanup."""
    # If you uncomment you wont be able to see logs in docker.
    # print("🛑 Shutting down Docker services...")
    # try:
    #     # Stop and remove containers, networks, and volumes
    #     print("   - Stopping and removing containers...")
    #     run_command(["docker-compose", "down", "-v", "--remove-orphans"], suppress_output=True)
    #     print("✅ Docker services stopped and cleaned up!")
    # except Exception as e:
    #     print(f"⚠️  Warning: Error stopping services: {e}")
    #     try:
    #         # Fallback: try basic stop
    #         print("   - Attempting basic shutdown...")
    #         run_command(["docker-compose", "stop"], suppress_output=True)
    #         print("✅ Services stopped (cleanup may be incomplete)")
    #     except Exception as e2:
    #         print(f"❌ Failed to stop services: {e2}")
    #         print("   Manual intervention required: docker-compose down")
    pass

def cleanup_database(phone_number=None):
    """Calls the Flask cleanup endpoint."""
    try:
        if phone_number:
            url = f"{FLASK_APP_URL}/testing/cleanup?phone_number={phone_number}"
            print(f"🧹 Cleaning up data for {phone_number}...")
        else:
            url = f"{FLASK_APP_URL}/testing/cleanup"
            print("🧹 Cleaning up all test data...")
            
        response = requests.delete(url, timeout=10)
        response.raise_for_status()
        print("✅ Cleanup successful")
        return True
    except requests.RequestException as e:
        print(f"❌ Cleanup failed: {e}")
        return False

def call_gemini_with_retry(prompt, max_retries=MAX_RETRIES, base_delay=BASE_DELAY):
    """Ultra-conservative Gemini API calls with extensive retry logic."""
    global GEMINI_LAST_REQUEST
    
    for attempt in range(max_retries + 1):
        try:
            # Rate limiting with immediate feedback
            current_time = time.time()
            time_since_last_request = current_time - GEMINI_LAST_REQUEST
            
            min_wait_time = GEMINI_REQUEST_INTERVAL + 2  # 2 second buffer
            if time_since_last_request < min_wait_time:
                sleep_time = min_wait_time - time_since_last_request
                print(f"⏱️  Rate limiting: waiting {sleep_time:.1f}s...")
                # Show countdown for long waits
                if sleep_time > 3:
                    for remaining in range(int(sleep_time), 0, -1):
                        print(f"   - {remaining}s remaining...", end='\r')
                        time.sleep(1)
                    print()  # New line after countdown
                else:
                    time.sleep(sleep_time)
            
            jitter = random.uniform(1, 3)
            time.sleep(jitter)
            GEMINI_LAST_REQUEST = time.time()
            
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "response_mime_type": "application/json",
                    "temperature": 0.7,
                    "topP": 0.8,
                    "topK": 40
                }
            }
            
            print(f"🤖 Calling Gemini API (attempt {attempt + 1}/{max_retries + 1})...")
            response = requests.post(GEMINI_API_URL, json=payload, timeout=60)
            
            print(f"📊 Response status: {response.status_code}")
            
            if response.status_code == 429:
                if attempt < max_retries:
                    delay = base_delay * (4 ** attempt) + random.uniform(10, 30)
                    print(f"🔄 Rate limited! Waiting {delay:.1f}s...")
                    # Show countdown for long delays
                    for remaining in range(int(delay), 0, -1):
                        if remaining % 5 == 0 or remaining <= 5:
                            print(f"   - {remaining}s remaining...")
                        time.sleep(1)
                    continue
                else:
                    return create_fallback_response("Rate limit exceeded")
            
            if response.status_code == 403:
                print(f"❌ Quota exceeded or API key issue")
                return create_fallback_response("API quota exceeded")
            
            response.raise_for_status()
            response_data = response.json()
            
            if 'candidates' not in response_data or not response_data['candidates']:
                if attempt < max_retries:
                    print("⚠️ No candidates, retrying...")
                    time.sleep(base_delay)
                    continue
                return create_fallback_response("No response candidates")
                
            candidate = response_data['candidates'][0]
            if 'content' not in candidate or 'parts' not in candidate['content']:
                if attempt < max_retries:
                    print("⚠️ Invalid response structure, retrying...")
                    time.sleep(base_delay)
                    continue
                return create_fallback_response("Invalid response structure")
            
            response_text = candidate['content']['parts'][0]['text'].strip()
            
            # Clean up markdown formatting
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            try:
                parsed_response = json.loads(response_text)
                print(f"✅ Gemini API call successful")
                return parsed_response
            except json.JSONDecodeError:
                if attempt < max_retries:
                    print("⚠️ JSON parsing failed, retrying...")
                    time.sleep(base_delay)
                    continue
                return create_fallback_response("JSON parsing failed")
            
        except Exception as e:
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt) + random.uniform(2, 5)
                print(f"🔄 Error (attempt {attempt + 1}): {e}")
                print(f"   - Retrying in {delay:.1f}s...")
                time.sleep(delay)
                continue
            else:
                return create_fallback_response(f"Error: {e}")
    
    return create_fallback_response("Maximum retries exceeded")

def create_fallback_response(reason):
    """Create a fallback response when API calls fail."""
    return {
        "next_user_message": "I need to end this conversation due to technical issues.",
        "rating": 2,
        "reasoning": f"Could not evaluate due to API issues: {reason}"
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
    print("🧠 Generating evaluation response...")
    return call_gemini(prompt)

def send_message_to_app(phone_number, message, timeout=30):
    """Sends a message to the Flask app and waits for the actual AI response."""
    print(f"📨 Sending message: '{message[:50]}...' to {phone_number}")
    
    payload = {
        'From': phone_number,
        'Body': message
    }
    
    try:
        clear_previous_responses(phone_number)
        response = requests.post(f"{FLASK_APP_URL}/message", data=payload, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ HTTP {response.status_code} error from /message endpoint")
            response.raise_for_status()
        
        try:
            immediate_response = response.text.split('<Message>')[1].split('</Message>')[0].strip()
            print(f"📱 Immediate response: {immediate_response}")
            
            # Check if it's just a thinking message
            thinking_indicators = ['thinking', 'processing', 'let me', 'please wait', 'analyzing', 'looking into']
            is_thinking = any(indicator in immediate_response.lower() for indicator in thinking_indicators)
            
            if is_thinking:
                print("🤔 Detected thinking message, waiting for actual AI response...")
            else:
                print("💬 Got substantial immediate response")
                
        except IndexError:
            immediate_response = "[Could not parse immediate response]"
            is_thinking = True
        
        # Always wait for the AI response, but wait longer if it's a thinking message
        wait_time = 45 if is_thinking else timeout
        print(f"⏳ Waiting up to {wait_time}s for AI response...")
        
        ai_response = wait_for_ai_response(phone_number, wait_time)
        
        if ai_response:
            return ai_response
        elif not is_thinking:
            # If we got a substantial immediate response and no AI response, use immediate
            return immediate_response
        else:
            return "[Timeout: No substantial response received]"
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return f"[Error: {str(e)}]"

def wait_for_ai_response(phone_number, timeout=30):
    """Wait for the AI response with progress indicators."""
    start_time = time.time()
    last_check_time = 0
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{FLASK_APP_URL}/testing/get-response/{phone_number}")
            if response.status_code == 200:
                data = response.json()
                if data.get('has_response'):
                    response_text = data.get('response')
                    print(f"✅ Got AI response: {response_text[:100]}...")
                    return response_text
        except:
            pass
        
        # Show progress every 5 seconds
        current_time = time.time()
        if current_time - last_check_time >= 5:
            elapsed = int(current_time - start_time)
            remaining = int(timeout - elapsed)
            print(f"⏳ Still waiting for AI response... ({elapsed}s elapsed, {remaining}s remaining)")
            last_check_time = current_time
        
        time.sleep(0.5)
    
    print(f"⏰ Timeout after {timeout}s waiting for AI response")
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
    print(f"\n🎭 Starting test: {test_config['test_name']}")
    print(f"👤 Persona: {test_config['persona']['name']}")
    print(f"🎯 Goal: {test_config['intent']['goal']}")
    
    conversation_log = []
    user_message = test_config['intent']['initial_message']
    
    clear_previous_responses(test_config['phone_number'])
    
    for i in range(test_config['max_turns']):
        print(f"\n--- Turn {i+1}/{test_config['max_turns']} ---")
        
        agent_response = send_message_to_app(test_config['phone_number'], user_message)
        
        if agent_response.startswith("[Error:") or agent_response.startswith("[Timeout:"):
            print(f"❌ Error detected: {agent_response}")
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
            "rating": eval_result.get('rating', 1),
            "reasoning": eval_result.get('reasoning', 'No reasoning provided')
        }
        conversation_log.append(current_turn)
        
        print(f"📊 Rating: {eval_result.get('rating', 1)}/10")
        print(f"💭 Reasoning: {eval_result.get('reasoning', 'No reasoning')}")

        user_message = eval_result.get('next_user_message')
        if not user_message or user_message.strip().lower() in ['', 'none', 'end']:
            print("🛑 Conversation ended by evaluator")
            break

    total_score = sum(turn['rating'] for turn in conversation_log if 'rating' in turn)
    avg_score = total_score / len(conversation_log) if conversation_log else 0
    
    print(f"📋 Test completed: {len(conversation_log)} turns, average score: {avg_score:.1f}/10")
    
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
    print("🚀 Flight Agent Evaluation System Starting...")
    print("=" * 50)
    
    all_test_results = []
    
    try:
        start_services()
        
        print("\n🧹 Initial database cleanup...")
        if not cleanup_database():
            print("❌ Database cleanup failed, continuing anyway...")

        print(f"\n📋 Loading test configuration from {CONFIG_PATH}...")
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)

        test_configs = config if isinstance(config, list) else [config]
        print(f"✅ Loaded {len(test_configs)} test scenario(s)")
        
        # Show configuration
        estimated_turns = sum(tc.get('max_turns', 10) for tc in test_configs)
        estimated_time_minutes = (estimated_turns * (GEMINI_REQUEST_INTERVAL + 10)) / 60
        
        print(f"\n⚙️  Configuration:")
        print(f"   - Rate limit: {GEMINI_RATE_LIMIT} requests/minute")
        print(f"   - Max retries: {MAX_RETRIES}")
        print(f"   - Estimated turns: {estimated_turns}")
        print(f"   - Estimated time: {estimated_time_minutes:.0f} minutes")
        print(f"\n🧪 Running evaluation suite...")
        print("=" * 50)
        
        for i, test_config in enumerate(test_configs, 1):
            print(f"\n[TEST {i}/{len(test_configs)}]")
            
            cleanup_database(test_config['phone_number'])
            
            test_result = run_single_test(test_config)
            all_test_results.append(test_result)
            
            score_emoji = "🟢" if test_result['avg_score'] >= 7 else "🟡" if test_result['avg_score'] >= 5 else "🔴"
            print(f"\n{score_emoji} Test completed - Average Score: {test_result['avg_score']:.1f}/10")
            
            if i < len(test_configs):
                print(f"⏸️  Taking 10s break before next test...")
                for remaining in range(10, 0, -1):
                    print(f"   - {remaining}s remaining...", end='\r')
                    time.sleep(1)
                print()

        print("\n" + "=" * 50)
        generate_report(all_test_results)
        print(f"\n🎉 All tests completed! Check {REPORT_FILE} for detailed results.")
        
        # Show summary
        overall_avg = sum(t['avg_score'] for t in all_test_results) / len(all_test_results)
        print(f"📊 Final Summary:")
        print(f"   - Tests run: {len(all_test_results)}")
        print(f"   - Total turns: {sum(len(t['conversation']) for t in all_test_results)}")
        print(f"   - Overall average: {overall_avg:.1f}/10")

    except KeyboardInterrupt:
        print("\n⏹️  Evaluation interrupted by user")
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🧹 Cleaning up...")
        stop_services()
        print("👋 Evaluation system shutdown complete")

if __name__ == "__main__":
    main()
    