from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union

# --- Standard Protocol Definitions (The "Language" of Agents) ---

class BaseTaskPayload(BaseModel):
    """Base schema for all tasks to ensure agents speak the same language"""
    protocol_version: str = "1.0"
    
    class Config:
        extra = "allow"

# 1. Text Processing Protocol
class TextProcessingTask(BaseTaskPayload):
    text: str = Field(..., description="The input text content to process")
    instruction: str = Field(..., description="What to do with the text")
    language: Optional[str] = "en"
    format: Optional[str] = "markdown"

# 2. Image Generation Protocol
class ImageGenerationTask(BaseTaskPayload):
    prompt: str = Field(..., description="The image generation prompt")
    width: int = 1024
    height: int = 1024
    steps: int = 30
    model: Optional[str] = "stable-diffusion-xl"

# 3. Data Scraping Protocol
class DataScrapingTask(BaseTaskPayload):
    url: str = Field(..., description="Target URL to scrape")
    selectors: Optional[List[str]] = Field(None, description="CSS selectors to extract")
    actions: Optional[List[Dict[str, Any]]] = Field(None, description="Interaction steps (click, wait)")

# 4. OpenClaw Physical Control Protocol
class OpenClawTask(BaseTaskPayload):
    device_id: str = Field(..., description="Target device identifier")
    command: str = Field(..., description="Command to execute (e.g., 'move_arm', 'read_sensor')")
    parameters: Dict[str, Any] = Field(default_factory=dict)

# 5. Settlement Protocol (Invoicing)
class InvoiceTask(BaseTaskPayload):
    amount_gstd: float = Field(..., description="Amount of GSTD to be paid")
    description: str = Field(..., description="Reason for the invoice")
    issuer_address: str = Field(..., description="Wallet address of the service provider")
    payer_address: str = Field(..., description="Wallet address of the client")
    task_id: Optional[str] = Field(None, description="Optional linked task ID")

# 6. Fine-Tuning Protocol
class FineTuneTask(BaseTaskPayload):
    job_id: str = Field(..., description="Unique training job identifier")
    base_model: str = Field(..., description="Model to fine-tune: llama3.1:8b | qwen2.5:7b | mistral:7b")
    domain: str = Field(default="general", description="Training domain for specialization routing")
    shard_url: str = Field(..., description="Signed URL to JSONL dataset shard (Alpaca format)")
    steps: int = Field(default=100, ge=10, le=10000)
    epochs: int = Field(default=1, ge=1, le=10)
    reward_gstd: float = Field(default=0.0, description="GSTD reward for this shard")

# 7. Gradient Submission Protocol
class GradientSubmission(BaseTaskPayload):
    job_id: str = Field(..., description="Training job this gradient belongs to")
    node_id: str = Field(..., description="Node that produced this gradient")
    domain: str = Field(default="general")
    metacognitive_score: float = Field(..., ge=0.0, le=1.0, description="Quality score from MetacognitiveEvaluator")
    gradient_norm: float = Field(..., ge=0.0, description="L2 norm of the gradient delta")
    dataset_size: int = Field(..., ge=1)
    val_loss_improvement: float = Field(..., description="(before-after)/before validation loss change")
    lora_path: str = Field(default="", description="Path or URL to LoRA adapter weights")

# --- Registry ---
TASK_SCHEMAS = {
    "text-processing": TextProcessingTask,
    "image-generation": ImageGenerationTask,
    "data-scraping": DataScrapingTask,
    "openclaw-control": OpenClawTask,
    "settlement-invoice": InvoiceTask,
    "finetune": FineTuneTask,
    "federated": FineTuneTask,
    "gradient-submission": GradientSubmission,
}

def validate_task_payload(task_type: str, payload: Dict[str, Any]) -> bool:
    """Ensures the payload matches the strict protocol definition for the task type"""
    schema = TASK_SCHEMAS.get(task_type)
    if not schema:
        # Unknown protocol - allow but warn
        return True 
    try:
        schema(**payload)
        return True
    except Exception:
        return False
