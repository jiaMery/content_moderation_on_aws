import json
import logging
import boto3
import time
import random
import string
from easydict import EasyDict as edict
from langchain.llms.bedrock import Bedrock

rand_int = random.randint(0, 1000000) 
random_char = str(rand_int)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

mySession = boto3.session.Session()
awsRegion = mySession.region_name
rekognition = boto3.client('rekognition')
s3 = boto3.client('s3')
transcribe = boto3.client('transcribe')

image_file = ["jpg", "jpeg", "png"]
video_file = ["mp4", "mov"]
audio_file = ["amr", "flac", "mp3", "mp4", "ogg", "webm", "wav"]
text_file = ["txt"]

content_result = edict()


def comprehend_dect(text):
    comprehend_analysis_dict = edict()
    is_negative = False 
    negative_score = 0
    age = None

    comprehend = boto3.client(service_name='comprehend')
    # Detect language
    detect_language_result = comprehend.detect_dominant_language(Text=text)
    language_code = detect_language_result['Languages'][0]['LanguageCode']

    sentiment = comprehend.detect_sentiment(Text=text, LanguageCode= 'en')
    pii_entities = comprehend.detect_pii_entities(Text=text, LanguageCode='en')   
    comprehend_analysis_dict['Sentiment'] = sentiment['Sentiment']
    comprehend_analysis_dict['SentimentScore'] = sentiment['SentimentScore']
    comprehend_analysis_dict["PII"] = pii_entities
    return comprehend_analysis_dict


def bedrock_modration(text):
    
    bedrock = boto3.client(service_name="bedrock-runtime")   

    inference_modifier = {'max_tokens_to_sample':4096, 
                          "temperature":0.5,
                          "top_k":250,
                          "top_p":1,
                          "stop_sequences": ["\n\nHuman"]}

    textgen_llm = Bedrock(model_id = "anthropic.claude-v2",
                    client = bedrock, 
                    model_kwargs = inference_modifier )
    

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
    prompt_template = f"""
    The following is our company's content moderation policy, based on the moderation policy, we gather text information from the user uploaded text. Please answer the question with json format. 
            
    ###### moderation policy ######
    {moderation_policy}
            
    ###### text information ######
    {text}
            
    ###### Question ######
    Based on the following Moderation policy and QA, tell me if the text containes unsafe content, also give its category and reason. Please anwser the question with the following format and only put explanation into the reason field: 
    """

    prompt_template += """
    {
        "flag": "xxx",
        "category": "xxx",
        "reason": "the reason is ..."
    }
    """
    
    llm_response = textgen_llm(prompt_template)
    
    return llm_response



def image_moderation(bucketName, putObjectPathName):
    image = {'S3Object':{'Bucket':bucketName,'Name':putObjectPathName}}
    content_result["Image_moderation_lable"] = rekognition.detect_moderation_labels(Image=image)
    # Face Dection on Image
    content_result["Image_Face_analysis_lable"] = rekognition.detect_faces(Image=image,Attributes=['ALL'])
    # Rekognition celebrities on Image
    content_result["Image_Celebrities_lable"] = rekognition.recognize_celebrities(Image=image)
    # Extract Text from Image
    extra_text_results = rekognition.detect_text(Image=image)
    content_result["Extra_text_results"] = extra_text_results
    content_result["Text_from_Image"] = ""
    # logger.info(type(content_result["Text_from_Image"][0]['Confidence']))
    for text in extra_text_results["TextDetections"]:
        if text['Confidence'] >= 99:
            content_result["Text_from_Image"] += text['DetectedText']
    if "Text_from_Image" in content_result and len(content_result["Text_from_Image"])>0:
        content_result["ImageText_bedrock_lable"] = bedrock_modration(content_result["Text_from_Image"])
        content_result["ImageText_comprehend_lable"] = comprehend_dect(content_result["Text_from_Image"])
    # # Object Dection
    # content_result["Object_lable"] = rekognition.detect_labels(Image=image)

  
def Audio_moderation(bucketName, putObjectPathName, file_uri):
    
    transcribe_job_name = putObjectPathName.split("/")[-1] + random_char
    outputkey = putObjectPathName.split(".")[0] + random_char + ".json"
    
    transcribe.start_transcription_job(
        TranscriptionJobName = transcribe_job_name,
        Media = {
            'MediaFileUri': file_uri
        },
        OutputBucketName = bucketName,
        OutputKey = outputkey, 
        LanguageCode = 'en-US', 
        ToxicityDetection = [ 
            { 
                'ToxicityCategories': ['ALL']
            }
        ]
    )
    while True:
        status = transcribe.get_transcription_job(TranscriptionJobName = transcribe_job_name)
        if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
            break
    # Toxicity detection
    response = s3.get_object(Bucket=bucketName, Key=outputkey)
    json_data = edict(json.loads(response['Body'].read()))
    content_result["Toxicity_lable"] = json_data.results.toxicity_detection
    #Put the text content of audio file to Bedrock and Comprehend to get content moderaion results
    audio2text = json_data.results.toxicity_detection[0].text
    content_result["Audio2text_bedrock_lable"] = bedrock_modration(audio2text)
    content_result["Audio2text_comprehend_lable"] = comprehend_dect(audio2text)

    
def text_moderation(bucketName, putObjectPathName):
    # Read file
    file = s3.get_object(Bucket=bucketName, Key=putObjectPathName)
    text = file['Body'].read().decode('utf-8')
    # Content moderation 
    content_result["Text"] = text
    content_result["Text_Bedrock_lable"] = bedrock_modration(text)
    content_result["Text_comprehend_lable"] = comprehend_dect(text)

  
def lambda_handler(event, context):
    logger.info(event)
    logger.info('Put event handled successfully')
    
    # Get information from response
    bucketName = event["Records"][0]["s3"]["bucket"]["name"]
    putObjectPathName = event["Records"][0]["s3"]["object"]["key"]
    file_uri = "s3://" + bucketName + "/" + putObjectPathName
    content_result["file_uri"] = file_uri
    # Get object's type
    put_object_type = putObjectPathName.split(".")[-1]
    # Content Moderation
    if put_object_type in image_file:
        image_moderation(bucketName, putObjectPathName)
    if put_object_type in audio_file:
        Audio_moderation(bucketName, putObjectPathName, file_uri)
    if put_object_type in text_file:
        text_moderation(bucketName, putObjectPathName)
    else:
        logging.info("Invalid file type")
        
    logging.info(content_result)
    
    return {
        'statusCode': 200,
        'content_moderation_result': content_result
    }
    
