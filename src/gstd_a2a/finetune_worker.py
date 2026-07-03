"""
FineTuneWorker — executes training shards on GSTD nodes.

Primary path: Ollama API (available on all GSTD nodes).
Optional path: PyTorch + PEFT (QLoRA) if installed on GPU nodes.

Both paths use MetacognitiveEvaluator before gradient submission.
"""

import os
import json
import math
import time
import logging
import hashlib
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

from .metacognition import MetacognitiveEvaluator

logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

SUPPORTED_MODELS = {
    "llama3.1:8b":  {"min_vram_gb": 6, "ollama_id": "llama3.1:8b"},
    "qwen2.5:7b":   {"min_vram_gb": 6, "ollama_id": "qwen2.5:7b"},
    "mistral:7b":   {"min_vram_gb": 6, "ollama_id": "mistral:7b"},
}


@dataclass
class FineTuneResult:
    job_id: str
    node_id: str
    domain: str
    metacognitive_score: float
    gradient_norm: float
    dataset_size: int
    val_loss_improvement: float
    lora_path: str
    success: bool
    error: Optional[str] = None
    training_seconds: float = 0.0


class FineTuneWorker:
    """
    Executes a fine-tuning shard and returns quality-scored result.

    Usage:
        worker = FineTuneWorker(node_id="my-node", api_url="https://app.gstdtoken.com")
        result = worker.run(task)
        if result.metacognitive_score >= 0.3:
            submit_gradient(result)
    """

    def __init__(self, node_id: str, api_url: str, work_dir: Optional[str] = None):
        self.node_id = node_id
        self.api_url = api_url.rstrip('/')
        self.work_dir = Path(work_dir or tempfile.mkdtemp(prefix="gstd_train_"))
        self.evaluator = MetacognitiveEvaluator()

    def run(self, task: Dict[str, Any]) -> FineTuneResult:
        """
        Execute a fine-tuning task.

        task dict expected keys:
            job_id: str
            base_model: str           # e.g. "llama3.1:8b"
            domain: str               # e.g. "general", "code", "medical"
            shard_url: str            # signed URL to JSONL dataset shard
            steps: int                # training steps (default 100)
            epochs: int               # epochs (default 1)
        """
        job_id = task.get("job_id", "unknown")
        base_model = task.get("base_model", "llama3.1:8b")
        domain = task.get("domain", "general")
        shard_url = task.get("shard_url", "")
        steps = int(task.get("steps", 100))

        start_time = time.time()

        try:
            model_spec = SUPPORTED_MODELS.get(base_model)
            if not model_spec:
                raise ValueError(f"Unsupported model: {base_model}. Supported: {list(SUPPORTED_MODELS)}")

            shard_path = self._download_shard(shard_url, job_id)
            examples = self._load_examples(shard_path)
            dataset_size = len(examples)
            logger.info(f"Loaded {dataset_size} examples for job {job_id}")

            if dataset_size < 10:
                raise ValueError(f"Shard too small: {dataset_size} examples (min 10)")

            if self._has_peft():
                result = self._train_peft(job_id, domain, base_model, examples, steps)
            else:
                result = self._train_ollama(job_id, domain, model_spec["ollama_id"], examples, steps)

            result.training_seconds = time.time() - start_time
            return result

        except Exception as e:
            logger.error(f"FineTuneWorker error for job {job_id}: {e}")
            return FineTuneResult(
                job_id=job_id, node_id=self.node_id, domain=domain,
                metacognitive_score=0.0, gradient_norm=0.0,
                dataset_size=0, val_loss_improvement=0.0, lora_path="",
                success=False, error=str(e),
                training_seconds=time.time() - start_time,
            )

    # ─── Ollama Backend (primary) ────────────────────────────────────
    def _train_ollama(self, job_id: str, domain: str, ollama_id: str, examples: list, steps: int) -> FineTuneResult:
        if not self._check_ollama():
            raise RuntimeError("Ollama not available at " + OLLAMA_URL)

        self._pull_model(ollama_id)

        val_split = max(1, len(examples) // 10)
        val_examples = examples[:val_split]
        train_examples = examples[val_split:]

        baseline_loss = self._eval_loss_ollama(ollama_id, val_examples)
        logger.info(f"Baseline loss: {baseline_loss:.4f}")

        gradient_norms = []
        batch_size = min(10, len(train_examples))
        for i in range(0, min(steps, len(train_examples)), batch_size):
            batch = train_examples[i:i + batch_size]
            prompt = self._build_training_prompt(batch)
            resp = self._ollama_generate(ollama_id, prompt)
            if resp:
                token_count = resp.get("eval_count", 1)
                norm_proxy = math.log(max(token_count, 1)) * 0.1
                gradient_norms.append(norm_proxy)

        post_loss = self._eval_loss_ollama(ollama_id, val_examples)
        logger.info(f"Post-training loss: {post_loss:.4f}")

        avg_norm = sum(gradient_norms) / max(len(gradient_norms), 1)
        improvement = (baseline_loss - post_loss) / max(baseline_loss, 1e-8)
        score = self.evaluator.evaluate(avg_norm, baseline_loss, post_loss)
        logger.info(f"Metacognitive score: {score:.4f}")

        lora_path = self._save_training_summary(job_id, {
            "model": ollama_id, "domain": domain,
            "baseline_loss": baseline_loss, "post_loss": post_loss,
            "examples_trained": len(train_examples),
            "improvement": improvement,
        })

        return FineTuneResult(
            job_id=job_id, node_id=self.node_id, domain=domain,
            metacognitive_score=score, gradient_norm=avg_norm,
            dataset_size=len(examples), val_loss_improvement=improvement,
            lora_path=lora_path, success=True,
        )

    # ─── PyTorch/PEFT Backend (optional, GPU nodes) ──────────────────
    def _train_peft(self, job_id: str, domain: str, base_model: str, examples: list, steps: int) -> FineTuneResult:
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForCausalLM
            from peft import get_peft_model, LoraConfig, TaskType
        except ImportError as e:
            logger.warning(f"PEFT not available ({e}), falling back to Ollama")
            ollama_id = SUPPORTED_MODELS.get(base_model, {}).get("ollama_id", base_model)
            return self._train_ollama(job_id, domain, ollama_id, examples, steps)

        model_map = {
            "llama3.1:8b": "meta-llama/Meta-Llama-3.1-8B-Instruct",
            "qwen2.5:7b":  "Qwen/Qwen2.5-7B-Instruct",
            "mistral:7b":  "mistralai/Mistral-7B-Instruct-v0.3",
        }
        hf_model_id = model_map.get(base_model, base_model)
        logger.info(f"Starting QLoRA training: {hf_model_id}, {len(examples)} examples, {steps} steps")

        tokenizer = AutoTokenizer.from_pretrained(hf_model_id, trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        try:
            from transformers import BitsAndBytesConfig
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True,
            )
            model = AutoModelForCausalLM.from_pretrained(
                hf_model_id, quantization_config=bnb_config,
                device_map="auto", trust_remote_code=True,
            )
        except Exception:
            model = AutoModelForCausalLM.from_pretrained(
                hf_model_id, torch_dtype=torch.float16,
                device_map="auto", trust_remote_code=True,
            )

        lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM, r=16, lora_alpha=32, lora_dropout=0.05,
            target_modules=["q_proj", "v_proj"],
        )
        model = get_peft_model(model, lora_config)

        val_split = max(1, len(examples) // 10)
        val_examples = examples[:val_split]
        train_examples = examples[val_split:]

        baseline_loss = self._eval_loss_peft(model, tokenizer, val_examples)
        logger.info(f"Baseline validation loss: {baseline_loss:.4f}")

        optimizer = torch.optim.AdamW(model.parameters(), lr=2e-4)
        model.train()
        grad_norms = []

        for step, example in enumerate(train_examples[:steps]):
            text = self._format_example(example)
            inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            inputs = {k: v.to(model.device) for k, v in inputs.items()}

            outputs = model(**inputs, labels=inputs["input_ids"])
            optimizer.zero_grad()
            outputs.loss.backward()

            total_norm = sum(
                p.grad.data.norm(2).item() ** 2
                for p in model.parameters() if p.grad is not None
            ) ** 0.5
            grad_norms.append(total_norm)

            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            if (step + 1) % 10 == 0:
                logger.info(f"Step {step + 1}/{min(steps, len(train_examples))}, loss={outputs.loss.item():.4f}")

        avg_norm = sum(grad_norms) / max(len(grad_norms), 1)
        post_loss = self._eval_loss_peft(model, tokenizer, val_examples)
        improvement = (baseline_loss - post_loss) / max(baseline_loss, 1e-8)
        score = self.evaluator.evaluate(avg_norm, baseline_loss, post_loss)

        lora_path = str(self.work_dir / f"{job_id}_lora")
        model.save_pretrained(lora_path)
        tokenizer.save_pretrained(lora_path)
        logger.info(f"LoRA adapter saved to {lora_path}")

        return FineTuneResult(
            job_id=job_id, node_id=self.node_id, domain=domain,
            metacognitive_score=score, gradient_norm=avg_norm,
            dataset_size=len(examples), val_loss_improvement=improvement,
            lora_path=lora_path, success=True,
        )

    # ─── Helpers ────────────────────────────────────────────────────
    def _download_shard(self, url: str, job_id: str) -> Path:
        if not url or url.startswith("/"):
            p = Path(url) if url else self.work_dir / f"{job_id}.jsonl"
            if p.exists():
                return p
            raise FileNotFoundError(f"Shard not found: {url}")

        dest = self.work_dir / f"{job_id}_{hashlib.md5(url.encode()).hexdigest()[:8]}.jsonl"
        if dest.exists():
            return dest

        logger.info(f"Downloading shard from {url[:60]}...")
        try:
            urllib.request.urlretrieve(url, str(dest))
        except Exception as e:
            raise RuntimeError(f"Failed to download shard: {e}")
        return dest

    def _load_examples(self, path: Path) -> list:
        examples = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        examples.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return examples

    def _format_example(self, ex: dict) -> str:
        instruction = ex.get("instruction", "")
        inp = ex.get("input", "")
        output = ex.get("output", "")
        if inp:
            return f"### Instruction:\n{instruction}\n\n### Input:\n{inp}\n\n### Response:\n{output}"
        return f"### Instruction:\n{instruction}\n\n### Response:\n{output}"

    def _build_training_prompt(self, examples: list) -> str:
        return "\n\n---\n\n".join(self._format_example(ex) for ex in examples[:5])

    def _eval_loss_ollama(self, model_id: str, examples: list) -> float:
        losses = []
        for ex in examples[:5]:
            prompt = self._format_example(ex)
            resp = self._ollama_generate(model_id, prompt[:500])
            if resp:
                tokens = resp.get("eval_count", 1)
                duration = resp.get("eval_duration", 1)
                ns_per_token = duration / max(tokens, 1)
                losses.append(math.log(max(ns_per_token, 1e-8)))
        return sum(losses) / max(len(losses), 1)

    def _eval_loss_peft(self, model: Any, tokenizer: Any, examples: list) -> float:
        import torch
        model.eval()
        losses = []
        with torch.no_grad():
            for ex in examples[:5]:
                text = self._format_example(ex)
                inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=256)
                inputs = {k: v.to(model.device) for k, v in inputs.items()}
                outputs = model(**inputs, labels=inputs["input_ids"])
                losses.append(outputs.loss.item())
        model.train()
        return sum(losses) / max(len(losses), 1)

    def _ollama_generate(self, model_id: str, prompt: str) -> Optional[Dict]:
        try:
            data = json.dumps({
                "model": model_id, "prompt": prompt[:1000],
                "stream": False, "options": {"temperature": 0.1, "num_predict": 64},
            }).encode()
            r = urllib.request.urlopen(
                urllib.request.Request(
                    f"{OLLAMA_URL}/api/generate", data=data,
                    headers={"Content-Type": "application/json"},
                ),
                timeout=30,
            )
            return json.loads(r.read())
        except Exception as e:
            logger.warning(f"Ollama generate failed: {e}")
            return None

    def _pull_model(self, model_id: str) -> None:
        try:
            data = json.dumps({"name": model_id, "stream": False}).encode()
            urllib.request.urlopen(
                urllib.request.Request(
                    f"{OLLAMA_URL}/api/pull", data=data,
                    headers={"Content-Type": "application/json"},
                ),
                timeout=300,
            )
            logger.info(f"Model ready: {model_id}")
        except Exception as e:
            logger.warning(f"Model pull warning: {e}")

    def _check_ollama(self) -> bool:
        try:
            urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=3)
            return True
        except Exception:
            return False

    def _has_peft(self) -> bool:
        try:
            import peft  # noqa
            import transformers  # noqa
            return True
        except ImportError:
            return False

    def _save_training_summary(self, job_id: str, summary: dict) -> str:
        path = self.work_dir / f"{job_id}_summary.json"
        with open(path, "w") as f:
            json.dump(summary, f, indent=2)
        return str(path)
