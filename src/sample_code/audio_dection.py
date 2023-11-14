from __future__ import print_function
import time
import boto3
import json
from easydict import EasyDict as edict
s3 = boto3.client('s3')
transcribe = boto3.client('transcribe', 'us-east-1')
job_name = "my-first-job"
job_uri = "s3://Buket-name/speech_polly.mp3"
bucketName = 'Buket-name'
out = transcribe.start_transcription_job(
    TranscriptionJobName = job_name,
    Media = {
        'MediaFileUri': job_uri
    },
    OutputBucketName = bucketName,
    OutputKey = 'content_moderation_test_data/', 
    LanguageCode = 'en-US', 
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
    print("Not ready yet...")
    time.sleep(5)
print(type(out))
print(out)
print(status)