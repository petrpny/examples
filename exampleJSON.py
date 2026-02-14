import json

devices ={
  "routers": [
    {
      "hostname": "RouterA",
      "interfaces": {
        "GigabitEthernet0": {
          "status": "up",
          "address": {
            "ipv4": "10.3.11.1",
            "mask": "255.255.255.0"
          }
        },
        "GigabitEthernet1": {
          "status": "administratively down",
          "address": {
            "ipv4": "10.3.12.1",
            "mask": "255.255.255.0"
          }
        }
      }
    }
  ]
}

# print(devices)

print(devices["routers"][0]['interfaces']['GigabitEthernet0']['address']['mask'])