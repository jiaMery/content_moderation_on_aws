from langchain.llms.bedrock import Bedrock
from langchain import PromptTemplate
import boto3

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
    prompt = PromptTemplate(
        input_variables=["npc_descrpition"], 
        template="""
        Human:
        You are a well-trained language model for detecting inappropriate content in text. 
        Here is a paragraph {npc_descrpition}. 
        Your task is to critically review if the above paragraph suitable for children under 14 years old.
        For example,content not good for chilrens include but not limited to:profanity, hate speech, uncivil words, violent, explicit sexual or illegal. If yes, answer me with True and then select the <degree> about the degree of harm:
        low,medium, high. If no, answer me with False, give me <degree> with None. Whatever give me explanation of your assessment. Answer format as follows:
        '''
        result:"True or False"
        degree of harm:"<degree>,or None "
        '''
        Assistant:""")
    prompt = prompt.format(npc_descrpition=text)
    response = textgen_llm(prompt)
    text = response[response.index('\n')+1:]
    
    lines = text.splitlines()

    is_inappropriate = lines[2]    
    degree_of_harm = lines[3]
    
    return is_inappropriate,degree_of_harm