### this python script deletes unused target groups based on the cloudwatch metric (request count). if the sum of the request count is zero for the previous week it will delete the LB rule 
### And delete the associated target group
### please note that this is used to delete target groups in the testing environment.

import boto3
from datetime import date, datetime, timedelta

def delete_load_balancer_rules_and_target_groups(load_balancer_name):
    elbv2 = boto3.client('elbv2')
    cw = boto3.client('cloudwatch')
    
    start_time = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%S')
    end_time = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    load_balancer = elbv2.describe_load_balancers(Names=[load_balancer_name])['LoadBalancers'][0]
    load_balancer_arn = load_balancer['LoadBalancerArn']
    listener_arn = 'arn:aws:elasticloadbalancing:eu-west-1:652586300051:listener/app/stage-infra-poc-internal/502f766dbe5b3419/5e980efdf194d774'
    loadbalancer_name_CW= '/'.join(load_balancer_arn.split('/')[1:])
    # Get all target groups associated with the load balancer
    response = elbv2.describe_target_groups(LoadBalancerArn=load_balancer_arn)
    target_group_arns = [tg['TargetGroupArn'] for tg in response['TargetGroups']]
    # Get the target group requests metric for each target group for the previous week
    for target_group_arn in target_group_arns:
        tg = target_group_arn.split(':')
        tg = tg[-1]
        
        metric = cw.get_metric_data(
                MetricDataQueries=[
                    {
                        "Id": "m1",
                        "MetricStat": {
                            "Metric": {
                                "Namespace": "AWS/ApplicationELB",
                                "MetricName": "RequestCount",
                                "Dimensions": [
                                    {
                                        "Name": "LoadBalancer",
                                        "Value": loadbalancer_name_CW
                                    },
                                    {
                                        "Name": "TargetGroup",
                                        "Value": tg
                                    }
                                ]
                            },
                            "Period": 86400,
                            "Stat": "Sum",
                            "Unit":'Count'
                        },
                        "ReturnData": True
                    }
                ],
                StartTime=start_time,
                EndTime=end_time
            )
        if 'MetricDataResults' in metric and len(metric["MetricDataResults"]) > 0:
            data = sum(metric["MetricDataResults"][0]["Values"])
            if data==0:
                
                
                response = elbv2.describe_rules(ListenerArn=listener_arn)
                rules = response['Rules']
                for rule in rules:
                    for action in rule['Actions']:
                        if action['Type'] == 'forward' and action['TargetGroupArn'] == target_group_arn:
                            rule_arn = rule['RuleArn']
                            break
    
                elbv2.delete_rule(RuleArn=rule_arn)
                elbv2.delete_target_group(TargetGroupArn=target_group_arn)
                
                
    

def lambda_handler(event, context):
    load_balancer_name = 'stage-infra-poc-internal' # Replace this with the name of your load balancer
    delete_load_balancer_rules_and_target_groups(load_balancer_name)
    
