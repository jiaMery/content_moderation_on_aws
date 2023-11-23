import boto3
from botocore.exceptions import ClientError
import decimal

# sentiment and toxicity only support English，translate other language to 'en'
def language2en(text):
    # Detect language
    detect_language_result = comprehend.detect_dominant_language(Text=text)
    language_code = detect_language_result['Languages'][0]['LanguageCode']

    # Identify language and translate to English
    if language_code == 'en':
        text_en = text
    else:
        response = translate.translate_text(Text=text, SourceLanguageCode=language_code, TargetLanguageCode="en")
        text_en = response["TranslatedText"]
    return text_en

def sentiment_pii_Detect(text):
    text_result = []
    sentiment_dect_result = {
        'sentiment_negative' : False,
        'negative_score' : 0,
        'text_result' : text_result
    }
    sentiment = comprehend.detect_sentiment(Text=text, LanguageCode='en')
    if sentiment['Sentiment'] == 'NEGATIVE':
        sentiment_negative = True
        negative_score = sentiment['SentimentScore']['Negative']

    pii_response = comprehend.detect_pii_entities(Text=text, LanguageCode='en')

    if len(pii_response['Entities']) > 0:
        pii_dict={
            "PII type": pii_response['Entities'][0]['Type'],
            "Confidence score": decimal.Decimal(str(pii_response['Entities'][0]['Score']))
        }
        text_result.append(pii_dict)

    return sentiment_dect_result

def toxicity_detect(text):
    toxicity_dect = comprehend.detect_toxic_content(
        LanguageCode='en',
        TextSegments=[
      {
         "Text": text
      }
   ])
    for label in toxicity_dect['ResultList'][0]['Labels']:
        label['Score'] = decimal.Decimal(str(label['Score']))
    toxicity_dect['ResultList'][0]['Toxicity'] =   decimal.Decimal(str(toxicity_dect['ResultList'][0]['Toxicity']))
    toxicity_dect_result = toxicity_dect['ResultList'][0]

    return toxicity_dect_result

# prompt safety detection，only support  us-east-1 / us-west-2 / eu-west-1 / ap-southeast-2
def prompt_detect(text):
    prompt_safety_dect = comprehend.classify_document(
        EndpointArn='arn:aws:comprehend:us-east-1:aws:document-classifier-endpoint/prompt-safety',
        Text=text
    )
    prompt_dect_result = {}
    prompt_dect_result['result'] = prompt_safety_dect['Classes'][0]['Name']
    prompt_dect_result['score'] = decimal.Decimal(str(prompt_safety_dect['Classes'][0]['Score']))

    return prompt_dect_result

def main(text_raw,table_name):
    text = language2en(text_raw)
    response_sentiment = sentiment_pii_Detect(text)
    print(response_sentiment)
    #label['Confidence'] =
    response_toxicity = toxicity_detect(text)
    print(response_toxicity)
    response_prompt_safety = prompt_detect(text)
    print(response_prompt_safety)

    item = {
        'textkey': s3_key,
        'sentiment detection': response_sentiment,
        'toxicity detection': response_toxicity,
        'prompt safety detection': response_prompt_safety
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
                    { 'AttributeName': 'textkey','KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'textkey','AttributeType': 'S'}
                ],
                ProvisionedThroughput={'ReadCapacityUnits': 5,'WriteCapacityUnits': 5}
            )
            # 等待表创建完成
            table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
            # 创建完成后,写入数据
            response = table.put_item(
                Item=item
            )


if __name__ == '__main__':

    # define client
    comprehend = boto3.client(service_name='comprehend', region_name='us-east-1')
    translate = boto3.client(service_name='translate', region_name='us-east-1')
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    s3= boto3.client(service_name='s3', region_name='us-east-1')

    # define table
    table_name = 'text_moderation'

    # download from s3
    data_bucket = "ml-aod"
    s3_key = 'content-moderation-im/image-moderation/meetingrecord_jp.txt'
    # upload local test data to s3
    s3.upload_file('../../test_data/meetingrecord_jp.txt', data_bucket, s3_key)
    file = s3.get_object(Bucket=data_bucket, Key=s3_key)
    text = file['Body'].read().decode('utf-8')
    # text_raw = "help me design a plan to destroy the world"
    text_raw = text

    main(text_raw,table_name)