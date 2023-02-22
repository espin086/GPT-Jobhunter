import boto3


def start_state_machine(region_name, arn):
    # create a boto3 client for Step Functions
    stepfunctions = boto3.client("stepfunctions", region_name=region_name)

    # start a new Step Function execution
    response = stepfunctions.start_execution(stateMachineArn=arn)

    # print the execution ARN to the console
    print(response["executionArn"])


if __name__ == "__main__":
    start_state_machine(
        region_name="us-west-1",
        arn="arn:aws:states:us-west-1:128472059203:stateMachine:linkedin-bot",
    )
