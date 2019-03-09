Do you have a classic elastic load balancer serving traffic to an application comprised of three EC2 instances on AWS? Well here is your chance to deploy new ones to the same load balancer and experience zero down time.

Disclaimer: The only way this works is if you have three EC2 instances using the same AMI behind a classic load balancer and no other instances exist using the same AMI.

Dependencies:
 ```
 python3
 boto3
 aws account with necessary access keys configured locally
 classic load balancer with three registered ec2 instances of the same ami
 ```

How to run:
  ```
  $ python deploy.py old_ami new_ami
  ```