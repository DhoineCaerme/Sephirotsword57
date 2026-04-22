import subprocess
import json
from crewai.tools import BaseTool

class SafeBashTool(BaseTool):
    name: str = "Safe Read-Only Bash Executor"
    description: str = "Executes read-only Bash commands. Can run in real mode or mock mode for dataset evaluation."
    
    # We will use this to inject the simulated state from dataset
    mock_dataset_state: dict = None 
    
    BLOCKLIST = ["rm", "mv", "dd", "chmod", "chown", "systemctl stop", "systemctl disable", "kill", "reboot", "shutdown", ">", ">>"]

    def _run(self, command: str) -> str:
        # 1. Security Check
        for blocked_word in self.BLOCKLIST:
            if blocked_word in command:
                return f"[SECURITY VIOLATION]: '{blocked_word}' is blocked."

        # 2. MOCK MODE (For Doc2State-100 Evaluation)
        if self.mock_dataset_state is not None:
            return f"Simulated Command Execution Success. Telemetry data found: {json.dumps(self.mock_dataset_state)}"

        # 3. REAL MODE (For live deployment)
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return result.stdout.strip()
            return f"[COMMAND ERROR]: {result.stderr.strip()}"
        except Exception as e:
            return f"[SYSTEM ERROR]: {str(e)}"