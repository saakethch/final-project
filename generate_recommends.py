import requests
import os
import json
from io import BytesIO
from PIL import Image
import openai
import time
from snowflake.snowpark.session import Session

# Function to download and save image locally
def download_image(image_url, save_folder):
    response = requests.get(image_url)
    image = Image.open(BytesIO(response.content))
    # os.mkdir(save_folder)
    file_path = os.path.join(save_folder, 'image.jpg')
    image.save(file_path)
    print("Image Downloaded")
    return file_path

# Function to call API and get caption
def get_caption_snowpark(image_path):
    # Connect Snowpark  
    import json
    connection_parameters = json.load(open('connection.json'))
    session = Session.builder.configs(connection_parameters).create()
    
    # Upload file to Snowpark
    session.file.put("./images/image.jpg",'@dash_models',overwrite=True,auto_compress=False)
    session.add_packages(["transformers","Pillow"])
    print("Uploaded Image")
    # Import Model & Image to Snowpark    
    directory = '../model/'
    for filename in os.listdir(directory):
        f = os.path.join(directory, filename)
        if os.path.isfile(f):
            session.add_import('@dash_models/'+filename)
    session.add_import('@dash_models/image.jpg')
    print("Imported Image")
    # Call Model with UDF
    predicted_label = session.sql('''SELECT image_caption_generator()''').collect()
    generated_caption = predicted_label[0][0]
    print("Generated Captions - ", generated_caption)
    return generated_caption

# Function to extract nouns from caption
def extract_nouns(caption):
    extracted_nouns = []
    try:
        response = openai.Completion.create(
          prompt=f"Extract nouns from the following caption: '{caption}', Result Intructions : give a single string seperated by commas, type nothing else.",
          max_tokens=1024,
          n=1,
          engine = "text-davinci-003",
          stop=None
        )
        caption = response['choices'][0]['text']
        print("Extracted Nouns - "+ nouns)
        extracted_nouns = caption.strip().split(',')
    except Exception as e:
        print(f"Error extracting nouns: {e}")
    return extracted_nouns,caption

# Function to get product recommendations based on nouns
def get_product_recommendations(nouns,caption):
    # Call API to get product recommendations based on nouns
    # Replace <API_KEY> with your actual API key
    concatinated_noun_str = {'nouns': ','.join(nouns)}
    emotion_recognition = "it is very important for you to understand the emotion of this line: " + caption

    prompt_instructions = f"Now Give some potential market product recommendations for the following items or the emotion you recognized: '{concatinated_noun_str}'"
    result_instructions = ", Result Intructions : give a single string seperated by commas, type nothing else."
    product_recommendations = []
    try:
        response = openai.Completion.create(
          prompt= emotion_recognition + prompt_instructions + result_instructions,
          engine = "text-davinci-003",
          max_tokens=1024,
          n=1,
          stop=None
        )
        product_recommendations = response['choices'][0]['text']
        print("Generated Recommends - "+ product_recommendations)
        product_recommendations = product_recommendations.strip().split(',')
    except Exception as e:
        print(f"Error extracting nouns: {e}")
    return product_recommendations


# Main function to download image, get caption, extract nouns, and get product recommendations
def generate_recommends(image_url):
    save_folder = 'images'
    image_path = download_image(image_url, save_folder)
    caption = get_caption_snowpark(image_path)
    nouns,caption = extract_nouns(caption)
    product_recommendations = get_product_recommendations(nouns,caption)
    os.remove(image_path)
    return product_recommendations

# Example usage
api_key = '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'
openai.api_key = api_key
# image_url = 'https://plus.unsplash.com/premium_photo-1676158159495-6b8448629412?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=774&q=80'
image_url = 'https://plus.unsplash.com/premium_photo-1682175064711-2e2870132d9c?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=1740&q=80'
product_recommendations = generate_recommends(image_url)
print(product_recommendations)
