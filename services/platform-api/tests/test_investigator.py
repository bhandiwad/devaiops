from pathlib import Path

from aiops.investigator import RuleBasedInvestigator


def test_investigator_crashloop_oom():
    repo_root = Path(__file__).resolve().parents[3]
    investigator = RuleBasedInvestigator(platform_config=None)
    evidence = {
        "k8s": {
            "snapshot": [
                {
                    "status": {
                        "container_statuses": [
                            {
                                "state": {"waiting": {"reason": "CrashLoopBackOff"}},
                                "last_state": {"terminated": {"reason": "OOMKilled"}},
                            }
                        ]
                    }
                }
            ]
        }
    }
    result = investigator.investigate(evidence)
    assert result["fix_type"] == "RESOURCE_TUNE"
