"""
!/usr/bin/env python
   Prerequisites:
       pip intall boto3
   Author: Cosmin.Gavagiuc@gavagiuc.com
   Usage : python retention.py [AWS-profile-name1 AWS-profile-name2 AWS-profile-name3]
   Python script to generate a CSV report containing Number of snapshots for every instance volume
"""
import boto3
import os
import re
import time
from datetime import datetime, timedelta
import logging
from botocore.exceptions import ClientError
import tempfile
import sys
import string
from boto3.session import Session
from operator import itemgetter
import csv
import unicodedata

"""
Global Variable Declaration
"""
global VERSION
VERSION="1.0"
os.environ['AWS_DEFAULT_REGION'] = "eu-west-1"
timestr = time.strftime("%Y%m%d-%H%M%S")
logger = logging.getLogger()
logger.setLevel(logging.INFO)
now=datetime.utcnow()
nownaive = now.replace(tzinfo=None)

def get_snapshots(region):
    """
        List all EC2 snapshots owned by account in region.
        It is faster than querying aws each time.
        :return: global json dictionary list
    """
    client = boto_ec2_client(region)
    paginator = client.get_paginator('describe_snapshots')
    response_iterator = paginator.paginate(OwnerIds=[Account])
    snapshots = list()
    for page in response_iterator:
        for obj in page['Snapshots']:
            snapshots.append(obj)
    return(snapshots)

def get_volumes(InstanceId,region,VolumeID):
    """
        List all volumes from transmitted instance id // Counting Snapshots by Description
        :return: number of snaps and volume age in days
    """
    client = boto_ec2_client(region)
    paginator = client.get_paginator('describe_volumes')
    response_iterator = paginator.paginate(VolumeIds=[VolumeID])
    for page in response_iterator:
        for volume in page['Volumes']:
             # calculating volume age
             voldatenaive = volume['CreateTime'].replace(tzinfo=None)
        delta=nownaive-voldatenaive
        VolumeAge = delta.days
        # filtering snapshots by VolumeID
        FilteredSnapshots = [x for x in snapshots if x['VolumeId'] == volume['VolumeId']]
        return VolumeAge, len(FilteredSnapshots)

def get_ec2(region):
    """
        List all EC2 instances.
        :return: list of rows to be added in CVS
    """
    # Create EC2 client
    client = boto_ec2_client(region)
    paginator = client.get_paginator('describe_instances')
    response_iterator = paginator.paginate()
    row = list()
    for page in response_iterator:
        for obj in page['Reservations']:
            for Instance in obj['Instances']:
                InstanceName=None
                if Instance['State']['Name'] != 'terminated':
                    for tag in Instance['Tags']:
                        if tag["Key"] == 'Name':InstanceName = tag["Value"]
                print(InstanceName)
                for Volume in Instance['BlockDeviceMappings']:
                    VolumeAge, SnapshotsCount = get_volumes(Instance['InstanceId'],region,Volume['Ebs']['VolumeId'])
                    row.append({
                        'Region': region,
                        'InstanceName': InstanceName,
                        'VolumeID': Volume['Ebs']['VolumeId'],
                        'VolAge': VolumeAge,
                        'SnapshotCount': SnapshotsCount,
                        'AccountName': AccountName
                        })
    return row

def get_regions():
    """
        List all AWS region available
        :return: list of regions
    """
    client = boto3.client('ec2')
    regions = [region['RegionName'] for region in client.describe_regions()['Regions']]
    return regions

def log(level, message):
    if level == 1:
        level_str = 'INFO'
    elif level == 2:
        level_str = 'WARNING'
    elif level == 3:
        level_str = 'CRITICAL'
    print(str(__file__) + ' - ' + str(VERSION) + ' - <' + str(level_str) + '> - ' + str(message))

def boto_ec2_client(region):
    """
    Initiates boto resource to communicate with AWS API
    """
    ec2_client = boto3.client(
        'ec2',
        region_name = region
    )
    return ec2_client
def boto_client(role):
    """
    Initiates boto resource to communicate with AWS API
    """
    iam_client = boto3.client(
        role
    )
    return iam_client

def init():
    """
        Main init script
        :return: None
    """
    # Parsing the argument list from command line
    for arg in sys.argv[1:]:
        os.environ['AWS_PROFILE'] = arg
        global region_list
        region_list = get_regions()
        boto3.setup_default_session(profile_name=arg)
        # List Account ID and Alias
        global Account
        global AccountName
        Account = boto_client("sts").get_caller_identity()['Account']
        iam = boto_client("iam")
        paginator = iam.get_paginator('list_account_aliases')
        for response in paginator.paginate():
            AccountName = "\n".join(response['AccountAliases'])
            # Calling functions for every region
        print(AccountName)
        cvsrow = list()
        for region in region_list:
            global snapshots
            snapshots=get_snapshots(region)
            cvsrow.extend(get_ec2(region))
        if len(cvsrow):
            with open('retention-'+AccountName+'-'+timestr+'.csv', 'w') as csvfile:
                fieldnames = ['Region','InstanceName','VolumeID','VolAge','SnapshotCount','AccountName']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for item in cvsrow:
                    writer.writerow(item)
        else:
            print("No snapshots found on ", AccountName)

if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.WARNING)
    try:
        init()
    except ClientError as e:
        logger.error(e)
    except Exception as err:
        logger.error(err)
