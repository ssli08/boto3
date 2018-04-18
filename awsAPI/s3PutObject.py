#coding=utf-8

import boto3
# import json
import argparse
import os
import sys
import threading
from botocore.client import Config
import datetime
import time
import json

import logging
import logging.handlers
 
ERROR_LOG_SIZE = 100*1024*1024
 
# SELT handler output format 
logFormatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
 
# create logger  
logger = logging.getLogger('s3PutObject')  
logger.setLevel(logging.DEBUG)  
   
# create handler for FILE
logFileHandler = logging.handlers.RotatingFileHandler('c:\error.log', 
                    mode='a', maxBytes=ERROR_LOG_SIZE, backupCount=2, encoding=None, delay=0)
#logFileHandler.setLevel(logging.DEBUG)
logFileHandler.setFormatter(logFormatter) 
   
# create handler for STDOUT  
logStdoutHandler = logging.StreamHandler()
#logStdoutHandler.setLevel(logging.DEBUG)
logStdoutHandler.setFormatter(logFormatter) 
  
# add handlerto logger
logger.addHandler(logFileHandler)  
logger.addHandler(logStdoutHandler) 

class ProgressPercentage(object):
    '''显示传输进度并添加提示'''
    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()
    def __call__(self, bytes_amount):
        # To simplify we'll assume this is hooked up
        # to a single filename.
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            sys.stdout.write(
                "\r%s  %s / %s  (%.2f%%)" % (
                    self._filename, self._seen_so_far, self._size,
                    percentage))
            sys.stdout.flush()
        
                    
def token(ACCESS_KEY,SECRET_KEY,region):
    session = boto3.session.Session(
                    region_name = region,
                    aws_access_key_id=ACCESS_KEY,
                    aws_secret_access_key=SECRET_KEY
                    )
    return session
       
def createBucket(session,bucket,region,lifetime):
    s3 = session.client('s3')
    response = s3.list_buckets()
    buckets = [bucketer['Name'] for bucketer in response['Buckets']]
#     return buckets
    if bucket not in buckets:
        try:
            result = s3.create_bucket(
                #     ACL='private'|'public-read'|'public-read-write'|'authenticated-read',
                    ACL='authenticated-read',
                    Bucket=bucket,
                    CreateBucketConfiguration={
                        'LocationConstraint': region
                    },

                    )
            setLifeCycleforBucket(session,bucket,lifetime)
            return bucket
        except Exception,e:
#             print e,'create bucket %s failed!' % bucket
            logger.error('create bucket failed, %s'% e)
            return False
    else:
        ttl = getLifeCycleforBucket(session, bucket)
        if ttl:
            logger.info('current bucket %s lifecycle is %s' %(bucket, ttl))
        else:
            logger.info('NO lifecycle settings for %s' % bucket)
        return bucket
        
def setLifeCycleforBucket(session,bucket,lifetime):
    '''bucket object lifecycle defintiion''' 
    s3 = session.client('s3')
    try:
        response = s3.put_bucket_lifecycle(
                Bucket=bucket,
                LifecycleConfiguration={
                    'Rules': [
                        {
                            'Expiration': {
                                'Days': lifetime,
                                        },
                            'ID': 'Log Expiration Definition',
                            'Prefix': '',
                            'Status': 'Enabled',                 
                        },
                              ]         
                                        }
                                           )
        return response
    except Exception,e:
        logger.error('failed to setup %s lifecycle, %s' %(bucket, e))

    
def getLifeCycleforBucket(session,bucket):
    "get bucket lifecycle"
    s3 = session.client('s3')
    try:
        response = s3.get_bucket_lifecycle(
                                           Bucket=bucket
                                           )
#         print response
        lifeTime = response['Rules'][0]['Expiration']['Days']
        return lifeTime
    except Exception,e:
        logger.error('Getting bucket %s lifetime failed, %s' %(bucket, e))
        return False

def uploadFile(session,bucket,directory,filename,region):
    '''generate  url for the uploaded file and create directory'''
    s3 = session.client('s3',config=Config(signature_version='s3v4'))
    while True:
        if os.path.isfile(filename):
            try:
                s3.upload_file(filename,bucket,'%s/%s' % (directory,filename),Callback = ProgressPercentage(filename))
                logger.info('%s upload sucessfully at %s!' % (filename, time.asctime()))
                break
            except Exception,e:
                logger.error('fail to upload, %s' %e)
                return False
        else:
            logger.error('%s not exist!' %filename)
            return False
    
    #Generate down links for upload file!!
    try:
        url = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': bucket,
                'Key': '%s/%s' % (directory,filename)
                    }
                                    )
        logger.info('File links below:\n%s' %url)
#         print "%s upload successfully at %s, the links from which you can download below:\n%s" % (filename, ,url)
    except Exception,e:
        logger.error('failed to generate url for %s, %s' %(filename, e))
#     return url
def fileProcess(filepath):
    logger.info('Pack logfile %s' %filepath)
    tarName = filepath.split('/')[-1] + '.' + 'tar.gz'
    cmd = 'tar zcPf %s %s' %(tarName, filepath)
    try:
        os.system(cmd)
        #pass
    except Exception,e:
        logger.error(e)
        return False
    if os.path.getsize(tarName) > 0:
        return tarName
    else:
        logger.error('Empty file %s' %tarName)
        return False
def get_bucket_policy(session,bucket):
    client = session.client('s3')
#     result = client.list_buckets()
    response = client.get_bucket_cors(
                                      Bucket=bucket
                                      )
    print json.dumps(response, indent=2)
def outputProcess(content):
    '''
                格式：\033[显示方式;前景色;背景色m
             
            说明：
            前景色            背景色           颜色
            ---------------------------------------
            30                40              黑色
            31                41              红色
            32                42              绿色
            33                43              黃色
            34                44              蓝色
            35                45              紫红色
            36                46              青蓝色
            37                47              白色
            显示方式           意义
            -------------------------
            0                终端默认设置
            1                高亮显示
            4                使用下划线
            5                闪烁
            7                反白显示
            8                不可见
             
            例子：
            #
            \033[1;32;40m    <!-- \033[ 表示开始颜色设置 1-高亮显示 32-前景色绿色  40-背景色黑色-->
            \033[0m          <!-- \033[0m 结束颜色设置-->

    '''
    print '\033[1;32;40m'
    print content         # 背景黑色，前景绿色，高亮输出hello， world! 
    print '\033[0m'
#     return True
def main():
    import ConfigParser
    cf = ConfigParser.ConfigParser()
    cf.read('aws_credentials')
    ACCESS_KEY = cf.get('aws', 'ACCESS_KEY')
    SECRET_KEY = cf.get('aws', 'SECRET_KEY')
    region = cf.get('aws', 'srcRegion')
    
    session = token(ACCESS_KEY, SECRET_KEY, region)
    if bucket:
    #"create the specified bucket"
        createBucket(session, bucket, region,lifetime)
    else:
        raise 'Error'
      
    if filename:
        uploadFile(session, bucket, directory, filename,region)

#     get_bucket_policy(session, 'gwn-cloud')

if __name__ == '__main__':
    import socket
    parser = argparse.ArgumentParser(description='create bucket & directorory & upload file')
    parser.add_argument('-B', dest='bucketname', type=str,
                        help='create s3 bucket')
#     parser.add_argument('-D', dest='directory', type=str,
#                         help='directory in bucket')
    parser.add_argument('-F', dest='filename', type=str,
                        help='file to upload the bucket.')
    parser.add_argument('-L',dest='lifetime',type=int,
                        help='put lifecycle for bucket')
    args = parser.parse_args()
         
    bucket = args.bucketname
#     directory = args.directory
    directory = socket.gethostname()
    filename = fileProcess(args.filename)
    lifetime = args.lifetime

    main()    
    

    
  

