"""Command-line entry point (the web API lives in backend/main.py).

    .venv/bin/python -m backend.cli                          # Boss works the open tickets
    .venv/bin/python -m backend.cli --approved-by "Jane Doe"  # a human approves spending for this run
    .venv/bin/python -m backend.cli --role facilities --task "Verify the rent notice on ticket 102"

--approved-by is the ONLY way a payment can be recorded; leave it off and agents can only request approval.
"""
import argparse
import asyncio

from backend.models import RunLimits, Role
from backend.runtime import run_team

DEFAULT_TASK = ("Work all open tickets. Triage them, delegate to the specialists, check cash across tickets, "
                "set ticket statuses, and return your final plan.")


def main() -> None:
    p = argparse.ArgumentParser(description="Run the Campus Customs agent team.")
    p.add_argument("--role", default="boss", choices=[r.value for r in Role])
    p.add_argument("--task", default=DEFAULT_TASK)
    p.add_argument("--approved-by", default=None, help="Name of the human approving spending for this run.")
    p.add_argument("--max-tokens", type=int, default=RunLimits().total_tokens_limit)
    p.add_argument("--max-requests", type=int, default=RunLimits().request_limit)
    a = p.parse_args()
    limits = RunLimits(total_tokens_limit=a.max_tokens, request_limit=a.max_requests)
    out = asyncio.run(run_team(Role(a.role), a.task, approved_by=a.approved_by, limits=limits))
    print(out.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
