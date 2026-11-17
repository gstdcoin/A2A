"""
GSTD watch-only SDK agent.

ИСПОЛЬЗОВАНИЕ:
    from gstd_a2a import Agent
    Agent.run()  # Register and monitor using GSTD_WALLET_ADDRESS.

ИЛИ:
    agent = Agent(name="MyAgent")
    agent.start()

---
GSTD — The AI Network That Works For You
"""

import os
import time
import json
import math
import threading
import signal
from typing import Optional, Callable, List, Dict, Any
from tonsdk.utils import Address

from .gstd_client import GSTDClient
from .security import SovereignSecurity


class AgentConfig:
    """Конфигурация агента"""
    def __init__(self):
        self.api_url = os.getenv("GSTD_API_URL", "https://app.gstdtoken.com")
        self.api_key = os.getenv("GSTD_API_KEY", "")
        self.wallet_address = os.getenv("GSTD_WALLET_ADDRESS", "")
        self.poll_interval = int(os.getenv("GSTD_POLL_INTERVAL", "5"))
        self.heartbeat_interval = int(os.getenv("GSTD_HEARTBEAT_INTERVAL", "30"))
        self.language = os.getenv("GSTD_LANGUAGE", "ru")
        self.capabilities = []
        self.verbose = os.getenv("GSTD_VERBOSE", "true").lower() == "true"


class Agent:
    """
    Watch-only GSTD node registration and optional explicit task handlers.
    
    Запуск в одну строку:
        Agent.run()
    
    Или с кастомизацией:
        agent = Agent(name="MyBot", capabilities=["image-processing"])
        agent.on_task(my_handler)
        agent.start()
    """
    
    _instance = None
    _running = False
    
    def __init__(
        self,
        name: str = "GSTD-Agent",
        capabilities: List[str] = None,
        config: AgentConfig = None,
        referrer: str = None
    ):
        self.name = name
        self.config = config or AgentConfig()
        self.capabilities = capabilities or self.config.capabilities
        self.referrer = referrer
        
        self.client: Optional[GSTDClient] = None
        self.task_handlers: Dict[str, Callable] = {}
        self.default_handler: Optional[Callable] = None
        
        self._stop_event = threading.Event()
        self._heartbeat_thread = None
        self._worker_thread = None
        
        self.stats = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_earned": 0.0,
            "start_time": None
        }
        
    @classmethod
    def run(cls, **kwargs) -> 'Agent':
        """
        🚀 Запуск агента в ОДНУ СТРОКУ
        
        >>> from gstd_a2a import Agent
        >>> Agent.run()
        
        Register using a public payout address and a separate node identity.
        Tasks require an explicitly registered handler.
        """
        if cls._running:
            print("⚠️  Agent already running!")
            return cls._instance
            
        agent = cls(**kwargs)
        agent.start()
        return agent
    
    def start(self):
        """Register a watch-only node and run its configured handlers."""
        self._init_client()
        self._register()
        self._stop_event.clear()
        self._running = True
        Agent._instance = self
        Agent._running = True
        
        self._print_banner()

        try:
            if threading.current_thread() is threading.main_thread():
                signal.signal(signal.SIGINT, self._signal_handler)
                signal.signal(signal.SIGTERM, self._signal_handler)
            self.stats["start_time"] = time.time()
            self._start_heartbeat()
            self._worker_loop()
        finally:
            self.stop()
    
    def stop(self):
        """Останавливает агента"""
        self._log("🛑 Stopping agent...")
        self._stop_event.set()
        self._running = False
        Agent._running = False
        
        if self._heartbeat_thread and self._heartbeat_thread is not threading.current_thread():
            self._heartbeat_thread.join(timeout=5)
        
        self._print_stats()
        self._log("👋 Agent stopped. See you next time!")
    
    def on_task(self, task_type: str = None):
        """
        Декоратор для регистрации обработчиков задач
        
        @agent.on_task("text-processing")
        def handle_text(task):
            return {"result": process(task["payload"])}
        """
        def decorator(func: Callable):
            if task_type:
                self.task_handlers[task_type] = func
            else:
                self.default_handler = func
            return func
        return decorator
    
    # =========================================================================
    # INTERNAL METHODS
    # =========================================================================
    
    def _init_client(self):
        address = self.config.wallet_address.strip()
        try:
            Address(address)
        except Exception as error:
            raise ValueError("Set GSTD_WALLET_ADDRESS to a public TON payout address") from error

        self.client = GSTDClient(
            api_url=self.config.api_url,
            wallet_address=address,
            api_key=self.config.api_key,
            preferred_language=self.config.language,
        )
        if self.client.health_check().get("status") not in ("ok", "healthy"):
            raise RuntimeError("GSTD platform is unavailable")

    def _register(self):
        self.client.register_node(
            device_name=self.name,
            capabilities=self.capabilities,
            referrer_id=self.referrer,
        )
        if not self.client.send_heartbeat(status="idle"):
            raise RuntimeError("GSTD did not acknowledge the first heartbeat")

    def _start_heartbeat(self):
        """Запускает heartbeat thread"""
        def heartbeat_loop():
            while not self._stop_event.is_set():
                try:
                    self.client.send_heartbeat(status="working")
                except Exception:
                    self._log("Heartbeat failed")
                self._stop_event.wait(self.config.heartbeat_interval)
        
        self._heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
    
    def _worker_loop(self):
        """Основной цикл обработки задач"""
        while not self._stop_event.is_set():
            try:
                # Получаем задачи
                tasks = self.client.get_pending_tasks() if (self.task_handlers or self.default_handler) else []
                
                if tasks:
                    self._log(f"📋 Found {len(tasks)} task(s)")
                    
                    for task in tasks:
                        if self._stop_event.is_set():
                            break
                        self._process_task(task)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                self._log(f"⚠️  Error in worker loop: {e}")
            
            # Ждём перед следующим poll
            self._stop_event.wait(self.config.poll_interval)
    
    def _process_task(self, task: Dict[str, Any]):
        """Обрабатывает одну задачу"""
        task_id = task.get("task_id") or task.get("id")
        if not isinstance(task_id, str) or not task_id:
            return
        task_type = task.get("type") or task.get("task_type", "unknown")
        payload = task.get("payload", {})
        reward = task.get("reward_gstd") or task.get("budget", 0)
        
        # Payload from worker API can be JSON string (from DB)
        if isinstance(payload, str):
            try:
                payload = json.loads(payload) if payload else {}
            except json.JSONDecodeError:
                payload = {}
        if not isinstance(payload, dict):
            payload = {}
        
        task["payload"] = payload  # Ensure handlers receive dict
        self._log(f"⚡ Processing task {task_id[:8]}... (type: {task_type}, reward: {reward} GSTD)")
        
        start_time = time.time()
        
        try:
            # Определяем обработчик
            handler = self.task_handlers.get(task_type) or self.default_handler
            if handler is None:
                raise ValueError("No handler registered for task type")
            
            # Валидация payload (must be dict for sanitize_payload)
            payload, is_safe = SovereignSecurity.sanitize_payload(payload)
            task["payload"] = payload
            if not is_safe:
                self._log("⚠️  Security: Potential injection neutralized")
            
            # Выполняем задачу
            result = handler(task)
            
            # Отправляем результат
            execution_time = int((time.time() - start_time) * 1000)
            if not result or (isinstance(result, dict) and result.get("status") in ("failed", "error")):
                raise ValueError("Task handler produced no successful result")
            expected_model = payload.get("model") or task.get("model")
            model = result.get("model") if isinstance(result, dict) else None
            if expected_model and expected_model != "auto" and not model:
                raise ValueError("Task handler must identify the model it used")
            response = self.client.submit_result(task_id, result, execution_time_ms=execution_time, model=model)
            if not isinstance(response, dict) or response.get("ok") is not True or response.get("task_id") != task_id:
                raise RuntimeError("Grid rejected the task result")
            confirmed_reward = response.get("reward_gstd", 0)
            if isinstance(confirmed_reward, bool) or not isinstance(confirmed_reward, (int, float)) or not math.isfinite(confirmed_reward) or confirmed_reward < 0:
                raise RuntimeError("Grid returned an invalid reward amount")
            
            self.stats["tasks_completed"] += 1
            self.stats["total_earned"] += confirmed_reward
            
            self._log(f"✅ Task {task_id[:8]} completed in {execution_time}ms")
            self._log(f"💰 Earned: {confirmed_reward} GSTD | Total: {self.stats['total_earned']:.4f} GSTD")
            
        except Exception as e:
            self.stats["tasks_failed"] += 1
            self._log(f"❌ Task {task_id[:8]} failed: {e}")
    
    def _signal_handler(self, signum, frame):
        self._stop_event.set()

    def _print_banner(self):
        """Выводит баннер при запуске"""
        if not self.config.verbose:
            return
            
        banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🦾 GSTD AGENT v2.0 — Zero-Config Autonomous Agent         ║
║                                                              ║
║   The AI Network That Works For You                         ║
║   https://app.gstdtoken.com                                  ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
        print(banner)
    
    def _print_stats(self):
        """Выводит статистику при остановке"""
        if not self.config.verbose:
            return
            
        uptime = time.time() - (self.stats["start_time"] or time.time())
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║  📊 SESSION STATISTICS                                       ║
╠══════════════════════════════════════════════════════════════╣
║  ⏱️  Uptime:           {hours}h {minutes}m                               
║  ✅ Tasks Completed:   {self.stats['tasks_completed']}                                    
║  ❌ Tasks Failed:      {self.stats['tasks_failed']}                                    
║  💰 Total Earned:      {self.stats['total_earned']:.6f} GSTD                    
╚══════════════════════════════════════════════════════════════╝
""")
    
    def _log(self, message: str):
        """Логирование"""
        if self.config.verbose:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] {message}")


# ============================================================================
# CONVENIENCE EXPORTS
# ============================================================================

def run(**kwargs):
    """Shortcut для Agent.run()"""
    return Agent.run(**kwargs)

def cli():
    Agent.run()


def quick_start(name: str = "QuickAgent", referrer: str = None):
    """
    Быстрый старт для новых пользователей
    
    >>> from gstd.agent import quick_start
    >>> quick_start()
    """
    return Agent.run(name=name, referrer=referrer)


# Auto-run if executed directly
if __name__ == "__main__":
    cli()
