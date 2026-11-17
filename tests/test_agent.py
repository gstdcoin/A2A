from unittest.mock import Mock

from gstd_a2a.agent import Agent, AgentConfig


def test_agent_registers_a_public_address_without_opening_a_wallet(monkeypatch):
    address = "0:" + "ab" * 32
    monkeypatch.setenv("GSTD_WALLET_ADDRESS", address)
    client = Mock()
    client.health_check.return_value = {"status": "ok"}
    client.send_heartbeat.return_value = True
    factory = Mock(return_value=client)
    monkeypatch.setattr("gstd_a2a.agent.GSTDClient", factory)

    agent = Agent(config=AgentConfig())
    agent._init_client()
    agent._register()

    assert factory.call_args.kwargs["wallet_address"] == address
    assert "private_key" not in factory.call_args.kwargs
    assert client.register_node.call_args.kwargs["capabilities"] == []
    client.reauthenticate.assert_not_called()


def test_agent_never_submits_a_placeholder_for_an_unknown_task():
    agent = Agent()
    agent.client = Mock()

    agent._process_task({"task_id": "task-1", "type": "inference", "payload": {"prompt": "sample"}})

    assert agent.stats["tasks_failed"] == 1
    agent.client.submit_result.assert_not_called()


class StubClient:
    def __init__(self, response):
        self.response = response

    def submit_result(self, *args, **kwargs):
        return self.response


def make_agent(response):
    agent = Agent.__new__(Agent)
    agent.task_handlers = {"test": lambda task: {"result": "done"}}
    agent.default_handler = None
    agent.client = StubClient(response)
    agent.stats = {"tasks_completed": 0, "tasks_failed": 0, "total_earned": 0.0}
    agent._log = lambda message: None
    return agent


def test_agent_counts_only_server_confirmed_reward():
    agent = make_agent({"ok": True, "task_id": "task-1", "reward_gstd": 0.25})

    agent._process_task({"task_id": "task-1", "type": "test", "reward_gstd": 999})

    assert agent.stats["tasks_completed"] == 1
    assert agent.stats["total_earned"] == 0.25


def test_agent_does_not_count_rejected_submission_as_completed():
    agent = make_agent({"ok": False, "task_id": "task-1", "reward_gstd": 999})

    agent._process_task({"task_id": "task-1", "type": "test", "reward_gstd": 999})

    assert agent.stats["tasks_completed"] == 0
    assert agent.stats["tasks_failed"] == 1
    assert agent.stats["total_earned"] == 0.0
