## An automated storage solution for YouTube Reporting data on the cheap

In this tutorial, we'll walk through the steps to set up an AWS Lambda function to retrieve and process YouTube reports using the YouTube Reporting API. We'll then store the processed data in DynamoDB and perform local analysis.

## Prerequisites
Before we begin, make sure you have the following:

- An AWS account with appropriate permissions to create Lambda functions and DynamoDB tables.
- You need to have the AWS CLI installed.
- Python installed on your local machine.
- Basic knowledge of AWS Lambda, DynamoDB, and Python programming.
- A [Google Cloud](https://console.cloud.google.com/) Project with enabled YouTube Reporting API and OAuth Credentials for that project.

## Step 1: Set up the DynamoDB Tables
In the notebook [setup_dynamodb.ipynb](setup_dynamodb.ipynb) I am creating four tables which correspond to tables from the YouTube Reporting API I am interested in, a table named `reports` which logs which reports have been processed, as well as some mapping tables which correspond to all [categorical dimensions which are expressed as numbers](https://developers.google.com/youtube/reporting/v1/reports/dimensions) in the YouTube Reporting API.
Feel free to adjust the code to your needs.

## Step 2: Set Up the Lambda Function
1. In [IAM](https://us-east-1.console.aws.amazon.com/iam/home?region=us-east-1), create a new Service Role for your Lambda function, containing the policies `AWSLambdaBasicExecutionRole`, `AmazonDynamoDBFullAccess` and `SecretsManagerReadWrite`.
2. Create a new [Lambda](https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1) function in the AWS Management Console and assign this IAM role to it.
3. Configure the function to use the appropriate runtime, which is Python 3.12.
4. In order for the function to work you will need to package [lambda_function.py](lambda_function.py) along with its dependencies in a .zip file. These dependencies need to be provided for the Linux runtime used by AWS Lambda.
    1. Create a new subfolder for the dependencies.
    2. In a terminal, activate the current virtual environment to make sure you are using Python 3.12. `conda activate ./venv`
    3. Now install the requirements for the Lambda file using pip with additional parameters to specify the Linux platform and put them in the newly created target subfolder. `pip install -r requirements_lambda.txt --platform manylinux2014_x86_64 --target /path/to/target/directory --upgrade`.
    4. Copy [lambda_function.py](lambda_function.py) in the target directory, navigate there and create a zip file with all the contents.
    5. Since the Google packages are large, the zip file will be larger than what is allowed for upload in the console. What worked for me is the upload to an [S3](https://s3.console.aws.amazon.com/s3/home?region=us-east-1) bucket and then upload the code from there, but maybe the CLI method could work for you. For more information see the [AWS documentation](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html#python-package-create-update).
5. Since the authentication to the YouTube Reporting API requires OAuth, this needs to be handled with the [AWS Secrets Manager](https://us-east-1.console.aws.amazon.com/secretsmanager/home?region=us-east-1). Store the contents of the client_secrets.json file under a secret named `Youtube-API` and the contents of the retrieved credentials as `YouTubeTokenInfo` (you can use `credentials.to_json()` in the [setup notebook](setup_dynamodb.ipynb) to obtain the string). These names are what is currently used within [lambda_function.py](lambda_function.py). In case you want to use different names for the secrets, adjust also the code.
6. Adjust the timeout and memory settings of the Lambda function as needed. Especially in the beginning with historical reports created you might want to give the function some time. I currently have it set to 10 minutes. The default 3 seconds are definitely too short, especially taking into account that the function might wait some times if it gets too close to the default quota limit of 60 requests per minute.
7. Test the function.
8. If it works, set up a daily rule under [Amazon EventBridge](https://eu-central-1.console.aws.amazon.com/events/home?region=eu-central-1). Note that the day in the reports is defined as a 24-hour period in US Pacific Time (PT), so set the time zone accordingly and schedule the event maybe for 1-2am in the morning to trigger the Lambda function. I provided a payload similar to the example provided in the Lambda Test menu, but an empty dictionary might also work.  

## Step 3: Analyze locally
Use the boto3 package to retrieve your stored data for your YouTube channels into Python and analyze on your computer.
An example can be found in [analyze_dynamodb.ipynb](analyze_dynamodb.ipynb).

## Conclusion
Congratulations! You've successfully set up an AWS Lambda function to process YouTube reports, stored the data in DynamoDB, and performed local analysis. You can now automate this process further, integrate with other AWS services, or scale your solution as needed.

## Outlook
One could further enhance the process by regularly exporting data from DynamoDB to S3 in order to query the data using SQL with Amazon Athena. But given that the amount of data will increase only slowly this should be enough for now.