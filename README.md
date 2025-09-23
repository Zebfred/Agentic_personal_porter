# Agentic Personal Porter

## Introduction & Vision

Welcome, Hero. Your journey is uniquely yours, and every step, planned or unplanned, holds value. The Agentic Personal Porter is your non-judgmental companion on this adventure. It's not here to critique your detours but to help you find the treasures hidden within them.

Our primary goal is to compassionately bridge the gap between your stated intentions and your actual actions. This isn't just another productivity tracker; it's a tool for profound self-discovery. The Porter helps you understand the "why" behind your choices, find meaning in what you do, and align your life with your own definition of a fulfilling existence.

By leveraging holistic frameworks like Maslow's Hierarchy of Needs and custom metrics such as "Brain Fog," we aim to capture a more complete, nuanced picture of your state, helping you navigate your path with greater clarity and self-awareness.

## Core Features (Current MVP)

*   **Weekly Time Logging:** A user-friendly interface for logging your intentions and actual activities across a 7-day week. The week is broken down into six manageable time chunks per day, making logging quick and intuitive.
*   **AI-Powered Reflection:** A sophisticated multi-agent AI system analyzes each log entry and provides an empathetic, insightful reflection. This feedback is designed to be supportive and illuminating, never critical.
*   **Graph-Based Memory:** Every log entry and its corresponding reflection are saved as a network of interconnected nodes in a Neo4j graph database. Over time, this creates a rich, personal knowledge graph, allowing you to see patterns and growth in your journey.

## Tech Stack

*   **Front-End:** HTML5, Tailwind CSS, Vanilla JavaScript
*   **Back-End API:** Python, Flask
*   **AI Engine:** CrewAI framework with models accessed via the Groq API
*   **Database:** Neo4j Graph Database

## Architecture Overview

The system is designed with a clear separation of concerns, allowing for scalability and maintainability.

*   **Client (Front-End):** The `index.html` and `app.js` files work together to create the dynamic weekly planner UI. This client-side application captures all user input and sends it to the Flask server as a single JSON payload.
*   **Server (Back-End):** `server.py` acts as the central hub. It exposes an API endpoint that receives requests from the front-end, orchestrates the CrewAI workflow to process the data, and then passes the complete log data to the Neo4j connector for storage.
*   **AI Core (`main.py`):** This is where the magic happens. The CrewAI workflow coordinates three specialized agents to process the user's log:
    *   **Goal and Activity Analyst:** Parses the raw, often messy, user input into a structured and clean format.
    *   **Empathetic Self-Reflection Coach:** Takes the structured data and generates the nuanced, user-facing reflection with a supportive tone.
    *   **Personal Growth Librarian:** Summarizes key learnings and insights from the log, preparing them for future "inventory" features.
*   **Database (`neo4j_db.py`):** This module serves as the Neo4j connector. It takes the final, processed log data and writes it to the graph database, creating and connecting nodes like `User`, `Day`, `TimeChunk`, `Actual`, and `Reflection`.

## Setup & Installation

Follow these steps to get the Agentic Personal Porter running on your local machine.

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/your-username/Agentic_personal_porter.git
    cd Agentic_personal_porter
    ```

2.  **Set Up the Conda Environment**
    This project uses Python 3.11. Create and activate a dedicated Conda environment to manage dependencies.
    ```bash
    conda create --name agentic_porter python=3.11
    conda activate agentic_porter
    ```

3.  **Install Python Dependencies**
    Install all the required Python packages from the `requirements.txt` file.
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**
    Create a `.env` file by copying the example file. Then, fill in your credentials.
    ```bash
    cp .env.example .env
    ```
    Open the `.env` file and add your credentials for the following services:
    ```
    GROQ_API_KEY="your_groq_api_key"
    NEO4J_URI="your_neo4j_bolt_uri"
    NEO4J_USERNAME="your_neo4j_username"
    NEO4J_PASSWORD="your_neo4j_password"
    ```

5.  **Run the Application**
    The application requires two separate processes to run: the back-end server and the front-end client.

    *   **Terminal 1: Start the Back-End Server**
        Run the Flask server. It will listen for requests from the front-end.
        ```bash
        python server.py
        ```

    *   **Terminal 2 (or VS Code): Serve the Front-End**
        The simplest way to serve the front-end is by using the **Live Server** extension in Visual Studio Code. Right-click the `index.html` file and select "Open with Live Server".

## Future Roadmap

We have an exciting vision for the future of the Agentic Personal Porter. Here are some of the features we're planning to build:

*   **Hero's Inventory:** A comprehensive system to track your skills, knowledge, and other valuable "items" you collect on your journey.
*   **Questing System:** A dedicated AI agent will help you break down large, ambitious goals ("quests") into smaller, actionable sub-tasks.
*   **User Authentication & Onboarding:** A secure system for user accounts and a guided "Origin Story" setup to personalize the experience from the start.
*   **Google Calendar Integration:** Automate the logging of your *intentions* by seamlessly integrating with your Google Calendar.