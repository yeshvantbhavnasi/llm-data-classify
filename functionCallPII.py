from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_experimental.llms.ollama_functions import OllamaFunctions
from google.cloud import dlp_v2
from google.cloud.dlp_v2 import types 
from google.oauth2 import service_account

# Schema for structured response
class PII(BaseModel):
    """ Structured response for PII detection """
    isPII: bool = Field(description="PII detected yes or not ", required=False, default=False)
    typeOfPII: str = Field(description="Type of PII detected", required=False, default="")
    extractedInfo: str = Field(description="PII extracted from input", required=False, default="")

# Prompt template
prompt = PromptTemplate.from_template("""
You are a helpful assistant that detects PII (personally identifiable information) in text.                                    
Human: {question}
AI: """
)

# Chain for llama model
llm = OllamaFunctions(model="llama3.1", format="json", temperature=0)
structured_llm = llm.with_structured_output(PII)
llama_chain = prompt | structured_llm 

# Chain for DLP API
credentials_file = ""
def dlp_scan_string(string): 
    # Instantiate a client
    # pass the credentials to the client
    credentials = service_account.Credentials.from_service_account_file(credentials_file)
    client = dlp_v2.DlpServiceClient(credentials=credentials)
    # The string to inspect
    # string = 'My name is John Doe and my email address is
    parent = f"projects/box-dev-dp-autolog"
    item = {"value": string}
    inspect_config = {
        "info_types": [],
        "include_quote": True,
    }
    response = client.inspect_content(
        request={"parent": parent, "inspect_config": inspect_config, "item": item}
    )
    # Create a PII object
    pii = PII(
        isPII=False,
        typeOfPII="",
        extractedInfo=""
    )
    # Update the PII object if there are findings
    if response.result.findings:
        for finding in response.result.findings:
            if finding.likelihood.name == "LIKELY" or finding.likelihood.name == "VERY_LIKELY" :
                pii.isPII = True
                pii.typeOfPII += finding.info_type.name + ", "
                pii.extractedInfo += finding.quote + ", "
    return pii

def export_results(inputs):
    for input_data in inputs:
        print("Scanning with Llama model:")
        response = llama_chain.invoke(input_data)
        print(response)
        print("Scanning with DLP API:")
        dlp_scan_string(input_data)

# inputs = [
#     "My name is John Doe",
#     "I live at 123 Main Street, New York, NY.",
#     "My social security number is 123-45-6789.",
#     "My credit card number is 1234-5678-9012-3456.",
#     "Driving license number: 123456789."
#     "My phone number is 123-456-7890.",
#     "The quick brown fox jumps over the lazy dog. In a faraway land, a gentle breeze rustled through the leaves of ancient trees, whispering tales of old. The sky was painted in hues of orange and pink as the sun set behind the mountains. Birds chirped softly, signaling the end of another peaceful day. Meanwhile, in the bustling city, the aroma of freshly baked bread filled the air as people hurried along the crowded streets. Children laughed and played in the park, their carefree spirits a contrast to the busy world around them. The evening brought a calm that settled over the town, wrapping it in a comforting embrace.",
#     "simplicity is key to best hackathon projects",
#     "hey this is me ",
#     "hey this is a user playing around at office",
# ]

# export_results(inputs)
