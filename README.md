# ec2-snapshot-report.py

Python script to generate a CSV report containing Number of snapshots for every instance volume.
Paginating tehnique has been used to make sure we receive all AWS resources.

[Download](https://github.com/gavagiuc/ec2-snapshot-report)

Generate report has the following table header:

| Region | InstanceName | VolumeID | VolAge | SnapshotCount | AccountName |
| ------------ | ------------ | ------------ | ------------ | ------------ | ------------ |

Prerequisites:
```
$ pip install  boto3
```
Run via Python:
```
$ python retention.py [AWS-profile-name1 AWS-profile-name2 AWS-profile-name3]