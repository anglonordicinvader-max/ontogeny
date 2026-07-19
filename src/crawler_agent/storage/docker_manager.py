"""Docker manager for personal space - supports Windows Docker Desktop and Linux."""

import asyncio
import sys
import tempfile
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import structlog


@dataclass
class Container:
    """Docker container info."""

    id: str
    name: str
    image: str
    status: str
    state: str
    ports: dict[str, Any]
    created: str


@dataclass
class Volume:
    """Docker volume info."""

    name: str
    driver: str
    mountpoint: str
    created: str


@dataclass
class ExecutionResult:
    """Result of code execution in a container."""

    success: bool
    output: str
    error: str
    exit_code: int
    duration_ms: float


class DockerManager:
    """Manage Docker containers and volumes via Docker socket/CLI."""

    def __init__(self, socket_path: str | None = None):
        self.logger = structlog.get_logger()

        if socket_path:
            self.socket_path = socket_path
        elif sys.platform == "win32":
            self.socket_path = "//./pipe/docker_engine"
        else:
            self.socket_path = "/var/run/docker.sock"

        self._use_cli = sys.platform == "win32"
        self.base_url = f"http+unix://{self.socket_path.replace('/', '%2F')}"

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> httpx.Response:
        """Make request to Docker socket."""
        if self._use_cli:
            return await self._cli_request(method, endpoint, **kwargs)

        async with httpx.AsyncClient(
            transport=httpx.AsyncHTTPTransport(uds=self.socket_path)
        ) as client:
            response = await client.request(method, f"http://localhost{endpoint}", **kwargs)
            response.raise_for_status()
            return response

    async def _cli_request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> httpx.Response:
        """Fallback to Docker CLI on Windows."""
        import json as json_mod

        cmd_parts = ["docker"]

        if endpoint.startswith("/containers"):
            if method == "GET" and endpoint.endswith("/json"):
                container_id = endpoint.split("/")[2]
                if container_id == "json":
                    cmd_parts.extend(["ps", "-a", "--format", "{{json .}}"])
                else:
                    cmd_parts.extend(["inspect", container_id])
            elif method == "GET" and endpoint.endswith("/exec"):
                pass
            elif method == "POST" and "/start" in endpoint:
                container_id = endpoint.split("/")[2]
                cmd_parts.extend(["start", container_id])
            elif method == "POST" and "/stop" in endpoint:
                container_id = endpoint.split("/")[2]
                cmd_parts.extend(["stop", container_id])
            elif method == "DELETE":
                container_id = endpoint.split("/")[2]
                cmd_parts.extend(["rm", "-f", container_id])
            elif method == "POST" and endpoint == "/containers/create":
                pass
        elif endpoint.startswith("/images"):
            if endpoint.endswith("/json"):
                cmd_parts.extend(["images", "--format", "{{json .}}"])
        elif endpoint.startswith("/volumes"):
            if method == "GET":
                cmd_parts.extend(["volume", "ls", "--format", "{{json .}}"])

        proc = await asyncio.create_subprocess_exec(
            *cmd_parts,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        class MockResponse:
            def __init__(self, data, status_code=200):
                self._data = data
                self.status_code = status_code

            def json(self):
                return self._data

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise httpx.HTTPStatusError("CLI error", request=None, response=self)

        output = stdout.decode().strip()
        if not output:
            return MockResponse({})

        lines = output.split("\n")
        if len(lines) == 1:
            try:
                return MockResponse(json_mod.loads(lines[0]))
            except json_mod.JSONDecodeError:
                return MockResponse({"output": lines[0]})
        else:
            items = []
            for line in lines:
                try:
                    items.append(json_mod.loads(line))
                except json_mod.JSONDecodeError:
                    continue
            return MockResponse(items)

    async def list_containers(self, all: bool = False) -> list[Container]:
        """List containers."""
        if self._use_cli:
            cmd = ["docker", "ps"]
            if all:
                cmd.append("-a")
            cmd.extend(["--format", "{{json .}}"])

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            output = stdout.decode().strip()
            if not output:
                return []

            import json as json_mod

            containers = []
            for line in output.split("\n"):
                try:
                    c = json_mod.loads(line)
                    containers.append(
                        Container(
                            id=c.get("ID", "")[:12],
                            name=c.get("Names", ""),
                            image=c.get("Image", ""),
                            status=c.get("Status", ""),
                            state=c.get("State", ""),
                            ports=c.get("Ports", ""),
                            created=c.get("CreatedAt", ""),
                        )
                    )
                except (json_mod.JSONDecodeError, KeyError):
                    continue
            return containers

        params = {"all": "true" if all else "false"}
        response = await self._request("GET", "/containers/json", params=params)
        containers = response.json()

        return [
            Container(
                id=c["Id"][:12],
                name=c["Names"][0].lstrip("/"),
                image=c["Image"],
                status=c["Status"],
                state=c["State"],
                ports=c.get("Ports", {}),
                created=c["Created"],
            )
            for c in containers
        ]

    async def run_container(
        self,
        image: str,
        name: str,
        command: str | None = None,
        volumes: dict[str, str] | None = None,
        env: dict[str, str] | None = None,
        ports: dict[str, str] | None = None,
        detach: bool = True,
    ) -> Container:
        """Run a new container."""
        if self._use_cli:
            return await self._run_container_cli(image, name, command, volumes, env, ports)

        config: dict[str, Any] = {
            "Image": image,
            "HostConfig": {
                "Binds": [f"{k}:{v}" for k, v in (volumes or {}).items()],
                "PortBindings": {},
            },
            "Env": [f"{k}={v}" for k, v in (env or {}).items()],
        }

        if command:
            config["Cmd"] = command.split()

        if ports:
            for container_port, host_port in ports.items():
                config["HostConfig"]["PortBindings"][container_port] = [{"HostPort": host_port}]

        response = await self._request(
            "POST", "/containers/create", params={"name": name}, json=config
        )
        container_id = response.json()["Id"]

        await self._request("POST", f"/containers/{container_id}/start")

        info = await self._request("GET", f"/containers/{container_id}/json")
        data = info.json()

        return Container(
            id=container_id[:12],
            name=name,
            image=image,
            status=data["State"]["Status"],
            state=data["State"]["Status"],
            ports=data.get("NetworkSettings", {}).get("Ports", {}),
            created=data["Created"],
        )

    async def _run_container_cli(
        self,
        image: str,
        name: str,
        command: str | None = None,
        volumes: dict[str, str] | None = None,
        env: dict[str, str] | None = None,
        ports: dict[str, str] | None = None,
    ) -> Container:
        """Run container using Docker CLI."""
        cmd = ["docker", "run", "-d", "--name", name]

        for k, v in (volumes or {}).items():
            cmd.extend(["-v", f"{k}:{v}"])

        for k, v in (env or {}).items():
            cmd.extend(["-e", f"{k}={v}"])

        for container_port, host_port in (ports or {}).items():
            cmd.extend(["-p", f"{host_port}:{container_port}"])

        cmd.append(image)
        if command:
            cmd.extend(command.split())

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        container_id = stdout.decode().strip()[:12]

        return Container(
            id=container_id,
            name=name,
            image=image,
            status="running",
            state="running",
            ports=ports or {},
            created="",
        )

    async def stop_container(self, container_id: str, timeout: int = 10) -> None:
        """Stop a container."""
        if self._use_cli:
            proc = await asyncio.create_subprocess_exec(
                "docker",
                "stop",
                container_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return

        await self._request("POST", f"/containers/{container_id}/stop", params={"t": timeout})

    async def remove_container(self, container_id: str, force: bool = False) -> None:
        """Remove a container."""
        if self._use_cli:
            cmd = ["docker", "rm"]
            if force:
                cmd.append("-f")
            cmd.append(container_id)
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return

        await self._request("DELETE", f"/containers/{container_id}", params={"force": force})

    async def exec_in_container(
        self,
        container_id: str,
        command: str,
    ) -> str:
        """Execute command in container."""
        if self._use_cli:
            return await self._exec_cli(container_id, command)

        exec_config = {
            "Cmd": command.split(),
            "AttachStdout": True,
            "AttachStderr": True,
        }
        response = await self._request("POST", f"/containers/{container_id}/exec", json=exec_config)
        exec_id = response.json()["Id"]

        await self._request("POST", f"/exec/{exec_id}/start", json={"Detach": False, "Tty": False})

        return f"Executed: {command}"

    async def _exec_cli(self, container_id: str, command: str) -> str:
        """Execute command using Docker CLI."""
        proc = await asyncio.create_subprocess_exec(
            "docker",
            "exec",
            container_id,
            "sh",
            "-c",
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        output = stdout.decode()
        error = stderr.decode()
        if error and proc.returncode != 0:
            return f"ERROR: {error}"
        return output

    async def exec_with_result(
        self,
        container_id: str,
        command: str,
        timeout: float = 30.0,
    ) -> ExecutionResult:
        """Execute command and capture full result."""
        import time

        start = time.monotonic()

        if self._use_cli:
            proc = await asyncio.create_subprocess_exec(
                "docker",
                "exec",
                container_id,
                "sh",
                "-c",
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except TimeoutError:
                proc.kill()
                return ExecutionResult(
                    success=False,
                    output="",
                    error="Timeout",
                    exit_code=-1,
                    duration_ms=(time.monotonic() - start) * 1000,
                )

            duration = (time.monotonic() - start) * 1000
            return ExecutionResult(
                success=proc.returncode == 0,
                output=stdout.decode(),
                error=stderr.decode(),
                exit_code=proc.returncode or 0,
                duration_ms=duration,
            )

        exec_config = {
            "Cmd": command.split(),
            "AttachStdout": True,
            "AttachStderr": True,
        }
        response = await self._request("POST", f"/containers/{container_id}/exec", json=exec_config)
        exec_id = response.json()["Id"]

        await self._request("POST", f"/exec/{exec_id}/start", json={"Detach": False, "Tty": False})

        duration = (time.monotonic() - start) * 1000
        return ExecutionResult(
            success=True,
            output=f"Executed: {command}",
            error="",
            exit_code=0,
            duration_ms=duration,
        )

    async def list_volumes(self) -> list[Volume]:
        """List volumes."""
        if self._use_cli:
            proc = await asyncio.create_subprocess_exec(
                "docker",
                "volume",
                "ls",
                "--format",
                "{{json .}}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            import json as json_mod

            volumes = []
            for line in stdout.decode().strip().split("\n"):
                if not line:
                    continue
                try:
                    v = json_mod.loads(line)
                    volumes.append(
                        Volume(
                            name=v.get("Name", ""),
                            driver=v.get("Driver", ""),
                            mountpoint="",
                            created="",
                        )
                    )
                except json_mod.JSONDecodeError:
                    continue
            return volumes

        response = await self._request("GET", "/volumes")
        volumes = response.json().get("Volumes", [])

        return [
            Volume(
                name=v["Name"],
                driver=v["Driver"],
                mountpoint=v["Mountpoint"],
                created=v["CreatedAt"],
            )
            for v in volumes
        ]

    async def create_volume(self, name: str, driver: str = "local") -> Volume:
        """Create a volume."""
        if self._use_cli:
            proc = await asyncio.create_subprocess_exec(
                "docker",
                "volume",
                "create",
                name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return Volume(name=name, driver=driver, mountpoint="", created="")

        response = await self._request(
            "POST", "/volumes/create", json={"Name": name, "Driver": driver}
        )
        data = response.json()

        return Volume(
            name=data["Name"],
            driver=data["Driver"],
            mountpoint=data["Mountpoint"],
            created=data["CreatedAt"],
        )

    async def remove_volume(self, name: str, force: bool = False) -> None:
        """Remove a volume."""
        if self._use_cli:
            proc = await asyncio.create_subprocess_exec(
                "docker",
                "volume",
                "rm",
                name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return

        await self._request("DELETE", f"/volumes/{name}", params={"force": force})

    async def pull_image(self, image: str) -> None:
        """Pull a Docker image."""
        if self._use_cli:
            proc = await asyncio.create_subprocess_exec(
                "docker",
                "pull",
                image,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return

        await self._request("POST", "/images/create", params={"fromImage": image})

    async def list_images(self) -> list[dict[str, Any]]:
        """List images."""
        if self._use_cli:
            proc = await asyncio.create_subprocess_exec(
                "docker",
                "images",
                "--format",
                "{{json .}}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            import json as json_mod

            images = []
            for line in stdout.decode().strip().split("\n"):
                if not line:
                    continue
                try:
                    images.append(json_mod.loads(line))
                except json_mod.JSONDecodeError:
                    continue
            return images

        response = await self._request("GET", "/images/json")
        return response.json()

    async def get_disk_usage(self) -> dict[str, Any]:
        """Get disk usage info."""
        if self._use_cli:
            proc = await asyncio.create_subprocess_exec(
                "docker",
                "system",
                "df",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            return {"output": stdout.decode()}

        response = await self._request("GET", "/system/df")
        return response.json()


class CrawlerWorkspace:
    """Dedicated workspace for crawler operations."""

    def __init__(self, docker: DockerManager, workspace_name: str = "crawler-workspace"):
        self.docker = docker
        self.name = workspace_name
        self.logger = structlog.get_logger()

    async def setup(self) -> None:
        """Create workspace with persistent volumes."""
        await self.docker.create_volume(f"{self.name}-data")
        await self.docker.create_volume(f"{self.name}-cache")
        await self.docker.create_volume(f"{self.name}-logs")
        self.logger.info("workspace_created", name=self.name)

    async def start_service(
        self,
        service_name: str,
        image: str,
        ports: dict[str, str] | None = None,
        env: dict[str, str] | None = None,
    ) -> Container:
        """Start a service in the workspace."""
        return await self.docker.run_container(
            image=image,
            name=f"{self.name}-{service_name}",
            volumes={
                f"{self.name}-data": "/data",
                f"{self.name}-cache": "/cache",
            },
            env=env,
            ports=ports,
        )

    async def stop_service(self, service_name: str) -> None:
        """Stop a service."""
        await self.docker.stop_container(f"{self.name}-{service_name}")

    async def list_services(self) -> list[Container]:
        """List workspace services."""
        containers = await self.docker.list_containers(all=True)
        return [c for c in containers if c.name.startswith(self.name)]

    async def cleanup(self) -> None:
        """Remove all workspace resources."""
        services = await self.list_services()
        for service in services:
            await self.docker.remove_container(service.id, force=True)

        for vol_name in [f"{self.name}-data", f"{self.name}-cache", f"{self.name}-logs"]:
            try:
                await self.docker.remove_volume(vol_name)
            except Exception:
                pass

        self.logger.info("workspace_cleaned", name=self.name)


class CodeSandbox:
    """Sandboxed code execution environment using Docker."""

    SANDBOX_IMAGE = "python:3.11-slim"
    CONTAINER_PREFIX = "agent-sandbox"

    def __init__(self, docker: DockerManager):
        self.docker = docker
        self.logger = structlog.get_logger()
        self._active_sandboxes: dict[str, Container] = {}

    async def ensure_image(self) -> None:
        """Ensure the sandbox image is available."""
        images = await self.docker.list_images()
        image_names = [i.get("RepoTags", [""])[0] if isinstance(i, dict) else "" for i in images]
        if not any(self.SANDBOX_IMAGE in name for name in image_names):
            self.logger.info("pulling_sandbox_image", image=self.SANDBOX_IMAGE)
            await self.docker.pull_image(self.SANDBOX_IMAGE)

    async def create_sandbox(self, name: str | None = None) -> str:
        """Create a persistent sandbox container."""
        await self.ensure_image()

        sandbox_name = name or f"{self.CONTAINER_PREFIX}-{id(self) % 10000}"
        container = await self.docker.run_container(
            image=self.SANDBOX_IMAGE,
            name=sandbox_name,
            command="sleep infinity",
            volumes={"agent-code": "/workspace"},
        )
        self._active_sandboxes[sandbox_name] = container
        self.logger.info("sandbox_created", name=sandbox_name)
        return sandbox_name

    async def execute_code(
        self,
        code: str,
        language: str = "python",
        sandbox_name: str | None = None,
        timeout: float = 30.0,
    ) -> ExecutionResult:
        """Write and execute code in the sandbox."""
        if not sandbox_name:
            sandbox_name = await self.create_sandbox()

        container = self._active_sandboxes.get(sandbox_name)
        if not container:
            sandbox_name = await self.create_sandbox()
            container = self._active_sandboxes[sandbox_name]

        if language == "python":
            # Write code via stdin, then run it
            write_cmd = "cat > /workspace/script.py"
            await self.docker._exec_cli(container.id, "mkdir -p /workspace")
            proc = await asyncio.create_subprocess_exec(
                "docker",
                "exec",
                "-i",
                container.id,
                "sh",
                "-c",
                write_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate(input=code.encode())

            result = await self.docker.exec_with_result(
                container.id,
                "python3 /workspace/script.py",
                timeout=timeout,
            )
        elif language == "bash":
            write_cmd = "cat > /workspace/script.sh"
            await self.docker._exec_cli(container.id, "mkdir -p /workspace")
            proc = await asyncio.create_subprocess_exec(
                "docker",
                "exec",
                "-i",
                container.id,
                "sh",
                "-c",
                write_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate(input=code.encode())
            await self.docker._exec_cli(container.id, "chmod +x /workspace/script.sh")

            result = await self.docker.exec_with_result(
                container.id,
                "bash /workspace/script.sh",
                timeout=timeout,
            )
        else:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Unsupported language: {language}",
                exit_code=1,
                duration_ms=0,
            )

        return result

    async def install_package(self, package: str, sandbox_name: str) -> ExecutionResult:
        """Install a package in the sandbox."""
        container = self._active_sandboxes.get(sandbox_name)
        if not container:
            return ExecutionResult(
                success=False,
                output="",
                error="Sandbox not found",
                exit_code=1,
                duration_ms=0,
            )

        return await self.docker.exec_with_result(
            container.id,
            f"pip3 install {package}",
            timeout=60.0,
        )

    async def destroy_sandbox(self, sandbox_name: str) -> None:
        """Destroy a sandbox."""
        container = self._active_sandboxes.pop(sandbox_name, None)
        if container:
            await self.docker.stop_container(container.id)
            await self.docker.remove_container(container.id, force=True)
            self.logger.info("sandbox_destroyed", name=sandbox_name)

    async def list_sandboxes(self) -> list[str]:
        """List active sandboxes."""
        tracked = list(self._active_sandboxes.keys())
        try:
            containers = await self.docker.list_containers(all=False)
            for c in containers:
                if c.name.startswith(self.CONTAINER_PREFIX) and c.name not in tracked:
                    tracked.append(c.name)
        except Exception:
            pass
        return tracked

    async def cleanup_all(self) -> None:
        """Destroy all sandboxes."""
        for name in list(self._active_sandboxes.keys()):
            await self.destroy_sandbox(name)
