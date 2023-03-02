import boto3
import yaml


with open('../config.yaml') as f:
    data = yaml.load(f, Loader=yaml.FullLoader)
    
arn = data['dev']['step_function']
print(arn)
region = data['default']['region']



def start_state_machine(region_name, arn):
    # create a boto3 client for Step Functions
    stepfunctions = boto3.client("stepfunctions", region_name=region_name)

    # start a new Step Function execution
    response = stepfunctions.start_execution(stateMachineArn=arn)

    # print the execution ARN to the console
    print(response["executionArn"])


if __name__ == "__main__":
    start_state_machine(
        region_name=region,
        arn=arn,
    )
