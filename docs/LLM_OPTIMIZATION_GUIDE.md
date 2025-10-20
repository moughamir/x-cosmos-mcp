# LLM Optimization Guide: Training, Quantization, and Fine-tuning for Product Data

This guide outlines the process for enhancing your Large Language Models (LLMs) to generate higher-quality product titles and comprehensive product details, including safe HTML tags, using techniques like fine-tuning and quantization. This process is iterative and requires careful data preparation and evaluation.

**Goal:** Improve the relevance, accuracy, and formatting (including safe HTML) of generated product titles and descriptions.

## I. Understanding the Concepts

1.  **Fine-tuning:**
    *   **What it is:** Taking a pre-trained LLM (like those available on Ollama) and further training it on a smaller, domain-specific dataset. This adapts the model's knowledge and style to your particular use case (e.g., product descriptions).
    *   **Why it's useful:** Improves output quality for specific tasks, teaches the model desired formatting (like HTML), and aligns its tone with your brand.

2.  **Quantization:**
    *   **What it is:** Reducing the precision of the model's weights (e.g., from 32-bit floating-point to 4-bit integers). This makes the model smaller and faster.
    *   **Why it's useful:** Significantly reduces memory footprint and speeds up inference, crucial for local deployments (like Ollama) and real-time applications.
    *   **Trade-offs:** Can lead to a slight degradation in model performance or output quality, which needs to be balanced against the speed and memory benefits.

## II. Prerequisites

*   **Ollama Installation:** Ensure Ollama is correctly installed and running on your system (or within your Docker setup).
*   **Sufficient Hardware:** Fine-tuning can be memory and compute-intensive. Ensure your machine has adequate RAM and GPU resources if you plan to fine-tune larger models.
*   **Data:** A high-quality dataset of product titles and descriptions is paramount.

## III. Step-by-Step Process

### Step 1: Data Preparation (The Most Crucial Step)

The quality of your training data directly impacts the quality of your fine-tuned model.

*   **Source High-Quality Data:**
    *   **Existing Product Catalog:** Your own product database is the best starting point. Identify products with excellent, human-written titles and descriptions.
    *   **Competitor Analysis:** Analyze well-crafted product descriptions from competitors or industry leaders.
    *   **Manual Creation/Refinement:** For specific patterns or HTML structures you want the model to learn, you might need to manually create or refine examples.
*   **Data Format:**
    *   For fine-tuning, you'll typically need pairs of `prompt` and `completion` (or `instruction` and `response`).
    *   **Example for Title Generation:**
        *   `prompt`: "Generate a concise title for a product with the following details: [Product Features, Brand, Material, Use Case]"
        *   `completion`: "Ergonomic Leather Office Chair with Lumbar Support"
    *   **Example for Detailed Description (with HTML):**
        *   `prompt`: "Generate a detailed product description with HTML for: [Product Name, Key Features, Benefits]"
        *   `completion`: "<h3>Key Features:</h3><ul><li><b>Premium Leather:</b> Durable and soft.</li><li><b>Adjustable Lumbar Support:</b> Enhances comfort.</li><li><b>360-Degree Swivel:</b> Maximum flexibility.</li></ul><p>This chair combines ergonomic design with luxurious materials...</p>"
*   **Data Cleaning and Preprocessing:**
    *   **Remove Noise:** Eliminate irrelevant information, typos, or inconsistencies.
    *   **Standardize Formatting:** Ensure consistent use of punctuation, capitalization, and especially HTML tags. If you want `<b>` tags, don't mix them with `<strong>` unless you explicitly want both.
    *   **Balance:** Ensure your dataset is balanced across different product types and desired output styles.
    *   **Quantity:** The more high-quality data, the better. Aim for hundreds to thousands of examples for effective fine-tuning.
*   **HTML Tag Safety:**
    *   **Explicitly Teach:** Your training data *must* contain examples of how HTML tags should be used. The model will learn from these patterns.
    *   **Sanitization:** Even after fine-tuning, always implement a post-processing step in your application to sanitize any generated HTML to prevent Cross-Site Scripting (XSS) vulnerabilities. Use a library like `Bleach` in Python or `DOMPurify` in JavaScript.

### Step 2: Model Selection

*   **Start Small:** Begin with smaller, instruction-tuned models (e.g., `llama3.2:1b-instruct`, `qwen2:1.5b`) as your base. They are faster to fine-tune and require fewer resources.
*   **Consider Task-Specific Models:** Some models are better suited for certain tasks. For example, models specifically trained for summarization or instruction following might be good starting points.

### Step 3: Fine-tuning with Ollama (Using Modelfiles)

Ollama allows you to create custom models by extending existing ones with your own data and instructions via `Modelfiles`.

1.  **Create a `Modelfile`:**
    A `Modelfile` is a simple text file that defines how to build your custom model.

    ```modelfile
    # Modelfile for Product Title Generation
    FROM llama3.2:1b-instruct-q4_K_M # Your chosen base model

    # System prompt to guide the model's behavior
    PARAMETER temperature 0.7
    PARAMETER top_k 40
    PARAMETER top_p 0.9
    PARAMETER repeat_penalty 1.1

    # Instruction to the model
    SYSTEM """You are an expert e-commerce copywriter. Your task is to generate concise, engaging, and SEO-friendly product titles based on provided product information. Focus on clarity and key selling points. Do not include any introductory or concluding remarks, just the title."""

    # Example data (can be extended with more examples)
    # This is a simplified example; for larger datasets, you'd typically use a separate data file
    # and potentially a more advanced fine-tuning script if Ollama's direct Modelfile examples are insufficient.
    # For true fine-tuning with a dataset, Ollama's `ollama create` command can take a `Modelfile`
    # that points to a dataset.
    ```

    *   **`FROM`:** Specifies the base model you're extending.
    *   **`PARAMETER`:** Adjusts inference parameters (e.g., `temperature` for creativity, `top_k`, `top_p` for sampling).
    *   **`SYSTEM`:** Provides a system-level instruction that guides the model's overall behavior. This is crucial for setting the context for your tasks.
    *   **`TEMPLATE` (Advanced):** For more complex instruction-response pairs, you can define a custom `TEMPLATE` in your Modelfile to structure how prompts and completions are fed to the model during inference.

2.  **Prepare Your Dataset for Fine-tuning (JSONL format):**
    For actual fine-tuning with a dataset, Ollama expects a JSONL (JSON Lines) format where each line is a JSON object representing a single training example.

    ```jsonl
    {"prompt": "Generate a concise title for a product with the following details: Brand: XYZ, Type: Wireless Earbuds, Feature: Noise Cancelling", "completion": "XYZ Noise-Cancelling Wireless Earbuds"}
    {"prompt": "Generate a detailed product description with HTML for: Product Name: Smart Coffee Maker, Key Features: Programmable, Wi-Fi Enabled, Built-in Grinder", "completion": "<h3>Smart Coffee Maker</h3><p>Experience the future of brewing with our <b>Wi-Fi enabled</b> Smart Coffee Maker. Program your brew from anywhere, ensuring a fresh cup awaits you. The <i>integrated grinder</i> ensures optimal flavor from whole beans.</p>"}
    ```

3.  **Build Your Custom Model:**
    Once you have your `Modelfile` and (optionally) your JSONL dataset, you can build your custom model using the Ollama CLI:

    ```bash
    ollama create your-custom-model-name -f ./Modelfile --dataset ./your_training_data.jsonl
    ```
    *   Replace `your-custom-model-name` with a unique name for your fine-tuned model.
    *   Replace `./Modelfile` with the path to your `Modelfile`.
    *   Replace `./your_training_data.jsonl` with the path to your prepared dataset.

    Ollama will then download the base model (if not already present) and apply your fine-tuning data.

### Step 4: Quantization (Post-Fine-tuning or for Base Models)

You can quantize models directly using Ollama. This is often done *after* fine-tuning, or you can quantize a base model if you don't plan to fine-tune it but want performance benefits.

1.  **Quantize a Model:**
    ```bash
    ollama create your-quantized-model-name -f ./Modelfile --quantize q4_K_M # or other quantization levels
    ```
    *   You can specify different quantization levels (e.g., `q2_K`, `q4_K_M`, `q5_K_M`, `q8_0`). `q4_K_M` is a good balance of size and quality.
    *   If you're quantizing a fine-tuned model, use its `Modelfile`. If you're quantizing a base model, you can create a simple `Modelfile` that just `FROM`s the base model.

### Step 5: Integration into Your Application

Once you have your fine-tuned and/or quantized models, update your `config.yaml` to use them.

1.  **Update `config.yaml`:**
    Modify the `models` section in your `config.yaml` to point to your new custom models.

    ```yaml
    models:
      title_model: your-custom-title-model-name # e.g., my-product-title-model:latest
      description_model: your-custom-description-model-name # e.g., my-product-desc-model:latest
      provider: ollama
      # ... other settings
    ```
    If you are using quantized models, ensure `quantize: true` is set, and your `quantized_models` mapping is correct.

2.  **Restart Backend:** Restart your `mcp_backend` service for the changes to take effect.

### Step 6: Evaluation and Iteration

*   **Test Thoroughly:** Generate titles and descriptions for a wide range of products.
*   **Human Review:** Have human reviewers assess the quality, accuracy, and adherence to desired formatting (especially HTML safety).
*   **A/B Testing:** If possible, A/B test the output of your new models against previous versions.
*   **Refine Data & Retrain:** Based on feedback, refine your training data, adjust `Modelfile` parameters, and repeat the fine-tuning process.
