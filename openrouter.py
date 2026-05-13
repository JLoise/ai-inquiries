import os
from dotenv import load_dotenv
import openai

load_dotenv()

# Example OpenRouter client using the OPENROUTER_API_KEY environment variable.
# Change the model string below to use a different OpenRouter-compatible model.
client = openai.OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

# Stream the response to get reasoning tokens in usage
stream = client.chat.completions.create(
    model="google/gemma-3-27b-it:free",
    messages=[
        {
            "role": "user",
            "content": "How many r's are in the word 'strawberry'?"
        }
    ],
    stream=True
)

response = ""
for chunk in stream:
    content = chunk.choices[0].delta.content
    if content:
        response += content
        print(content, end="")

    # Usage information comes in the final chunk
    if chunk.usage:
        if hasattr(chunk.usage, 'completion_tokens_details') and chunk.usage.completion_tokens_details and hasattr(chunk.usage.completion_tokens_details, 'reasoning_tokens'):
            print(f"\nReasoning tokens: {chunk.usage.completion_tokens_details.reasoning_tokens}")
        else:
            print(f"\nUsage: {chunk.usage}")