#!/bin/usr/env python3

import os
import json
import subprocess
import datetime
import requests
import psutil
from dotenv import load_dotenv

load_dotenv()

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
LOG_FILE = "logs/incident.log"

THRESHOLDS = {
    "cpu":          {"warning": 80, "critical": 95},
    "memory":       {"warning": 80, "critical": 95},
    "disk":    {"warning": 80, "critical": 95},
}

SERVICES_TO_MONITOR = [
    "nginx",
    "postgresql",
    "docker",
]



def log_incident(level, check, value, message):
    entry = {
        "timestamp":    datetime.datetime.now(datetime.UTC).isoformat() + "Z",
        "level":        level,
        "check":        check,
        "value":        round(value, 1),
        "message":      message,
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"[{level.upper()}] {message}")    



def send_slack_alert(level, message):
    if not SLACK_WEBHOOK_URL:
        print("No Slack webhook configured - skipping alert")
        return
    emoji = ":red_circle:" if level == "critical" else ":warning:"
    payload = {
        "text": f"{emoji} * [{level.upper()}] * {message}"
    }
    try:
        requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=5)
    except Exception as e:
        print(f"Slack alert failed: {e}")    



def check_cpu():
    usage = psutil.cpu_percent(interval=2)
    if usage >= THRESHOLDS["cpu"]["critical"]:
        msg = f"CPU critical: {usage:.1f}% (threshold: {THRESHOLDS['cpu']['critical']}%)"
        log_incident("critical", "cpu", usage, msg)
        send_slack_alert("critical", msg)
    elif usage >= THRESHOLDS["cpu"]["warning"]:
        msg = f"CPU warning: {usage:.1f}% used"
        log_incident("warning", "cpu", usage, msg)
        send_slack_alert("critical", msg)



def check_memory():
    mem = psutil.virtual_memory()
    usage = mem.percent
    if usage >= THRESHOLDS["memory"]["critical"]:
        msg = f"Memory critical: {usage:.1f}% used ({mem.used // 1024**2}MB / {mem.total // 1024**2}MB)"
        log_incident("critical", "memory", usage, msg)
        send_slack_alert("critical", msg)
    elif usage >= THRESHOLDS["memory"]["warning"]:
        msg = f"Memory warning: {usage:.1f}% used"
        log_incident("memory", "warning", usage, msg)
        send_slack_alert("warning", msg)



def check_disks():
    disk = psutil.disk_usage("/")
    usage = disk.percent
    if usage >= THRESHOLDS["disk"]["critical"]:
        msg = f"Disk critical: {usage:.1f}% used ({disk.free // 1024**3})GB free"
        log_incident("critical", "disk", usage, msg)
        send_slack_alert("critical", msg)
    elif usage >= THRESHOLDS["disk"]["warning"]:
        msg = f"Disk warning: {usage:.1f}% used"
        log_incident("warning", "disk", usage, msg)
        send_slack_alert("warning", msg)


def check_services():
    for service in SERVICES_TO_MONITOR:
        result = subprocess.run(
            ["systemctl", "is-active", service],
            capture_output=True, text=True
        )
        status = result.stdout.strip()
        if status != "active":
            msg = f"Service down: {service} (status: {status})"
            log_incident("critical", f"service.{service}", 0, msg)
            send_slack_alert("critical", msg)
            #Trigger auto-restart
            subprocess.run(["sudo", "bash", "restart.sh", service],)


def run_checks():
    print(f"\n--- Check run: {datetime.datetime.now(datetime.UTC).isoformat()}Z ---")
    check_cpu()
    check_memory()
    check_disks()
    check_services()

check_cpu()    

if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    run_checks()