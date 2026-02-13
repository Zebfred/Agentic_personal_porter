import os
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

print("Attempting to connect to Groq API to list available models...")

try:
    # Initialize the Groq client. It will automatically use the GROQ_API_KEY
    # from your .env file.
    client = Groq()

    # Fetch the list of models
    models_response = client.models.list()
    
    # The actual list of model objects is in the 'data' attribute
    model_list = models_response.data
    
    if model_list:
        print("\nSuccessfully retrieved available models:")
        
        # Prepare a list of model IDs
        model_ids = [model.id for model in model_list]
        
        # Print models to the console
        for model_id in model_ids:
            print(f"- {model_id}")
            
        # Write the list to a text file for easy reference
        with open("available_models.txt", "w") as f:
            f.write("Available Groq Models:\n")
            for model_id in model_ids:
                f.write(f"- {model_id}\n")
        
        print("\nList of models has been saved to 'available_models.txt'")
    else:
        print("API call successful, but no models were returned.")

except Exception as e:
    print(f"\nAn error occurred: {e}")
    print("Please check the following:")
    print("1. Your GROQ_API_KEY in the .env file is correct.")
    print("2. You have an active internet connection.")
    print("3. There are no service outages at Groq.")
