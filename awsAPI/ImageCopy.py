# -*- coding=UTF-8 -*-
'''
Created on 2018年2月28日

@author: Administrator
'''
from awsAPI.awsInterface import API
# import boto3
import json
import logging
import logging.handlers
import time
import ConfigParser





LOG_SIZE = 100*1024*1024

# SELT handler output format 
mylogFormatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')

# create mylogger  
mylogger = logging.getLogger('a')  
mylogger.setLevel(logging.DEBUG)  
  
# create handler for FILE
mylogFileHandler = logging.handlers.RotatingFileHandler('getLog.log', mode='a', maxBytes=LOG_SIZE, backupCount=2, encoding=None, delay=0)
#logFileHandler.setLevel(logging.DEBUG)
mylogFileHandler.setFormatter(mylogFormatter) 
  
# create handler for STDOUT  
mylogStdoutHandler = logging.StreamHandler()
#logStdoutHandler.setLevel(logging.DEBUG)
mylogStdoutHandler.setFormatter(mylogFormatter) 
 
# add handlerto mylogger
mylogger.addHandler(mylogFileHandler)  
mylogger.addHandler(mylogStdoutHandler)  

def autheticate_key():
    cf = ConfigParser.ConfigParser()
    cf.read('aws_credentials')
    ACCESS_KEY = cf.get('aws', 'ACCESS_KEY')
    SECRET_KEY = cf.get('aws', 'SECRET_KEY')
    srcRegion = cf.get('aws', 'srcRegion')
    destRegion = cf.get('aws', 'destRegion')
    return ACCESS_KEY, SECRET_KEY, srcRegion, destRegion


def migrateImage(amiName, srcAmiID):
    '''
    Copy AMI (aw account 07) from Beijing  Region to NingXia region!
    '''
    ACCESS_KEY, SECRET_KEY, srcRegion, destRegion = autheticate_key()
    
    ec2 = API(ACCESS_KEY, SECRET_KEY, region=destRegion)
    client = ec2.session('ec2')
    mylogger.info('Beginning to Migrate %s to %s' %(amiName, destRegion))
    print amiName, srcAmiID
    try:
        response = client.copy_image(
                Name = amiName,
                SourceImageId = srcAmiID,
                SourceRegion = srcRegion,
                )
#         print response
    except Exception,e:
        mylogger.error('Got an Error: %s and response %s' %(e, response))
        return False, response['ImageId']
    
    while True:
        result = client.describe_images(
                                        Filters=[
                                        {
                                            'Name': 'name',
                                            'Values': [
                                                amiName,
                                                        ]
                                        },
                                                 ],
                                 )
#         print result
        if len(result['Images']) == 0:
            mylogger.info('Migrating is in progress...')
            time.sleep(60)
            continue
        elif result['Images'][0]['State'] == 'available':
            
            mylogger.info('%s (imageID: %s) is Mirgrated to %s successfully!!!' % (amiName, result['Images'][0]['ImageId'], destRegion))
            break
        else:
            time.sleep(60)    
            mylogger.info('Current image (imageID: %s) State is %s ...' %(result['Images'][0]['ImageId'],result['Images'][0]['State']))
            continue   
    return result['Images'][0]['ImageId']
    
def createImage(Instance_Name, Instance_ID):
    #create image for current running instances
    ACCESS_KEY, SECRET_KEY, srcRegion, destRegion = autheticate_key()
    ec2 = API(ACCESS_KEY, SECRET_KEY, srcRegion)
    client = ec2.session('ec2')
    amiList = list()
    label = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    
    mylogger.info('create AMI for %s and its instanceid is %s' % (Instance_Name, Instance_ID))
    response = client.create_image(
            Description='Image Created by %s' %label,
            DryRun=False,
            InstanceId=Instance_ID,
            Name=Instance_Name,
            NoReboot=True
                )
    serv ={'Image_Name': Instance_Name, 'Image_Id': response['ImageId']}
    amiList.append(serv)
    mylogger.info('Checking ImageID %s which name %s' %(response['ImageId'],Instance_Name))
    imageChecking(response['ImageId'])
        
    return amiList

def imageChecking(imageID):
    ACCESS_KEY, SECRET_KEY, srcRegion, destRegion = autheticate_key()
    ec2 = API(ACCESS_KEY, SECRET_KEY, srcRegion)
    client = ec2.session('ec2')
    while True:
        response = client.describe_images(
             ImageIds=[
                 imageID,
             ],
             DryRun=False
        )
        if response['Images'][0]['State'] == 'available':
            mylogger.info('image %s is AVAILABE!!' %imageID)
#             mylogger.info('Begin to ')
            break
        else:
            mylogger.info('Current State of %s is %s ...' %(imageID,response['Images'][0]['State']))
            time.sleep(60)
            continue
    return True

                
def getInstanceID(tag):
    ACCESS_KEY, SECRET_KEY, srcRegion, destRegion = autheticate_key()
    ec2 = API(ACCESS_KEY, SECRET_KEY, region=srcRegion)
    #function listInstance is list()
    client = ec2.listInstance()
    host = list()
    for i in client:
        serv = dict()
        if tag.lower() in i['ServerName'].lower():
            serv['Instance_Name'] = i['ServerName']
            serv['Instance_ID'] = i['InstanceID']
            host.append(serv)
    return host
#     print json.dumps(research, indent=2), json.dumps(cloudmcu, indent=2)
def main(tag):
    result = getInstanceID(tag)
    #result is list
#     print result
    amiList = createImage(result[0]['Instance_Name'], result[0]['Instance_ID'])
    mylogger.info('amiList %s' %amiList)
    migrateImage(amiList[0]['Image_Name'],amiList[0]['Image_Id'])
    
    
if __name__ == '__main__':
#     import sys
#     origin, tag = sys.argv
    main('KeepClose_Master_Default_wwchen1')
