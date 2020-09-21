#Runscript for Cloudguard Serverless Demo

import boto3
import requests
import getpass
import json
import string
import time
from random import *
from requests.auth import HTTPBasicAuth
from base64 import b64encode
from nacl import encoding, public

#Encryption for Github Secrets

def encrypt(public_key: str, secret_value: str) -> str:
    """Encrypt a Unicode string using the public key."""
    public_key = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return b64encode(encrypted).decode("utf-8")


#Prompt User for information
#Dome9
dome9_api_key = input('Dome9 API Key: ')
dome9_api_secret =getpass.getpass('Dome9 Secret Key: ')

#AWS
access_key = input('AWS Access Key: ')
aws_secret_key = getpass.getpass('AWS Secret Key: ')
aws_account_name =input('Friendly name of AWS account for Dome9: ')
region = "us-east-1"
bucket_name = input('Name of S3 Bucket to create: ') #"mikedevopsbucket"

#Gather Policy Name
read_policy = 'dome9-readonly-policy'
write_policy = 'dome9-write-policy'

#Dome9 API
url = "https://api.dome9.com/v2/CloudAccounts"

#Create IAM client for AWS
iam=boto3.client('iam', aws_access_key_id=access_key,
    aws_secret_access_key=aws_secret_key,)

#Create IAM Policies

#Create Dome9 read only policy
dome9_readonly_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "Dome9ReadOnly",
            "Action": [
                "cloudtrail:LookupEvents",
                "dynamodb:DescribeTable",
                "elasticfilesystem:Describe*",
                "elasticache:ListTagsForResource",
                "es:ListTags",
                "firehose:Describe*",
                "firehose:List*",
                "guardduty:Get*",
                "guardduty:List*",
                "kinesis:List*",
                "kinesis:Describe*",
                "kinesisvideo:Describe*",
                "kinesisvideo:List*",
                "logs:Describe*",
                "logs:Get*",
                "logs:FilterLogEvents",
                "lambda:List*",
                "s3:List*",
                "sns:ListSubscriptions",
                "sns:ListSubscriptionsByTopic",
                "sns:ListTagsForResource",
                "waf-regional:ListResourcesForWebACL",
                "eks:ListNodegroups",
                "eks:DescribeNodegroup"
            ],
            "Effect": "Allow",
            "Resource": "*"
        }
    ]
}

try:
    response = iam.create_policy(
      PolicyName=read_policy,
      PolicyDocument=json.dumps(dome9_readonly_policy)
    )

    print (response)
except Exception:
    print ('dome9-readonly-policy already exists!')
    pass

#Create Dome9 write policy

dome9_write_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "Dome9Write",
            "Action": [
                "ec2:AuthorizeSecurityGroupEgress",
                "ec2:AuthorizeSecurityGroupIngress",
                "ec2:CreateSecurityGroup",
                "ec2:DeleteSecurityGroup",
                "ec2:RevokeSecurityGroupEgress",
                "ec2:RevokeSecurityGroupIngress",
                "ec2:ModifyNetworkInterfaceAttribute",
                "ec2:CreateTags",
                "ec2:DeleteTags"
            ],
            "Effect": "Allow",
            "Resource": "*"
        }
    ]
}

try:
    response = iam.create_policy(
      PolicyName=write_policy,
      PolicyDocument=json.dumps(dome9_write_policy)
    )
    
except Exception:
    print ('dome9-write-policy already exists!')
    pass




#Create Dome9 Role in AWS

#Generate External ID
extid = ''.join(choice(string.ascii_letters + string.digits) for _ in range(24))

#Role Information
path='/'
role_name = 'Dome9-Connect'
description='Dome9 Permissions Role'

#Trust Policy for Dome9 JSON to variables
trust_policy={
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::634729597623:root"
      },
      "Action": "sts:AssumeRole",
      "Condition": {"StringEquals": {"sts:ExternalId":extid}}
    }
  ]
}

tags=[
    {
        'Key': 'Environment',
        'Value': 'Production'
    }
]

#Create Initial Role or update external ID if exists
try:
    response = iam.create_role(
            Path=path,
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=description,
            MaxSessionDuration=3600,

     )

    
except Exception:
    print ('Dome9-Connect role already exists! Please delete role and try again')
  
    
    
#Add AWS Managed Policies
aws_policy_list = ['arn:aws:iam::aws:policy/SecurityAudit','arn:aws:iam::aws:policy/AmazonInspectorReadOnlyAccess']

for arn in aws_policy_list:
    response=iam.attach_role_policy(
        PolicyArn=arn,
        RoleName=role_name
    )                  

#Get ARN for Dome9 policies

policy_name_list = [read_policy, write_policy]


#Parse JSON to grab Arn Prefix

response = iam.get_role(
    RoleName=role_name
)


arn_prefix_tmp = response['Role']['Arn']
arn_prefix_tmp=arn_prefix_tmp.split(':')
arn_prefix_tmp=[':'.join(arn_prefix_tmp[0:5])]
arn_prefix=arn_prefix_tmp[0]



#Loop through list to Apply Access Policies to the newly created role
for x in policy_name_list:
    policy_arn = arn_prefix +':policy/'+ x
    response=iam.attach_role_policy(
        PolicyArn=policy_arn,
        RoleName=role_name
    )
    
role_arn = arn_prefix+':role/'+role_name


#Give AWS Time to process commands
print ("working . . . ")
time.sleep(20)

#Attach Account to Dome9

json_data = {"name": aws_account_name, "credentials": {"arn":role_arn, "secret": extid, "type": "RoleBased", "isReadOnly": "false"}, "fullProtection": "false", "magellan": "true", "lambdaScanner": "true",
  "serverless": {
    "codeAnalyzerEnabled": "true",
    "codeDependencyAnalyzerEnabled": "true"
  } }

headers = {'content-type': 'application/json'}

print (json_data)
response = requests.post(url, auth=HTTPBasicAuth(dome9_api_key, dome9_api_secret), json=json_data, headers=headers)

print (response.content)

#Create Bucket
s3_client = boto3.client('s3', aws_access_key_id=access_key,
    aws_secret_access_key=aws_secret_key,)
s3_client.create_bucket(Bucket=bucket_name)


 #Upload File
s3_client.upload_file('./package.zip', bucket_name, 'package.zip', ExtraArgs={'ACL': 'public-read'})


