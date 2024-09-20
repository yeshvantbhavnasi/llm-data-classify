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
    typeOfPII: str = Field(description="All Types of PII detected", required=False, default="")
    infoTypes: str = Field(description="Info types detected", required=False, default="")
    extractedInfo: str = Field(description="PII extracted from input", required=False, default="")
    maskedPIIString: str = Field(description="Masked PII original string", required=False, default="")

# Prompt template
prompt = PromptTemplate.from_template("""
You are a helpful assistant that detects PII (personally identifiable information) in text and formatted json or csv file, make sure the response is always structured with PII fields. Make sure you generate the masked PII field in the string try to be as absure as possible.
Human: {question}
AI: """
)

# Chain for llama model
llm = OllamaFunctions(model="llama3.1", format="json", temperature=0)
structured_llm = llm.with_structured_output(PII)
llama_chain = prompt | structured_llm 

# Chain for DLP API
credentials_file = "/Users/ybhavnasi/keys/dev/autolog-control.json"

from google.cloud import storage 
import json

def list_files(bucket_name):
    """List all files in a GCS bucket."""
    credentials = service_account.Credentials.from_service_account_file(credentials_file)
    storage_client = storage.Client(project="box-dev-dp-autolog", credentials=credentials)
    bucket = storage_client.get_bucket(bucket_name)
    blobs = bucket.list_blobs()
    return [blob.name for blob in blobs]

def read_file_content(bucket_name, file_name):
    """Read the content of a GCS file."""
    credentials = service_account.Credentials.from_service_account_file(credentials_file)
    storage_client = storage.Client(project="box-dev-dp-autolog", credentials=credentials)
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(file_name)
    return blob.download_as_text()

def gcs_content_response(bucket_name): 
    bucket = bucket_name.split("gs://")[1]
    print(bucket)
    files = list_files(bucket)
    file_content = ""
    for file in files:
        file_content += read_file_content(bucket, file)
    dlp_result = dlp_scan_string(file_content)
    llama_result = llama_chain.invoke(file_content)
    return {"llama_response": llama_result, "dlp_response": dlp_result}


from google.cloud import bigquery
from google.oauth2 import service_account

def query_bigquery_table(project_id, dataset_id, table_id):
    """
    Queries a BigQuery table and prints the results.
    
    Args:
    project_id (str): GCP project ID.
    dataset_id (str): BigQuery dataset ID.
    table_id (str): BigQuery table ID.
    """
    # Create a BigQuery client
    credentials_file = ""
    credentials = service_account.Credentials.from_service_account_file(credentials_file)
    client = bigquery.Client(credentials=credentials)

    # Construct the SQL query
    query = f"""
    SELECT *
    FROM `{project_id}.{dataset_id}.{table_id}`
    LIMIT 1
    """

    # Execute the query
    query_job = client.query(query)

    # Process and print the results
    results = query_job.result()
    # Process and print the results as JSON rows
    rows = [dict(row) for row in results]
    # generate a json string
    json_string = json.dumps(rows)
    return json_string



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
    
    info_types = [{'name': 'PERSON_NAME'}, {'name': 'EMAIL_ADDRESS'}, {'name': 'PHONE_NUMBER'}, {'name': 'CREDIT_CARD_NUMBER'}, {'name': 'US_SOCIAL_SECURITY_NUMBER'}, {'name': 'DATE_OF_BIRTH'}, {'name': 'LOCATION'}, {'name': 'IP_ADDRESS'}, {'name': 'AGE'}, {'name': 'US_DRIVERS_LICENSE_NUMBER'}, {'name': 'PHONE_NUMBER'}]
    deidentify_inspect_config = {
        "info_types": info_types,
        "include_quote": True,
    }
    masking_config = {
        'character_mask_config': {
            'masking_character': '*',
            'number_to_mask': 0
        }
    }

    # Define the de-identify config
    deidentify_config = {
        'info_type_transformations': {
            'transformations': [{
                'primitive_transformation': {
                    'character_mask_config': masking_config['character_mask_config']
                }
            }]
        }
    }

    de_identify_config = {

    }
    masked_response = client.deidentify_content(
        request={"parent": parent, "deidentify_config": deidentify_config, 'inspect_config': deidentify_inspect_config, "item": item}
    )
    
    # Create a PII object
    pii = PII(
        isPII=False,
        typeOfPII="",
        infoTypes="",
        extractedInfo="",
        maskedPIIString=masked_response.item.value
    )
    # Update the PII object if there are findings
    if response.result.findings:
        for finding in response.result.findings:
            if finding.likelihood.name == "LIKELY" or finding.likelihood.name == "VERY_LIKELY" :
                pii.isPII = True
                pii.typeOfPII += finding.info_type.name + ", "
                pii.infoTypes += finding.info_type.name + ", "
                pii.extractedInfo += finding.quote + ", "
    return pii

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

class InputData(BaseModel):
    text: str
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Update to match your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"Hello": "World"}

# make an post api to accept the input data
@app.post("/pii")
def detect_pii(input_data: InputData):
    # Call the llama model
    input_text = input_data.text
    llama_response = llama_chain.invoke(input_text)
    print(llama_response)
    # Call the DLP API
    dlp_response = dlp_scan_string(input_text)
    print(dlp_response)
    return {"llama_response": llama_response, "dlp_response": dlp_response}

@app.post("/pii_gcs")
def detect_pii_gcs(input_data: InputData):
    print(input_data)
    bucket_name = input_data.text
    dlp_response = gcs_content_response(bucket_name)
    return dlp_response

@app.post("/pii_bq")
def detect_pii_bq(input_data: InputData):
    print(input_data)
    tables = input_data.text.split(".")
    if tables[0].startswith("bigquery://"):
        project_id = tables[0][11:]
    else :
        project_id = tables[0]
    dataset_id = tables[1]
    table_id = tables[2]
    bq_response = query_bigquery_table(project_id, dataset_id, table_id)
    
    
    dlp_response = dlp_scan_string(bq_response)
    llama_response = llama_chain.invoke(bq_response)
    return {"llama_response": llama_response, "dlp_response": dlp_response}
