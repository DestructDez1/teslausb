import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.5.40", username="pi", password="raspberry", timeout=5)

print("=== SYSTEM HEALTH & UPTIME ===")
stdin, stdout, stderr = client.exec_command("uptime; free -m")
print(stdout.read().decode())

print("=== SERVICES STATUS ===")
stdin, stdout, stderr = client.exec_command("systemctl is-active nginx autofs")
print(stdout.read().decode())

print("=== RUNNING DAEMONS ===")
stdin, stdout, stderr = client.exec_command("ps aux")
for line in stdout.read().decode().splitlines():
    if any(k in line.lower() for k in ["archiveloop", "cttseraser", "nginx", "hostapd", "dnsmasq"]):
        print(line)

print("=== ROOT & STORAGE MOUNTS ===")
stdin, stdout, stderr = client.exec_command("mount")
for line in stdout.read().decode().splitlines():
    if any(k in line.lower() for k in ["mmcblk", "cttseraser", "teslacam"]):
        print(line)

client.close()
