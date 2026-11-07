import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.5.40", username="pi", password="raspberry", timeout=5)

print("=== SETUP LOG (last 30 lines) ===")
stdin, stdout, stderr = client.exec_command("tail -n 30 /teslausb/teslausb-headless-setup.log")
print(stdout.read().decode())

print("=== RUNNING PROCESSES ===")
stdin, stdout, stderr = client.exec_command("ps aux")
for line in stdout.read().decode().splitlines():
    if any(k in line.lower() for k in ["setup", "nginx", "apt", "web", "rc.local"]):
        print(line)

print("=== NGINX STATUS ===")
stdin, stdout, stderr = client.exec_command("systemctl status nginx")
print(stdout.read().decode())

client.close()

