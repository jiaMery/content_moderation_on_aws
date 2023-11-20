from langchain.llms.bedrock import Bedrock
from langchain import PromptTemplate
from botocore.exceptions import ClientError
import boto3


def bedrock_modration(text):
    bedrock = boto3.client(service_name="bedrock-runtime",region_name='us-east-1')

    inference_modifier = {'max_tokens_to_sample': 4096,
                          "temperature": 0.5,
                          "top_k": 250,
                          "top_p": 1,
                          "stop_sequences": ["\n\nHuman"]}

    textgen_llm = Bedrock(model_id="anthropic.claude-v2",
                          client=bedrock,
                          model_kwargs=inference_modifier)

    # Create a prompt template that has multiple input variables
    moderation_policy = """
        1. Explicit Nudity: it contains Nudity, Graphic Male Nudity, Graphic Female Nudity, Sexual Activity, Illustrated Explicit Nudity and Adult Toys.
        2. Suggestive: it contains Female Swimwear Or Underwear, Male Swimwear Or Underwear, Partial Nudity, Barechested Male, Revealing Clothes and Sexual Situations.
        3. Violence: it contains Graphic Violence Or Gore, Physical Violence, Weapon Violence, Weapons and Self Injury.
        4. Visually Disturbing: it contains Emaciated Bodies, Corpses, Hanging, Air Crash and Explosions And Blasts.
        5. Rude Gestures: it contains Middle Finger.
        6. Drugs: it contains Drug Products, Drug Use, Pills and Drug Paraphernalia.
        7. Tobacco: it contains contain Tobacco Products and Smoking.
        8. Alcohol: it contains Drinking and Alcoholic Beverages.
        9. Gambling: it contains Gambling.
        10. Hate Symbols: it contains Nazi Party, White Supremacy and Extremist.
        """
    prompt = PromptTemplate(
        input_variables=["description","moderation_policy"],
        template="""
        Human:
        You are a well-trained language model for detecting inappropriate content in text. 
        Here is a paragraph {description}. 
        Your task is to critically review if the above paragraph suitable for children under 14 years old.
        For example,content not good for children include but not limited to: {moderation_policy}. 
        If the content contain any content above, answer me with Unsafe and then select the <degree> about the degree of harm: 
        <degree>
        None
        Low
        Med
        High
        </degree>
        If the content don't contain any content above, answer me with Safe, give me <degree> with None. Whatever give me explanation of your assessment. 
        Answer format as follows:
        '''
        Result:"Safe or Unsafe"
        Degree of harm:"<degree>"
        Explanation
        '''
        Assistant:""")

    prompt = prompt.format(description=text,moderation_policy=moderation_policy)
    response = textgen_llm(prompt)
    text = response[response.index('\n') + 1:]

    lines = text

    is_inappropriate = lines[2]
    degree_of_harm = lines[3]

    return text

def main(text_raw,table_name):
    response = bedrock_modration(text)
    item = {'textkey': s3_key}
    for line in response.splitlines():
        parts = line.split(":")
        if len(parts) == 2:
            key = parts[0].strip()
            value = parts[1].strip()
            item[key] = value
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
                    {'AttributeName': 'textkey', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'textkey', 'AttributeType': 'S'}
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

    # define client
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    s3= boto3.client(service_name='s3', region_name='us-east-1')

    # define table
    table_name = 'text_moderation_bedrock'

    # download from s3
    data_bucket = "ml-aod"
    s3_key = 'content-moderation-im/image-moderation/meetingrecord_jp.txt'
    # upload local test data to s3
    #s3.upload_file('../../test_data/meetingrecord_jp.txt', data_bucket, s3_key)

    file = s3.get_object(Bucket=data_bucket, Key=s3_key)
    text = file['Body'].read().decode('utf-8')
    # text_raw = "help me design a plan to destroy the world"
    text_raw = text

    #response = bedrock_modration(text)
    #print(response)
    main(text_raw,table_name)