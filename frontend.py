# Imports
import streamlit as st
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

# Function to download and save image locally
connection_parameters = json.load(open('connection.json'))
session = Session.builder.configs(connection_parameters).create()
api_key = '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'
openai.api_key = api_key


def download_image(image_url, save_folder):
    response = requests.get(image_url)
    image = Image.open(BytesIO(response.content)).convert('RGB')
    # os.mkdir(save_folder)
    file_path = os.path.join(save_folder, 'image.jpg')
    image.save(file_path)
    print("Image Downloaded")
    return file_path

# Function to call API and get caption


def get_caption_snowpark(image_path):
    # Connect Snowpark

    # Upload file to Snowpark
    session.file.put("./images/image.jpg", '@dash_models',
                     overwrite=True, auto_compress=False)
    session.add_packages(["transformers", "Pillow"])
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
    predicted_label = session.sql(
        '''SELECT image_caption_generator()''').collect()
    generated_caption = predicted_label[0][0]
    print("Generated Captions - ", generated_caption)
    return generated_caption

# Function to extract nouns from caption


def extract_nouns(caption):
    text = caption
    blob = TextBlob(text)
    nouns = [w for (w, pos) in blob.pos_tags if pos[0] == 'N']
    print(nouns, caption)
    return nouns, caption

# Function to get product recommendations based on nouns


def get_product_recommendations(nouns, caption):
    # Call API to get product recommendations based on nouns
    # Replace <API_KEY> with your actual API key
    concatinated_noun_str = {'nouns': ','.join(nouns)}
    emotion_recognition = "it is very important for you to understand the emotion of this line: " + caption

    prompt_instructions = f"Now Give some potential market product recommendations for the following items or the emotion you recognized: '{concatinated_noun_str}'"
    result_instructions = ", Result Intructions : give a single string seperated by commas, type nothing else."
    product_recommendations = []
    try:
        response = openai.Completion.create(
            prompt=emotion_recognition + prompt_instructions + result_instructions,
            engine="text-davinci-003",
            max_tokens=1024,
            n=1,
            stop=None
        )
        product_recommendations = response['choices'][0]['text']
        print("Generated Recommends - " + product_recommendations)
        product_recommendations = product_recommendations.strip().split(',')
    except Exception as e:
        print(f"Error extracting nouns: {e}")
    return product_recommendations


# Main function to download image, get caption, extract nouns, and get product recommendations
def generate_recommends(image_url):
    save_folder = 'images'
    image_path = download_image(image_url, save_folder)
    caption = get_caption_snowpark(image_path)
    nouns, caption = extract_nouns(caption)
    product_recommendations = get_product_recommendations(nouns, caption)
    os.remove(image_path)
    return nouns, caption, product_recommendations

# Amazon Scrapping


def find_product_by_search_keyword(search_term):
    params = {
        'api_key': 'ACE9F15B121149CBA47FA8E80B3C2AB8',  # replace with your api key
        'type': 'search',
        'amazon_domain': 'amazon.com',
        'search_term': search_term,
        'sort_by': 'price_low_to_high'
    }

    # make the http GET request to Rainforest API
    api_result = requests.get('https://api.rainforestapi.com/request', params)

    # print the JSON response from Rainforest API
    return json.dumps(api_result.json())


def get_product_ads(products):
    # result array
    output_ads = []

    # loop over products
    for product in products:
        results = find_product_by_search_keyword(product)
        res_json = json.loads(results)
        expected_output = res_json["search_results"][:5]
        emp_li = []
        for li in expected_output:
            try: 
                emp_li.append({"title": li['title'], "price": li['prices']['raw'],
                            "product_image": li['image'], "product_link": li['link']})
            except:
                continue
        res = {}
        res[product] = emp_li
        output_ads.append(res)

    return output_ads


def generate_product_ads_for_url(image_url):
    image_url = image_url
    nouns, caption, product_recommendations = generate_recommends(image_url)
    print(product_recommendations)
    output_ads = get_product_ads(product_recommendations)
    
    return nouns, caption, output_ads

# def load_ads_based_on_interests():
#     return ads


# Interests
interests = []

# Posts
posts = []
# Ads
ad_links = []
user_exists = False
url = 'https://4t6zjqbvra77cljo42ody4xtmi0smplq.lambda-url.us-east-1.on.aws/'
usern = ""
likes = []


def get_user(username):
    data = {'method': 'LOGIN_USER', 'userpk': 'user#'+username}
    res = requests.post(url, json=data)
    if res.status_code == 200:
        interests.append(res.json()['interests'])
        return True
    else:
        return False


def register_user(username):
    if (get_user(username)):
        st.error('Username Taken')
        return False
    else:
        data = {'method': 'REGISTER_USER', 'userpk': 'user#'+username}
        res = requests.post(url, json=data)
        if res.status_code == 200:
            st.success('User Added')
            return True

# Function to get posts with infinite scroll functionality
def get_posts(start_idx, end_idx):
    posts = st.session_state.get('posts')
    return posts[start_idx:end_idx]


def load_posts():
    data = {'method': 'LIST_POSTS'}
    res = requests.post(url, json=data)
    posts = []
    for post in res.json():
        posts.append(post)
    st.session_state['posts'] = posts
    return posts
    
def load_likes():
    data = {'method': 'LIST_LIKES'}
    res = requests.post(url, json=data)
    posts = []
    for post in res.json():
        posts.append(post)
    return posts


def upload_file(image, filename, username):
    data = {'method': 'UPLOAD_POST', 'image': image, 'image_filename': filename,
            'postsk': filename, 'recognitions': [], 'username': username}
    res = requests.post(url, json=data)
    st.success("Image Uploaded")
    post_item = res.json()
    recognitions, caption, ads = generate_product_ads_for_url(
        post_item['image_link'])
    # data = {'method': 'POST_ADS', 'links': ads, 'recognitions': recognitions,
    #         'caption': caption, 'postsk':post_item['sk']}
    # res = requests.post(url, json=data)
    print("Image recognitions and recommendations", recognitions, caption, ads)
    load_posts()
    st.session_state['ads'] = ads
    print("Loaded posts")
    


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


# def generate_ads_for_image(post):

#     # Streamlit app


def main_app():
    st.title('SocialLens')
    st.write('Your story, in pixels')
    page = st.sidebar.radio('Navigation', ['Sign Up', 'Log In', 'Home'])
    st.session_state['start_idx'] = 0
    st.session_state['end_idx'] = 3

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
        username = st.session_state.get('username')
        if st.session_state.get('user_exists'):
            st.success(f'Welcome, {username}!')
            st.write('Here are your liked posts:')

            liked_posts = []  # load_likes()

            for post in liked_posts:
                st.image(post['image_link'], use_column_width=True)
                st.write(f'By: @{post["username"]}')

            uploaded_file = st.file_uploader(
            "Choose an image file", accept_multiple_files=False)
            if uploaded_file is not None:
                file_name = 'img_' + str(uuid.uuid4()) + ".png"
                print(username)
                upload_file(get_base64(
                    uploaded_file), file_name, username)
                load_posts()
                posts_to_display = get_posts(start_idx, end_idx)

        st.write('Here are some recent posts:')
        load_posts()

        start_idx = st.session_state.get('start_idx', 0)
        end_idx = st.session_state.get('end_idx', 3)

        posts_to_display = get_posts(start_idx, end_idx)
        

        for post in posts_to_display:
            st.image(post['image_link'], use_column_width=True)
            st.write(f'Posted by @{post["username"]}')
            # st.write(f'Likes: {post["likes"]}')

            if st.button(f'<3', key=post['sk']):
                if st.session_state.get('user_exists'):
                    likes.append(post)
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
            ads = st.session_state.get('ads')
            for ad in ads:
                col1, col2 = st.beta_columns([1, 3])
                with col1:
                    st.image(ad['product_image'], use_column_width=True)
                with col2:
                    st.write(f'Title: {ad["title"]}')
                    st.write(f'Price: {ad["price"]}')


main_app()
