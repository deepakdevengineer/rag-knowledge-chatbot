"""
NVIDIA LLM Service — Chat completions via NVIDIA's OpenAI-compatible API
"""
import logging
from openai import OpenAI
from app.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.client = OpenAI(
            base_url=settings.nvidia_base_url,
            api_key=settings.nvidia_api_key,
        )
        self.model = settings.nvidia_llm_model

    def _build_messages(self, prompt: str, system_prompt: str = None, history: list = None):
        """Build the messages list for the API call."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        return messages

    def generate(self, prompt: str, system_prompt: str = None, temperature: float = 0.2,
                 history: list = None) -> str:
        """Generate a complete response from the LLM."""
        try:
            messages = self._build_messages(prompt, system_prompt, history)
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=1024,
                stream=False,
            )
            return completion.choices[0].message.content or ""
        except Exception:
            logger.exception("LLM generate() failed")
            return "I encountered an error generating a response. Please try again."

    def generate_stream(self, prompt: str, system_prompt: str = None, temperature: float = 0.2,
                        history: list = None):
        """Generate a streaming response from the LLM."""
        try:
            messages = self._build_messages(prompt, system_prompt, history)
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=1024,
                stream=True,
            )

            for chunk in completion:
                if not getattr(chunk, "choices", None) or len(chunk.choices) == 0:
                    continue
                delta = chunk.choices[0].delta
                # Skip reasoning/thinking content — only stream final answer
                content = getattr(delta, "content", None)
                if content:
                    yield content

        except Exception:
            logger.exception("LLM generate_stream() failed")
            yield "\n\n⚠️ **Error:** Could not get a response from the AI model. Please check your API key and try again."

    def generate_title(self, first_message: str) -> str:
        """Generate a short chat title from the first message."""
        try:
            prompt = f'Generate a very short title (3-5 words max) for a conversation starting with: "{first_message[:200]}". Return ONLY the title text, no quotes, no punctuation at the end.'
            title = self.generate(prompt, temperature=0.3)
            if title.startswith("I encountered an error"):
                return first_message[:40]
            return title.strip().strip('"').strip("'").strip()[:60] or first_message[:40]
        except Exception:
            return first_message[:40]


# Singleton instance
llm_service = LLMService()
