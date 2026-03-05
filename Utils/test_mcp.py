import subprocess
import json
import sys
import time
import threading
import os

# Запускаем MCP-сервер как подпроцесс
server_cmd = [sys.executable, "-m", "MCPServer.YouTrackMCPServer"]
proc = subprocess.Popen(
    server_cmd,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1  # line buffered
)

def read_output(stream, timeout=5):
    """Читает строку из потока с таймаутом."""
    result = []
    event = threading.Event()
    def reader():
        line = stream.readline()
        if line:
            result.append(line)
        event.set()
    thread = threading.Thread(target=reader)
    thread.daemon = True
    thread.start()
    if not event.wait(timeout):
        raise TimeoutError("Таймаут чтения из stdout")
    return result[0] if result else None

try:
    # 1. Отправляем запрос инициализации
    init_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "0.1.0",
            "capabilities": {
                "tools": {}   # 👈 добавьте эту строку
            },
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        },
        "id": 1
    }
    proc.stdin.write(json.dumps(init_request) + "\n")
    proc.stdin.flush()

    # Читаем ответ initialize
    init_response = read_output(proc.stdout)
    print("Initialize response:", init_response)

    # 2. Отправляем запрос tools/list
    tools_request = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 2
    }
    proc.stdin.write(json.dumps(tools_request) + "\n")
    proc.stdin.flush()

    tools_response = read_output(proc.stdout)
    print("Tools list response:", tools_response)

    # Можно также прочитать stderr для отладки
    time.sleep(0.5)
    stderr = proc.stderr.read()
    if stderr:
        print("\nStderr:")
        print(stderr)

except Exception as e:
    print("Ошибка:", e)
finally:
    proc.terminate()