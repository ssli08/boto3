#coding=utf-8
'''
Created on 2017年12月14日

@author: Administrator
'''
import boto3
import json
import time
import datetime

  
  
class DateEncoder(json.JSONEncoder):  
    def default(self, obj):  
        if isinstance(obj, datetime.datetime):  
            return obj.strftime('%Y-%m-%d %H:%M:%S')  
        elif isinstance(obj, datetime.date):  
            return obj.strftime("%Y-%m-%d")  
        else:  
            return json.JSONEncoder.default(self, obj) 

class API(object):
    def __init__(self, key, secret, region):
        self.key = key
        self.secret = secret
        self.region = region
    def session(self):
        session = boto3.session.Session(self.key, self.secret, region_name=self.region)
        return session

    def volumes(self):
        client = self.session().client('ec2')
        response = client.describe_volumes(
            Filters=[
                {
                    'Name': 'attachment.status',
                    'Values': [
                        'attached',
                    ]
                },
            ],
    #         VolumeIds=[
    #             'string',
    #         ],
            DryRun=False,
            MaxResults=123,
    #         NextToken='test'
        )
        result = json.dumps(response['Volumes'],indent=2, cls=DateEncoder)
        print result
    #     print response['Volumes']

    def listInstance(self):
        '''
        Instances:[
             { 
                ImageId
                InstanceId
                IntanceType
                LanuchTime
                PrivateIpAddress
                PublicIpAddress
                State
                BlockDeviceMappings: []
                RootDeviceName
                RootDeviceType
                }
            ]
        '''
        client = self.session().client('ec2')
        hostList = list()
        result = client.describe_instances(
            Filters=[
                {    
                    'Name': 'instance-state-name',
                    'Values': [
#                                 'running',
                                'stopped'
                               ],
                },
                     ],
                                               )
        
        for instance in result['Reservations']:
#             host = dict()
            for k  in instance['Instances']:
                host = dict() 
#                 print json.dumps(k, indent=2, cls=DateEncoder)
#                 print k['Tags'][0]['Value']
                if k.has_key('PublicIpAddress'):   
                    host['PublicIP']=k['PublicIpAddress']
                else:
                    host['PublicIP']=''                           
                host['PrivateIP']=k['PrivateIpAddress']
                host['InstanceID']=k['InstanceId']
                host['LaunchTime']=k['LaunchTime']
                host['Device']=k['RootDeviceName']
                host['ServerName']=k['Tags'][0]['Value']
                host['Type']=k['InstanceType']   
                host['ImageID'] = k['ImageId']
                host['VolumeID'] = k['BlockDeviceMappings'][0]['Ebs']['VolumeId']
                host['State'] = k['State']['Name']               
                hostList.append(host)
#         output = json.dumps(hostList, indent=2, cls=DateEncoder)
#         print output
        return hostList
        
    #create instance
    def createInstances(self,imageID,instanceType,keyName, privateIP, subnetID, tagName):
#     boto3.set_stream_logger('botocore', level='DEBUG')
        client = self.session().client('ec2')
        response = client.run_instances(     
            ImageId=imageID,
            InstanceType=instanceType,
            KeyName=keyName, #eg, oregon region which key is oregon
            MaxCount=1,
            MinCount=1,
            NetworkInterfaces=[
            {
                'AssociatePublicIpAddress': True,
                'DeleteOnTermination': True,
                'Description': 'guest test',
                'DeviceIndex': 0,
                'Groups': [
                    'sg-52ee6c3b',
                ],
                'PrivateIpAddress': privateIP,
                'SubnetId': subnetID
            },
                               ],
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': tagName,
                        },
                    ],
                },
            ],  
            )
     
        state = response['Instances'][0]['State']['Name']
        print state
    
    def getSnapshot(self, args):
        client = self.session().client(args)
        response = client.describe_snapshots(
        DryRun=False
        )
        output = json.dumps(response['Snapshots'], indent=2, cls=DateEncoder)
        return output
    
    def runTimeFloat(self, timestr):
#         current = datetime.datetime.now()
        now = time.mktime(datetime.datetime.now().timetuple()) - 28800 #Beijing timezone translation
        lanchTime = time.mktime(time.strptime(timestr, '%Y-%m-%d %H:%M:%S'))
        result = (now - lanchTime)
        return result
    def upTime(self, args):
        result = self.instancesList(args)
        upTime = list()
        newUP = list()
        for i in result:
            para = dict()
            rt = self.runTimeFloat(str(i['LaunchTime'])[:-6])
            if rt/3600 > 240:  #run time more than 10 days
                para['runTime'] = rt/3600
                para['name'] = i['ServerName']
                upTime.append(para)
            else:
                para['runTime'] = rt/3600
                para['name'] = i['ServerName']
                newUP.append(para)
#                 print 'Nothing to be done!'
#                 pass
#         print 'RunTime more than 10 days list is %s' % upTime
#         print 'Just start up instances list %s' % newUP
        print  json.dumps(sorted(upTime, key=lambda s: s['runTime'], reverse=True),indent=2)   
    #带时区的时间格式转换
    def timeTransform(self, timeStr):
        timezone = timeStr[-6:]
        t = datetime.datetime.strptime(timeStr[:-6], "%Y-%m-%d %H:%M:%S")
        t = t - datetime.timedelta(minutes=int(timezone[0]+str(int(timezone[1:3])*60+int(timezone[4:6]))))
        return time.mktime(t.timetuple())
    
    def createTag(self, args, resourceID, tag):
        client = self.session().client(args)
        try:
            response = client.create_tags(
                DryRun=False,
                Resources=[
                    resourceID
                ],
                Tags=[
                    {
                        'Key': 'Name',
                        'Value': tag
                    },
                ]
                )
        except Exception,e:
            return e, False 
        return response
    #boto3 for aws network virtual private cloud
    def createVPC(self, args, cidr, tag):
        client = self.session().client(args)
        out = client.describe_vpcs(
            Filters=[
                {
                    'Name': 'cidr',
                    'Values': [
                        cidr,
                    ]
                },
                     ],
                                   )
#         print json.dumps(out,indent=2)
        if not out['Vpcs']:
            try:
                vpc = client.create_vpc(
                            CidrBlock=cidr,
#                                     AmazonProvidedIpv6CidrBlock=True|False,
                            DryRun=False,
                            InstanceTenancy='default'
                )
            except Exception,e:
                return e,False
            vpcid = vpc['Vpc']['VpcId']
            self.createTag(args, vpcid, tag)

            return  vpcid
        else:
#             print json.dumps(out,indent=2)
            vpcid = out['Vpcs'][0]['VpcId']
            self.createTag(args, vpcid, tag)
            return vpcid
    

#         print('vpc %s create') % vpc['Vpc']['VpcId']
    def createSubnet(self, args, subnet, cidr):
        client = self.session().client(args)
        try:
            #create subnet with vpc id
            response = client.create_subnet(
    #             AvailabilityZone='string',
                CidrBlock=subnet,
    #             Ipv6CidrBlock='string',
                VpcId=self.vpc_create(args, cidr),
                DryRun=False
            )
        except Exception,e:
            return False, e
        return response
        
    def attachRoute(self,args, cidr, tag):
        client = self.session().client(args)
        vpcid = self.vpc_create(args, cidr, tag)
        response = client.describe_route_tables(
            Filters=[
                {
                    'Name': 'vpc-id',
                    'Values': [
                        vpcid,
                    ]
                },
            ],
             )
        routeTableID = response['RouteTables'][0]['Associations'][0]['RouteTableId']
        out = client.describe_internet_gateways(
                Filters=[
                    {
                        'Name': 'attachment.vpc-id',
                        'Values': [
                            vpcid,
                        ]
                    },
                ],
            )
        igwID = out['InternetGateways'][0]['InternetGatewayId']
        
        if not igwID:
            gateway = client.create_internet_gateway()
            igw = gateway['InternetGateway']['InternetGatewayId']
            
            client.attach_internet_gateway(
                        InternetGatewayId=igw,
                        VpcId= vpcid
                        )
            
            response = client.create_route(
                DestinationCidrBlock='0.0.0.0/0',
                GatewayId=igw,
                RouteTableId=routeTableID,
                )
            return response
        else:
            print('%s already attached %s') %(igwID, vpcid)
    #ELB Describe
    def getELB(self, args, elbName):
        client = self.session().client(args)
        response = client.describe_load_balancers(
        LoadBalancerNames=[
            elbName,
        ],
#         Marker='string',
#         PageSize=123
        )
        print json.dumps(response, indent=2, cls=DateEncoder)
    def ELBPolicySetting(self,elbName,port,policy_name='Custom-TCP-ProxyProtocol-Policy', args='elb'):
        client = self.session().client(args)                                                        

        policy_result = client.create_load_balancer_policy(
                            LoadBalancerName=elbName,
                            PolicyName=policy_name,
                            PolicyTypeName='ProxyProtocolPolicyType',
                            PolicyAttributes=[
                                {
                                    'AttributeName': 'ProxyProtocol',
                                    'AttributeValue': 'true'
                                },
                            ]
                        )
# #         print json.dumps(response, indent = 2)
        status = policy_result['ResponseMetadata']['HTTPStatusCode']
        if status == 200:
            result = client.set_load_balancer_policies_for_backend_server(
                                                                LoadBalancerName=elbName,
                                                                InstancePort=port,
                                                                PolicyNames=[
                                                                             policy_name,
                                                                             ]
                                                                )
            print result
        else:
#             print 'error'
            result = client.describe_load_balancers(
                                                  LoadBalancerNames=[
                                                                     elbName,
                                                                     ],                                            
                                                  )
            print json.dumps(result, indent=2, cls=DateEncoder)


