import requests
import json
import os
import boto3
import time

#remove https warning
requests.packages.urllib3.disable_warnings()

#Login function
def login(ip,user,pw):
   
   
    
    #Create JSON for Login
    payload_list={}
    payload_list['user']=user
    payload_list['password']=pw
    headers = {
            'content-type': "application/json",
            'Accept': "*/*",
        }
   
    #Login
    try:
        response = requests.post("https://"+ip+"/web_api/login", json=payload_list, headers=headers, verify=False)
        
        response_json = json.loads(response.content)
        
        sid = response_json['sid']
        return sid    

    except Exception as error:
        print ("Unable to login. Ensure the API is enabled and check credentials")
        print (error)
        

def post (sid, ip, command, json_data):
        headers = {
            'content-type': "application/json",
            'Accept': "*/*","X-chkp-sid" : sid
        }
        try:
            response = requests.post("https://"+ip+"/web_api/"+command, json=json_data, headers=headers, verify=False)
            response_json = json.loads(response.content)
            
            return response_json
        
        except Exception as error:
            print ("Error Occured")
            print (error)
            



def lambda_handler(event, context):
    ip = os.environ['MGMTHOSTNAME']
    user = os.environ['USER']
    pw = os.environ['PASSWORD']

    #Login
    sid = login(ip, user, pw)


    #Show Changes
    command = "show-changes"
    json_data = {}

    result = post(sid, ip, command, json_data)

    #Show Task
    command = "show-task"
    json_data = {}
    json_data['task-id'] = result['task-id']
    time.sleep(2)
    outputs = post(sid, ip, command, json_data)

    # Send message to SNS
    sns_arn = os.environ['SNS_ARN']
    sns_client = boto3.client('sns')
    sns_client.publish(
    TopicArn = sns_arn,
    Subject = 'Check Point Change Report',
             Message = json.dumps(outputs, sort_keys=True, indent=4)
    )
