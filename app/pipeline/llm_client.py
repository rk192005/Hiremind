import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def generate_text(system_prompt: str, user_prompt: str, response_format: str = "text") -> str:
    """
    Unified LLM call routing to Anthropic -> Groq -> Gemini -> Demo Heuristics.
    response_format can be "text" or "json_object".
    """
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()

    # 1. Anthropic (Claude)
    if anthropic_key:
        import anthropic
        client = anthropic.Anthropic(api_key=anthropic_key)
        
        # Anthropic doesn't have a strict JSON mode flag in the same way, but it follows system prompts well
        # If response_format == "json_object", we just ensure the prompt demands JSON
        try:
            logger.info("Routing LLM call to Anthropic (claude-sonnet-4-20250514)")
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return message.content[0].text
        except Exception as e:
            logger.error(f"Anthropic call failed: {e}")
            raise e

    # 2. Groq
    if groq_key:
        from groq import Groq
        client = Groq(api_key=groq_key)
        
        try:
            logger.info("Routing LLM call to Groq (llama3-70b-8192)")
            kwargs = {}
            if response_format == "json_object":
                kwargs["response_format"] = {"type": "json_object"}
                
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="llama3-70b-8192",
                temperature=0.0,
                max_tokens=2048,
                **kwargs
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq call failed: {e}")
            raise e

    # 3. Google Gemini
    if gemini_key:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        
        try:
            logger.info("Routing LLM call to Gemini (gemini-1.5-flash)")
            model_kwargs = {}
            if response_format == "json_object":
                # Gemini JSON mode
                model_kwargs["generation_config"] = {"response_mime_type": "application/json"}
                
            # Gemini system instruction
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=system_prompt,
                **model_kwargs
            )
            
            response = model.generate_content(user_prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini call failed: {e}")
            raise e

    # 4. No keys present
    raise ValueError("No LLM keys configured (ANTHROPIC_API_KEY, GROQ_API_KEY, or GEMINI_API_KEY). Ensure demo mode checks wrap this.")

def is_demo_mode() -> bool:
    """Returns True if no LLM keys are configured."""
    return not (
        os.getenv("ANTHROPIC_API_KEY", "").strip() or
        os.getenv("GROQ_API_KEY", "").strip() or
        os.getenv("GEMINI_API_KEY", "").strip()
    )
