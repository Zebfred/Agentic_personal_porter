import os
from google.cloud.aiplatform_v1beta1 import ModelGardenServiceClient
from google.api_core.exceptions import GoogleAPICallError

def list_vertex_models():
    """
    Queries the Vertex AI Model Garden to list foundational models published by Google 
    (like Gemini, Claude on Vertex, etc.) and outputs them to the console.
    """
    print("Authenticating via Application Default Credentials...")
    try:
        # Initialize the client
        client = ModelGardenServiceClient()
        
        # The parent is publishers/{publisher}
        parent = "publishers/google"
        
        print(f"Querying Vertex AI Model Garden for {parent}...\n")
        
        # We'll filter to just show the most relevant / popular ones to avoid terminal spam
        # Specifically highlighting Gemini, Llama, Claude, etc.
        count = 0
        
        request = {"parent": parent}
        
        # Call the API
        page_result = client.list_publisher_models(request=request)
        
        print("========================================================")
        print("    Available Google Vertex AI Foundational Models      ")
        print("========================================================\n")
        
        for model in page_result:
            name = model.name
            
            # Filter for generative/LLM models
            if any(keyword in name.lower() for keyword in ['gemini', 'llama', 'claude', 'text-', 'chat-']):
                display_name = getattr(model, 'display_name', 'Unknown')
                version_id = getattr(model, 'version_id', 'latest')
                
                # Get description safely
                description = getattr(model, 'description', '')
                if description:
                    description = description.split('\n')[0][:100] + "..."
                else:
                    description = "No description"
                
                print(f"Model ID: {name.split('/')[-1]}")
                print(f"Display Name: {display_name}")
                print(f"Description: {description}")
                print("-" * 40)
                count += 1
                
        print(f"\nFound {count} highly relevant generative models.")
        print("For a full list of every single variant, see the GCP Vertex AI Model Garden Console.")
        print("========================================================\n")

    except GoogleAPICallError as e:
        print(f"GCP API Error: {e.message}")
    except Exception as e:
        print(f"Error fetching models: {e}")

if __name__ == "__main__":
    list_vertex_models()
