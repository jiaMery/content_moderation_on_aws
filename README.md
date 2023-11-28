 # Multi-Modal Intelligent Content Moderation

This repository contains the implementation of the Multi-Modal Intelligent Content Review based on AWS AI services. For detailed deployment steps and additional information, please refer to our [blog post](https://aws.amazon.com/cn/blogs/china/multi-modal-intelligent-content-review-based-on-aws-ai-services/) on AWS.

## Architecture Overview

![Architecture Diagram](./document/SolutionArchitecture.jpg)

## Deployment Steps
If testing via lambda, the steps are roughly:

1. Environment setup: Create S3 bucket, IAM role and BedRock policy

2. Create and configure Lambda function  

3. Import Lambda code and deploy Lambda function

4. Upload files to S3 bucket, check test results


If integrating the functionality into your own environment, you can refer to the sample code:

1. Environment setup: Create S3 bucket, IAM role and BedRock policy

2. Create and run corresponding python functions

3. View auditing results in DynamoDB

For more details and insights, please visit our [blog post](https://aws.amazon.com/cn/blogs/china/multi-modal-intelligent-content-review-based-on-aws-ai-services/).

## File Description
- src/lambda_func contains complete lambda code, sample_code contains python code for auditing different data types

- test_data and test_results are the test data and results used in the experiment


## Reference Documents
- Rekognition for image content moderation: https://aws.amazon.com/rekognition/content-moderation/

- Comprehend for text content moderation: https://docs.aws.amazon.com/comprehend/latest/dg/trust-safety.html

- Transcribe for audio content moderation: https://docs.aws.amazon.com/transcribe/latest/dg/toxicity.html 

- Bedrock documentation: https://docs.aws.amazon.com/bedrock/latest

## Disclaimer

It is recommended to use this solution for testing purposes. Please evaluate thoroughly before using it in production environments.
You are welcome to contact us for collaborating on the solution and submitting requirements. You can also leave feedback in the GitHub project issues.


