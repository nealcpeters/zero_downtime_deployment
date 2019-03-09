import sys
import boto3

ec2 = boto3.client('ec2')
elb = boto3.client('elb')

def find_instances_by_ami(ami):
	instances_using_ami = ec2.describe_instances(Filters=[{'Name': 'image-id','Values': [ami]},{'Name': 'instance-state-name','Values': ['running','pending']}])
	return instances_using_ami

def filter_instance_info(ami):
	existing_ec2_info = []
	for reservation in (find_instances_by_ami(ami)["Reservations"]):
		for instance in reservation["Instances"]:
			instance_info = {
				'instance_id': instance["InstanceId"],
				'subnet_id': instance["SubnetId"],
				'instance_type': instance["InstanceType"]
			}

			security_groups = []
			for security_group in instance["SecurityGroups"]:
				security_groups.append(security_group["GroupId"])

			instance_info.update({'security_groups': security_groups})
			existing_ec2_info.append(instance_info)

	return existing_ec2_info

# assumes three instances
def find_load_balancer_name(instance_one, instance_two, instance_three):
	load_balancers = elb.describe_load_balancers()
	for load_balancer in load_balancers['LoadBalancerDescriptions']:
		for instance in load_balancer['Instances']:
			if instance_one and instance_two and instance_three in instance.values():
				load_balancer_name = load_balancer['LoadBalancerName']

	try:
	  load_balancer_name
	except NameError:
	  print("No load balancer could be found that matched three running instances with old AMI")
	else:
		return load_balancer_name

def launch_ec2_instance(image_id, instance_type, security_group_ids, subnet_id):
	ec2.run_instances(
		ImageId=image_id,
		InstanceType=instance_type,
		MaxCount=1,
		MinCount=1,
		SecurityGroupIds=security_group_ids,
		SubnetId=subnet_id,
		TagSpecifications=[
			{
				'ResourceType': 'instance',
				'Tags': [
					{
						'Key': 'Name',
						'Value': 'HAL-9000'
					},
				]
			},
		],
	)

def register_instance_with_load_balancer(load_balancer_name, instance_id):
	elb.register_instances_with_load_balancer(
		LoadBalancerName=load_balancer_name,
		Instances=[
			{
				'InstanceId': instance_id
			},
		]
	)

def ensure_connection_draining_is_enabled_on_load_balancer(load_balancer_name):
	elb.modify_load_balancer_attributes(
		LoadBalancerName=load_balancer_name,
		LoadBalancerAttributes={
			'ConnectionDraining': {
				'Enabled': True,
				'Timeout': 300
			}
		}
	)

def deregister_instance_with_load_balancer(load_balancer_name, instance_id):
	elb.deregister_instances_from_load_balancer(
		LoadBalancerName=load_balancer_name,
		Instances=[
			{
				'InstanceId': instance_id
			},
		]
	)

def deploy():
	old_ami = sys.argv[1:][0]
	new_ami = sys.argv[1:][1]

	print("Beginning zero downtime deployment, replacing old AMI ID " + old_ami + " with new AMI ID " + new_ami)

	old_instances = filter_instance_info(old_ami)
	load_balancer_name = find_load_balancer_name(old_instances[0]['instance_id'], old_instances[1]['instance_id'], old_instances[2]['instance_id'])

	print("Launching EC2 Instances")

	for instance in old_instances:
		print("launching...")
		launch_ec2_instance(new_ami, instance['instance_type'], instance['security_groups'], instance['subnet_id'])

	new_instances = filter_instance_info(new_ami)

	print("Registering new instances with load balancer...")

	for instance in new_instances:
		register_instance_with_load_balancer(load_balancer_name, instance['instance_id'])

	print("Ensuring connection draining is enabled on load balancer...")

	ensure_connection_draining_is_enabled_on_load_balancer(load_balancer_name)

	print("Deregistering old instances from load balancer...")

	for instance in old_instances:
		deregister_instance_with_load_balancer(load_balancer_name, instance['instance_id'])

	print("Complete!")

deploy()