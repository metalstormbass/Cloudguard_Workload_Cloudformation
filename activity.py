import requests
from threading import Thread

#remove https warning
requests.packages.urllib3.disable_warnings()

def post(target):
   payload_list={}
   headers = {
            'content-type': "application/json",
            'Accept': "*/*",
        }
   response = requests.post(target, json=payload_list, headers=headers, verify=False)
   print (response)

#Input target
target = input("Target:")

for x in range(1, 1000):
   post(target)
