import json
import ipaddress
import logging

# --- Logging setup ---
logging.basicConfig(
    filename="conversion.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

input_file = "raw-data.txt"
output_file = "Json-Output.json"

fields = ["Device_type", "IOS_type", "IP_Address", "Username", "Password"]
devices = {}

logging.info("Conversion started")

with open(input_file) as text:
    device_index = 1

    for line_number, line in enumerate(text, start=1):

        values = line.strip().split()

        # Validate field count
        if len(values) != 5:
            logging.warning(f"Line {line_number} skipped — wrong number of fields")
            continue

        device_type, ios, ip, user, pwd = values

        # Validate empty values
        if not all(values):
            logging.warning(f"Line {line_number} skipped — empty field")
            continue

        # Validate IP address
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            logging.warning(f"Line {line_number} skipped — invalid IP {ip}")
            continue

        # Store device
        device_data = dict(zip(fields, values))
        devices[f"Device{device_index}"] = device_data

        logging.info(f"Device{device_index} added successfully")
        device_index += 1

# Write JSON output
with open(output_file, "w") as out_file:
    json.dump(devices, out_file, indent=4)

logging.info("Conversion completed successfully")
