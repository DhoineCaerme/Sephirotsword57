import re
import subprocess
import json
from typing import ClassVar, List, Optional
from pydantic import Field
from crewai.tools import BaseTool


class SafeBashTool(BaseTool):
    """
    Read-only Bash executor with two modes:
      - REAL MODE: runs commands on the local machine via subprocess.
      - MOCK MODE: returns simulated OS state from a dataset sample for evaluation.
    """

    name: str = "Safe Read-Only Bash Executor"
    description: str = (
        "Executes read-only Bash commands to probe the live Linux system. "
        "Blocked commands that could modify state are rejected before execution. "
        "Supports mock mode for dataset evaluation."
    )

    BLOCKLIST: ClassVar[List[str]] = [
        r"\brm\b", r"\bmv\b", r"\bdd\b", r"\bmkfs\b",
        r"\bchmod\b", r"\bchown\b",
        r"systemctl\s+stop", r"systemctl\s+disable",
        r"\bkill\b", r"\bpkill\b",
        r"\breboot\b", r"\bshutdown\b",
        r"apt[-\s]remove", r"apt[-\s]purge",
        r">>?[^>]",
        r"\bsudo\s+passwd\b",
    ]

    mock_dataset_state: Optional[dict] = Field(
        default=None,
        description="When set, the tool returns simulated telemetry instead of running real commands."
    )

    def _is_blocked(self, command: str) -> Optional[str]:
        for pattern in self.BLOCKLIST:
            if re.search(pattern, command):
                return pattern
        return None

    def _mock_response(self, command: str) -> str:
        """
        Returns crystal-clear simulated responses the agent can parse without ambiguity.
        Each response explicitly states what WAS found and what was NOT found.
        """
        state = self.mock_dataset_state
        cmd = command.lower()

        # Port probing (ss -tuln, netstat)
        if "ss" in cmd or "netstat" in cmd:
            ports = state.get("active_ports", [])
            if not ports:
                return (
                    "RESULT: No ports are currently listening on this system. "
                    "active_ports = []"
                )
            lines = "\n".join(
                f"tcp   LISTEN  0  0  0.0.0.0:{p}  0.0.0.0:*" for p in ports
            )
            return (
                f"RESULT: The following ports are currently LISTENING on this system:\n"
                f"{lines}\n"
                f"active_ports = {json.dumps(ports)}"
            )

        # Package probing (dpkg -l)
        if "dpkg" in cmd:
            packages = state.get("installed_packages", [])
            if not packages:
                return (
                    "RESULT: Package NOT found. dpkg reports this package is not installed. "
                    "installed_packages = []"
                )
            lines = "\n".join(f"ii  {p}  1.0.0  amd64  installed" for p in packages)
            return (
                f"RESULT: The following packages ARE installed:\n"
                f"{lines}\n"
                f"installed_packages = {json.dumps(packages)}"
            )

        # Docker probing
        if "docker" in cmd:
            services = state.get("running_services", [])
            # Extract the specific container name being queried
            # e.g. "docker ps --filter name=redis-server" -> "redis-server"
            import re as _re
            name_match = _re.search(r'name=(\S+)', command)
            queried = name_match.group(1).lower() if name_match else None
            if queried:
                svc_lower = [s.lower() for s in services]
                if queried in svc_lower:
                    return (
                        f"RESULT: Container '{queried}' IS running (Up).\n"
                        f"running_services = {json.dumps([queried])}"
                    )
                else:
                    return (
                        f"RESULT: Container '{queried}' is NOT running (not found).\n"
                        f"Other containers running: {json.dumps(services)}\n"
                        f"running_services = []"
                    )
            if not services:
                return (
                    "RESULT: No Docker containers are currently running. "
                    "running_services = []"
                )
            lines = "\n".join(f"abc123  {s}  Up 2 hours" for s in services)
            return (
                f"RESULT: The following containers ARE running:\n"
                f"{lines}\n"
                f"running_services = {json.dumps(services)}"
            )

        # Systemd probing
        if "systemctl" in cmd:
            services = state.get("running_services", [])
            # Extract the specific service name being queried from the command
            # e.g. "systemctl is-active redis-server" -> "redis-server"
            import re as _re
            svc_match = _re.search(r'systemctl\s+\S+\s+(\S+)', command)
            queried = svc_match.group(1).lower() if svc_match else None
            if queried:
                svc_lower = [s.lower() for s in services]
                if queried in svc_lower:
                    return (
                        f"RESULT: Service '{queried}' IS active (running).\n"
                        f"running_services = {json.dumps([queried])}"
                    )
                else:
                    return (
                        f"RESULT: Service '{queried}' is NOT active (inactive/dead).\n"
                        f"Other services running: {json.dumps(services)}\n"
                        f"running_services = []"
                    )
            # Fallback if we can't parse service name
            if not services:
                return (
                    "RESULT: Service is NOT active (inactive/dead). "
                    "running_services = []"
                )
            svc_lines = "\n".join(services)
            return (
                f"RESULT: The following services ARE active:\n"
                f"{svc_lines}\n"
                f"running_services = {json.dumps(services)}"
            )

        # Environment variable probing
        if "printenv" in cmd or "env" in cmd:
            env_vars = state.get("active_env_vars", [])
            if not env_vars:
                return (
                    "RESULT: Environment variable NOT set. printenv returned nothing. "
                    "active_env_vars = []"
                )
            lines = "\n".join(f"{ev['name']}={ev.get('value', '')}" for ev in env_vars)
            return (
                f"RESULT: The following environment variables ARE set:\n"
                f"{lines}\n"
                f"active_env_vars = {json.dumps(env_vars)}"
            )

        # Fallback
        return (
            f"RESULT: Command executed. Full system state:\n"
            f"{json.dumps(state, indent=2)}"
        )

    def _run(self, command: str) -> str:
        # 1. Security check
        blocked = self._is_blocked(command)
        if blocked:
            return (
                f"[SECURITY VIOLATION]: Command rejected. "
                f"Matched blocked pattern: '{blocked}'. "
                f"Only read-only commands are permitted."
            )

        # 2. Mock mode
        if self.mock_dataset_state is not None:
            return self._mock_response(command)

        # 3. Real mode
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip() or "[OK: command returned no output]"
            return f"[COMMAND ERROR (exit {result.returncode})]: {result.stderr.strip()}"
        except subprocess.TimeoutExpired:
            return "[TIMEOUT ERROR]: Command exceeded 10-second limit."
        except Exception as e:
            return f"[SYSTEM ERROR]: {str(e)}"