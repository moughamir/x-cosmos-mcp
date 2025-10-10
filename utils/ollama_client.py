"""
Ollama API client for MCP
"""
import ollama

class OllamaClient:
    """A client for interacting with the Ollama API."""

    def __init__(self, model_name: str, host: str, port: int):
        """
        Initialize the OllamaClient.

        Args:
            model_name: The name of the Ollama model to use.
            host: The Ollama host.
            port: The Ollama port.
        """
        self.model_name = model_name
        self.client = ollama.Client(host=f"{host}:{port}")

    def get_response(self, prompt: str) -> str:
        """
        Get a response from the Ollama model.

        Args:
            prompt: The prompt to send to the model.

        Returns:
            The model's response.
        """
        try:
            response = self.client.generate(model=self.model_name, prompt=prompt)
            return response["response"]
        except Exception as e:
            print(f"Error calling Ollama: {e}")
            return ""