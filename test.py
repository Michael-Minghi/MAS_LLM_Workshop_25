from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
import logfire
import os
load_dotenv(override=True)

if __name__ == "__main__":
    
    try:
        logfire.configure(token=os.getenv("LOGFIRE_TOKEN"))
        logfire.instrument_openai()
        print ("Logfire configured successfully.")
    except Exception as e:
        print (f"Failed to configure Logfire: {e}")
    
    try:
        model = OpenAIResponsesModel(
            'gpt-4o',
            provider=OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY"))
        )  

        agent = Agent(
            model=model,
            output_type=str,
        )

        print (agent.run_sync('Tell me about Digital building technology in ETH Zurich.').output)
    except Exception as e:
        print (f"Failed to initialize OpenAI model: {e}")