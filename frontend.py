
# Imports
import streamlit as st
import streamlit.components.v1 as components
import requests
from bs4 import BeautifulSoup
from snowflake.snowpark.session import Session
import json
import uuid
import base64
from PIL import Image
import os
from io import BytesIO
from PIL import Image
import openai
import time
from textblob import TextBlob
import itertools
import io

# Environment connections
connection_parameters = json.load(open('connection.json'))
session = Session.builder.configs(connection_parameters).create()
api_key = st.secrets["OPEN_AI_API"]
openai.api_key = api_key
amzn_api_key = "5EB311E772024A59BB861F16A6DC7B67"
api_url = 'https://4t6zjqbvra77cljo42ody4xtmi0smplq.lambda-url.us-east-1.on.aws/'

# Local variables
progress_bar = st.progress(0)
interests = []
posts = []
ad_links = []
user_exists = False
usern = ""
likes = []
st.session_state['start_idx'] = 0
st.session_state['end_idx'] = 5
st.session_state['ads'] = []
# Download image function

if 'not_uploaded' not in st.session_state:
    st.session_state.not_uploaded = False



def download_image(image_url, save_folder):
    response = requests.get(image_url)
    image = Image.open(BytesIO(response.content)).convert('RGB')
    # os.mkdir(save_folder)
    file_path = os.path.join(save_folder, 'image.jpg')
    image.save(file_path)
    print("Image Downloaded to local")
    return file_path

# Get caption -> caption string
def get_caption_snowpark(image_path):
    
    session.file.put("image.jpg", '@dash_models',
                     overwrite=True, auto_compress=False)
    session.add_packages(["transformers", "Pillow"])
    print("Uploaded Image to Snowflake")
    # Import Model & Image to Snowpark
    directory = ['config.json',
                 'events.out.tfevents.1633443513.t1v-n-bb5dfd23-w-0.8655.0.v2',
                 'flax_model.msgpack',
                 'jaxlib-0.4.7+cuda11.cudnn86-cp39-cp39-manylinux2014_x86_64.whl',
                 'jaxlib-0.4.7-cp311-cp311-manylinux2014_x86_64.whl',
                 'preprocessor_config.json',
                 'pytorch_model.bin',
                 'special_tokens_map (1).json',
                 'special_tokens_map.json',
                 'tokenizer.json',
                 'tokenizer_config.json',
                 'vocab.json']
    progress_bar.progress(40)
    for filename in directory:
        session.add_import('@dash_models/'+filename)
    session.add_import('@dash_models/image.jpg')
    print("Imported Image into Snowflake model")
    print("Running model")
    # Call Model with UDF
    progress_bar.progress(50)
    predicted_label = session.sql(
        '''SELECT image_caption_generator()''').collect()
    generated_caption = predicted_label[0][0]
    print("Generated Caption - ", generated_caption)
    progress_bar.progress(70)
    return generated_caption

# Nouns extract -> nouns list


def extract_nouns(caption):
    text = caption
    blob = TextBlob(text)
    nouns = [w for (w, pos) in blob.pos_tags if pos[0] == 'N']
    print("Extracted nouns", nouns)
    return nouns, caption

# Product recommendations extract -> recommends list


def get_product_recommendations(nouns, caption):
    concatinated_noun_str = {'nouns': ','.join(nouns)}
    emotion_recognition = caption
    prompt_instructions = f"Now Give some potential market product recommendations for the following items or the emotion you recognized: '{concatinated_noun_str}'"
    result_instructions = ", Result Intructions : give a single string seperated by commas, type nothing else."
    product_recommendations = []
    response = openai.Completion.create(
        prompt=emotion_recognition + prompt_instructions + result_instructions,
        engine="text-davinci-003",
        max_tokens=1024,
        n=1,
        stop=None
    )
    product_recommendations = response['choices'][0]['text']
    product_recommendations = product_recommendations.strip().split(',')
    print("Generated Recommends - ", product_recommendations)
    return product_recommendations

# Function connector -> nouns list , caption string , product_recommendations list


def generate_recommends(image_url):
    save_folder = 'images'
    image_path = 'image.jpg' #download_image(image_url, save_folder)
    caption = get_caption_snowpark(image_path)
    nouns, caption = extract_nouns(caption)
    product_recommendations = get_product_recommendations(nouns, caption)
    os.remove(image_path)
    return nouns, caption, product_recommendations


# Function to extract Product Title
# Ad generate -> ads list on product recommends

# set up the request parameters

# Amazon Scrapping

def find_product_by_search_keyword(search_term):
    params = {
        'api_key': amzn_api_key,
        'type': 'search',
        'amazon_domain': 'amazon.com',
        'search_term': search_term,
        'sort_by': 'price_low_to_high',
        'page': 1
    }
    api_result = requests.get('https://api.rainforestapi.com/request', params)
    return json.dumps(api_result.json())

# Ad generate -> ads list on product recommends


def get_product_ads(products):
    output_ads = []
    ctr = 0
    ix = 0
    # Loop over product recommends
    for product in products:
        if(ix>3):
            break
        ix+=1
        results = find_product_by_search_keyword(product)
        res_json = json.loads(results)
        expected_output = res_json["search_results"][:1]
        emp_li = []
        ctr+=5
        progress_bar.progress(70+ctr)
        print("Products links for ", product)
        
        for li in expected_output:
            try:
                output_ads.append({"title": li['title'], "price": li['price']['raw'],
                                   "product_image": li['image'], "link": li['link']})
            except:
                pass
    print("Ads generated", output_ads)
    return output_ads


# Function connector -> nouns list , caption string , ads list based on s3 image_url


def generate_product_ads_for_url(image_url):
    print("Initiated request")
    nouns, caption, product_recommendations = generate_recommends(image_url)
    output_ads = get_product_ads(product_recommendations)
    progress_bar.progress(100)
    return nouns, caption, product_recommendations, output_ads

# Get User


def get_user(username):
    data = {'method': 'LOGIN_USER', 'userpk': 'user#'+username}
    res = requests.post(api_url, json=data)
    if res.status_code == 200:
        interests.append(res.json()['interests'])
        return True
    else:
        return False

# Register User


def register_user(username):
    if (get_user(username)):
        st.error('Username Taken')
        return False
    else:
        data = {'method': 'REGISTER_USER', 'userpk': 'user#'+username}
        res = requests.post(api_url, json=data)
        if res.status_code == 200:
            st.success('User Added')
            return True

# Get Posts paginated
def get_posts(start_idx, end_idx):
    posts = st.session_state.get('posts')
    return posts[start_idx:end_idx]

# List Posts
def load_posts():
    data = {'method': 'LIST_POSTS'}
    res = requests.post(api_url, json=data)
    posts = []
    for post in res.json():
        posts.append(post)
    st.session_state['posts'] = posts
    return posts

# Update Posts


def update_post(caption, pr, ads, postsk):
    data = {
        "method": "POST_RECOGNITION",
        "postsk": postsk,
        "caption": caption,
        "ad_links": ads,
        "recommends": pr
    }
    res = requests.post(api_url, json=data)
    print("Updated Post")

# Append to ads


def gen_ads_on_likes(post):
    print(post['ad_links']['N'])
    st.session_state['ads'] = post['ad_links']['N']
    print("Updated ads")

# Upload Image


def upload_file(image, filename, username):
    data = {'method': 'UPLOAD_POST', 'image': image, 'image_filename': filename,
            'postsk': filename, 'recognitions': [], 'username': username}
    res = requests.post(api_url, json=data)
    st.success("Image Uploaded")
    progress_bar.progress(20)
    post_item = res.json()
    recognitions, caption, pr, ads = generate_product_ads_for_url(
        post_item['image_link'])
    print("Image recognitions and recommendations", recognitions, caption)
    st.session_state['ads'] = ads
    update_post(caption, pr, ads, filename)
    load_posts()
    print("Loaded posts")

# Convert base64


def get_base64(image):
    # Open the image with Pillow
    img = Image.open(image)
    img = img.convert('RGB')

    # Convert the image to a bytes object
    with BytesIO() as output:
        img.save(output, format='JPEG')
        contents = output.getvalue()

    # Encode the bytes object as a base64 string and return it
    encoded = base64.b64encode(contents).decode('utf-8')
    return encoded

# Main app


def main_app():
    st.title('SocialLens')
    st.write('Your story, in pixels')
    page = st.sidebar.radio(
        'Navigation', ['Sign Up', 'Log In', 'Home', 'Data Analysis'])

    if page == 'Sign Up':
        new_username = st.text_input('New Username')
        if st.button('Sign Up'):
            register_user(new_username)

    elif page == 'Log In':
        username = st.text_input('Username')
        if st.button('Log In'):
            if get_user(username):
                st.session_state['user_exists'] = True
                st.session_state['username'] = username
                st.success('Logged in successfully')
                st.sidebar.success(f'Logged in as {username}')
            else:
                st.session_state['user_exists'] = False
                st.error('Invalid username')

    elif page == 'Home':
        start_idx = st.session_state.get('start_idx')
        end_idx = st.session_state.get('end_idx')
        username = st.session_state.get('username')
        if st.session_state.get('user_exists'):
            st.success(f'Welcome, {username}!')
            
            # if st.button("Make a Post"):
            uploaded_file = st.file_uploader(
                "Choose an image file", accept_multiple_files=False, type=['jpg', 'jpeg', 'png'])
            if uploaded_file is not None and not(st.session_state.get("not_uploaded")):
                img_data = uploaded_file.read()
                img = Image.open(io.BytesIO(img_data)).convert("RGB")
                converted_img_data = io.BytesIO()
                img.save(converted_img_data, format="JPEG")
                file_path = os.path.join('image.jpg')
                with open(file_path, "wb") as f:
                    f.write(converted_img_data.getvalue())
                print("here")
                file_name = 'img_' + str(uuid.uuid4()) + ".jpg"
                print(username)
                upload_file(get_base64(
                    uploaded_file), file_name, username)
                st.progress(0)
                st.session_state.not_uploaded = True

        st.write('Here are some recent posts:')
        load_posts()

        posts_to_display = get_posts(start_idx, end_idx)

        for post in posts_to_display:
            st.image(post['image_link'], use_column_width=True)
            st.write(f'Posted by @{post["username"]}')
            # st.write(f'Likes: {post["likes"]}')

            if st.button(f'❤️', key=post['sk']):
                if st.session_state.get('user_exists'):
                    likes.append(post)
                    gen_ads_on_likes(post)
                    # st.session_state['ads'].append(post.ads)
                    st.success('Post liked!')
                else:
                    st.error('Please log in to like posts.')

        # Implement infinite scroll
        if len(st.session_state.get('posts')) > end_idx:
            if st.button('Load More'):
                st.session_state['start_idx'] += 3
                st.session_state['end_idx'] += 3
            else:
                st.warning('Scroll down to load more posts...')

        # Implement ads row after scrolling past a certain number of posts
        if end_idx >= 2:
            st.write('Here are some ads:')
            ads = st.session_state.ads
            for ad in ads:
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.image(ad['product_image'], use_column_width=True)
                with col2:
                    st.write(f'Title: {ad["title"]}')
                    st.write(f'Price: {ad["price"]}')
                    ad_link = ad["link"]
                    st.write(f'''
                            <a target="_self" href={ad_link} target="_blank" rel="noopener noreferrer">
                                <button>
                                    Go To Amazon
                                </button>
                            </a>
                            ''',
                             unsafe_allow_html=True)


main_app()
