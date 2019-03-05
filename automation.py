import string
import random
import boto3
import datetime
from pprint import pprint

VpcId = ""
Subnet1 = ""
Subnet2 = ""
LoadBalancerNames = "automation-LB"
LaunchConfigurationName = "automation-LC"
AutoScalingGroupName = "automation-ASG"
InstanceType = "m3.medium"
KeyName = "GiGiProd"
ImageId = "ami-089fa199786190de3"
SecurityName = "AutoScaling-SG1"

userDataCode = """
#!/bin/bash
set -e -x
# Setting up the docker server 
sudo yum install -y docker
sudo service docker start
sudo chkconfig docker on
sudo docker run -p 80:80 --name nginx-cont -d nginx

"""

# # Create Security Group. 
ec2 = boto3.resource('ec2')

sec_group = ec2.create_security_group(
    GroupName=SecurityName, Description=SecurityName, VpcId=VpcId)
sec_group.authorize_ingress(
    CidrIp='0.0.0.0/0',
    IpProtocol='tcp',
    FromPort=80,
    ToPort=80
)

# Create ELB.
alb = boto3.client('elbv2')
alb_lb = alb.create_load_balancer(
    Name= LoadBalancerNames,
    Subnets=[
        'Subnet1', 
        'Subnet2',
    ],
    SecurityGroups=[ sec_group.id ],
    Scheme='internet-facing',
    Type='application'
)

#print alb_lb["LoadBalancers"][0]["LoadBalancerArn"]


alb_tg = alb.create_target_group(
    Name='autoscalingtargetgroup',
    Port=80,
    Protocol='HTTP',
    VpcId= VpcId
)

alb_listener = alb.create_listener(
    DefaultActions=[
        {
            'TargetGroupArn': alb_tg["TargetGroups"][0]["TargetGroupArn"],
            'Type': 'forward',
        },
    ],
    LoadBalancerArn= alb_lb["LoadBalancers"][0]["LoadBalancerArn"],
    Port=80,
    Protocol='HTTP',
)


# Create Launch Configuration. 
alc = boto3.client('autoscaling')
response = alc.create_launch_configuration(
    ImageId= ImageId,
    InstanceType= InstanceType,
    LaunchConfigurationName= LaunchConfigurationName,
    KeyName= KeyName,
    SecurityGroups=[ sec_group.id ],
    UserData=userDataCode
)

# Create AutoScaling Group. 
asg = alc.create_auto_scaling_group(
    AutoScalingGroupName= AutoScalingGroupName,
    HealthCheckGracePeriod=120,
    HealthCheckType='EC2',
    LaunchConfigurationName= LaunchConfigurationName,
    VPCZoneIdentifier='Subnet1, Subnet2',
    TargetGroupARNs=[
        alb_tg["TargetGroups"][0]["TargetGroupArn"],
    ],
    MaxSize=5,
    MinSize=1,
    DesiredCapacity=2,
)
