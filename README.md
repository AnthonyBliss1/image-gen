# Image Generator
This project is an image generation tool that allows users to create or edit images using OpenAI's new API.

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/AnthonyBliss1/image-gen.git
    ```
2. Navigate to the project directory:
    ```bash
    cd image-gen
    ```
3. Create a virtual environment:
    ```bash
    python -m venv .venv
    ```
4. Activate the virtual environment:

    - On macOS/Linux:
        ```bash
        source .venv/bin/activate
        ```
    - On Windows:
        ```bash
        .venv\Scripts\activate
        ```

5. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage
1. Copy the .env template:
   ```bash
   cp .env.template .env
   ```
2. Add your OpenAI API key to the .env file
3. Run the application:
    ```bash
    python app.py
    ```
4. Enter a prompt to generate images.