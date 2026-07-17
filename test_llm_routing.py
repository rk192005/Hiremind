import os
from app.pipeline.llm_client import generate_text, is_demo_mode

def test_routing():
    print("Testing routing...")
    
    # Clear keys for testing
    if "ANTHROPIC_API_KEY" in os.environ: del os.environ["ANTHROPIC_API_KEY"]
    if "GROQ_API_KEY" in os.environ: del os.environ["GROQ_API_KEY"]
    if "GEMINI_API_KEY" in os.environ: del os.environ["GEMINI_API_KEY"]
    if "DEMO_MODE" in os.environ: del os.environ["DEMO_MODE"]
    
    print(f"Is demo mode (No keys): {is_demo_mode()}")
    assert is_demo_mode() == True
    
    # 1. Test Anthropic precedence
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"
    os.environ["GROQ_API_KEY"] = "gsk_test"
    os.environ["GEMINI_API_KEY"] = "AIza_test"
    print(f"Is demo mode (All keys): {is_demo_mode()}")
    assert is_demo_mode() == False
    
    try:
        generate_text("System", "User")
    except Exception as e:
        print(f"Anthropic error (expected invalid key): {type(e).__name__}")
        assert "anthropic" in str(e).lower() or "authentication" in str(e).lower() or type(e).__name__ == 'AuthenticationError'

    # 2. Test Groq precedence
    del os.environ["ANTHROPIC_API_KEY"]
    try:
        generate_text("System", "User")
    except Exception as e:
        print(f"Groq error (expected invalid key): {type(e).__name__}")
        assert "groq" in str(e).lower() or "authentication" in str(e).lower() or type(e).__name__ == 'AuthenticationError'

    # 3. Test Gemini precedence
    del os.environ["GROQ_API_KEY"]
    try:
        generate_text("System", "User")
    except Exception as e:
        print(f"Gemini error (expected invalid key): {type(e).__name__}")
        assert "api_key" in str(e).lower() or "defaultcredentials" in str(e).lower() or type(e).__name__ == 'InvalidArgument' or 'API key not valid' in str(e)

    print("All routing tests passed successfully!")

if __name__ == "__main__":
    test_routing()
