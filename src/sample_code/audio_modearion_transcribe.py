import time
import boto3
import json
from botocore.exceptions import ClientError

def toxicity_detect(job_name,job_uri,data_bucket,output_prefix):

    toxicity_response = transcribe.start_transcription_job(
        TranscriptionJobName = job_name,
        Media = {
            'MediaFileUri': job_uri
        },
        OutputBucketName = data_bucket,
        OutputKey = output_prefix,
        LanguageCode = 'en-US',
        # based on your biz logic,modify to specific label like Profanity，Violence or threat and etc.
        ToxicityDetection = [
            {
                'ToxicityCategories': ['ALL']
            }
        ]
    )

    while True:
        status = transcribe.get_transcription_job(TranscriptionJobName = job_name)
        if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
            break
        #print("Not ready yet...")
        time.sleep(5)
    outputkey = f"{output_prefix}{job_name}.json"
    toxicity_json = s3.get_object(Bucket=data_bucket, Key=outputkey)

    json_data = json.loads(toxicity_json['Body'].read())
    print(json_data)
    audio_dect_result = {}

    if json_data['results']['toxicity_detection'][0]['toxicity'] > 0.8:
        audio_dect_result["toxicity"] = json_data['results']['toxicity_detection'][0]['toxicity']
        audio_dect_result["categories"] =json_data['results']['toxicity_detection'][0]['categories']
    else:
        pass

    return audio_dect_result

def main():

    audio_dect_result = toxicity_detect(job_name, job_uri, data_bucket,output_prefix)
    print(audio_dect_result)
    table_name = "audio_moderation"

    item = {
        'audiokey': s3_key,
        'toxicity result': audio_dect_result
    }
    try:
        table = dynamodb.Table(table_name)
        response = table.put_item(
            Item=item
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            # 创建表
            table = dynamodb.create_table(
                TableName=table_name,
                KeySchema=[
                    {'AttributeName': 'audiokey', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'audiokey', 'AttributeType': 'S'}
                ],
                ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            )
            # 等待表创建完成
            table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
            # 创建完成后,写入数据
            response = table.put_item(
                Item=item
            )

if __name__ == '__main__':

    s3 = boto3.client('s3',region_name='us-east-1')
    transcribe = boto3.client('transcribe', region_name='us-east-1')
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    data_bucket = "ml-aod"
    s3_key = 'content-moderation/audio_toxicity_detect/speech_polly.mp3'
    output_prefix = 'audio_toxicity_detect_output/'
    # upload local test data to s3
    s3.upload_file('../../test_data/speech_polly.mp3', data_bucket, s3_key)

    job_name = "modify-job-name-yourself"
    job_uri = f"s3://{data_bucket}/" + s3_key

    main()

