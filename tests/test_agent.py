from gstd_a2a.agent import Agent


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
    agent.wallet = None
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
