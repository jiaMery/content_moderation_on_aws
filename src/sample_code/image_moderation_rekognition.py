'''
use Amazon Rekognition and Amazon Comprehend to quickly identify unsafe/inappropriate content in your image libraries
'''
import boto3
import decimal
import requests
import os

# modify with your own bucket name and region
region = "us-east-1"
data_bucket = "ml-aod"

os.environ["BUCKET"] = data_bucket
os.environ["REGION"] = region

# define client
s3 = boto3.client('s3', region_name=region)
rekognition = boto3.client('rekognition', region_name=region)
comprehend = boto3.client('comprehend', region_name=region)
dynamodb = boto3.resource('dynamodb', region_name=region)

# modify with your own dynamodb table or create a new table
table = dynamodb.Table('image_moderation')
'''
table_name = 'YourTableName'
table_key = 'YourPrimaryKey'

table_params = {
    'TableName' : table_name,
    'KeySchema': [ 
        { 'AttributeName': table_key, 'KeyType': 'HASH' }
    ],
    'AttributeDefinitions': [
        { 'AttributeName': table_key, 'AttributeType': 'S' }
    ],
    'ProvisionedThroughput': {
        'ReadCapacityUnits': 5,
        'WriteCapacityUnits': 5
    }
}
table = dynamodb.create_table(**table_params) 
'''

# sample image
s3_key = 'content-moderation-im/image-moderation/yoga_swimwear_lighttext.jpg'
# upload local test data to s3
# s3.upload_file('../../test_data/yoga_swimwear_lighttext.jpg', data_bucket, s3_key)

image= { 'S3Object': {'Bucket': data_bucket,'Name': s3_key}}

# also you can download image from url
'''
image_url = 'https://images.xxx.com/photos/xxx.'
response = requests.get(image_url)
image_bytes = response.content

image={'Bytes': image_bytes}
'''

# image moderation
#image_moderation_lab = rekognition.detect_moderation_labels(Image={'Bytes': image_bytes},MinConfidence=60)
image_moderation_lab = rekognition.detect_moderation_labels(
    Image= image,
    MinConfidence=60
)

for label in image_moderation_lab['ModerationLabels']:
    label['Confidence'] = decimal.Decimal(str(label['Confidence']))

# based on your business logic to define result
if not image_moderation_lab["ModerationLabels"]:
  item = {
    's3key': s3_key,
    'label': image_moderation_lab,
    'result': 'Pass',
  }
else:
    item = {'s3key': s3_key,
            'label': image_moderation_lab,
            'result': 'Human review',
        }

# face detect
face_lab = rekognition.detect_faces(
    Image=image,
    Attributes=['ALL']
)
# parse age information
for face in face_lab['FaceDetails']:
    low_age = face['AgeRange']['Low']
    high_age = face['AgeRange']['High']
item ['age'] = low_age


# dect the text in image
detectText = rekognition.detect_text(
    Image= image
)

# parse the text
detected_text_list = []
textfromDetections = detectText['TextDetections']
for text in textfromDetections:
    if text['Type'] == 'LINE':
        detected_text_list.append(text['DetectedText'])

text_result = []
for text in detected_text_list:
    pii_response = comprehend.detect_pii_entities(Text=text, LanguageCode='en')
    if len(pii_response['Entities']) > 0:
        pii_dict = {
            "PII type": pii_response['Entities'][0]['Type'],
            "Confidence score": decimal.Decimal(str(pii_response['Entities'][0]['Score']))
        }
        text_result.append(pii_dict)

item ['detected_text_list'] = detected_text_list
item ['detected_text_result'] = text_result
# print(item)

table.put_item(
    Item=item
)
