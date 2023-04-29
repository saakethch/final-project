import json
import boto3
import datetime
import base64


def lambda_handler(event, context):
    print(type(event))
    print(event)
    print("Event json %s" % json.dumps(event))
    print("Context %s" % context)
    client = boto3.resource('dynamodb')

    s3 = boto3.resource('s3')
    table = client.Table('adm-data')
    eventDateTime = (datetime.datetime.now()).strftime("%Y-%m-%d %H:%M:%S")

    event = json.loads(event['body'])

    # return {
    #             'statusCode': 404,
    #             'body': event['method'],
    #             "headers": {
    #         'Content-Type': 'application/json',
    #     }}
    if (event['method'] == "REGISTER_USER"):
        response = table.put_item(
            Item={
                'pk': event['userpk'],
                'sk': event['userpk'],
                'interests': [],
                'createdAt': eventDateTime,
            })
        return {
            'statusCode': response['ResponseMetadata']['HTTPStatusCode'],
            'body': "User Added",
            "headers": {
                'Content-Type': 'application/json',
            }

        }

    elif (event['method'] == "LOGIN_USER"):
        response = table.get_item(
            Key={
                'pk': event['userpk'],
                'sk': event['userpk']
            })
        item = response.get('Item')
        if item:
            return {
                'statusCode': 200,
                'body': item,
                "headers": {
                    'Content-Type': 'application/json',
                }
            }
        else:
            return {
                'statusCode': 404,
                'body': 'User not found',
                "headers": {
                    'Content-Type': 'application/json',
                }
            }

    elif (event['method'] == "LIST_POSTS"):
        response = table.scan(
            FilterExpression='#pk = :pk_val',
            ExpressionAttributeNames={
                '#pk': 'pk'
            },
            ExpressionAttributeValues={
                ':pk_val': "post"
            })
        return {
            'statusCode': response['ResponseMetadata']['HTTPStatusCode'],
            'body': response['Items'],
            "headers": {
                'Content-Type': 'text/html',
            }
        }

    elif (event['method'] == "GET_USER"):
        response = table.get_item(
            Key={
                'pk': event["userpk"],
                'sk': event["userpk"]
            })
        item = response['Item']
        return {
            'statusCode': response['ResponseMetadata']['HTTPStatusCode'],
            'body': item,
            "headers": {
                'Content-Type': 'text/html',
            }
        }
    elif (event['method'] == "ADD_INTERESTS"):
        response = table.get_item(
            Key={
                'pk': event["userpk"],
                'sk': event["userpk"]
            })
        item = response['Item']
        return {
            'statusCode': response['ResponseMetadata']['HTTPStatusCode'],
            'body': item,
            "headers": {
                'Content-Type': 'text/html',
            }
        }
    elif (event['method'] == "UPLOAD_POST"):
        image_data = event['image']
        image_binary_data = base64.b64decode(image_data)

        # Specify the S3 bucket name and image file name
        bucket_name = 'admmedia'
        image_file_name = "user_uploads/" + \
            event['image_filename']  # You can specify any file name

        # Upload the image to S3
        s3_client = boto3.client('s3')
        s3_client.put_object(
            Body=image_binary_data,
            Bucket=bucket_name,
            Key=image_file_name
        )
        item = {
            'pk': "post",
            'sk': event["postsk"],
            'image_link': "https://admmedia.s3.ap-south-1.amazonaws.com/user_uploads/"+event['image_filename'],
            'recommends': [],
            'caption': "",
            'ad_links': [],
            'username': event['username']
        }
        response = table.put_item(
            Item=item)
        return {
            'statusCode': response['ResponseMetadata']['HTTPStatusCode'],
            'body': item,
            "headers": {
                'Content-Type': 'text/html',
            }
        }
    elif (event['method'] == "POST_RECOGNITION"):
        key = {
            'pk': "post",
            'sk': event["postsk"]
        }

        # specify the attributes to update
        update_expression = 'SET #attr1 = :rec, #attr2 = :cap, #attr3 = :links '
        expression_attribute_names = {
            '#attr1': 'recommends', '#attr2': 'caption', '#attr3': 'ad_links'}
        expression_attribute_values = {':rec': {'S': event["recommends"]}, ':cap': {
            'N': event["caption"]}, ':links': {'N': event["ad_links"]}}

        # update the item in the table
        response = table.update_item(
            Key=key,
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
        )
        return {
            'statusCode': response['ResponseMetadata']['HTTPStatusCode'],
            'body': "post_updated",
            "headers": {
                'Content-Type': 'text/html',
            }
        }
    elif (event['method'] == "LIKE_POST"):
        response = table.get_item(
            Key={
                'pk': event["userpk"],
                'sk': event["postsk"],
            })
        item = response['Item']
        return {
            'statusCode': response['ResponseMetadata']['HTTPStatusCode'],
            'body': item,
            "headers": {
                'Content-Type': 'text/html',
            }
        }
    else:
        return {
            "statusCode": 404,
            "body": "Method not found",
            "headers": {
                    'Content-Type': 'text/html',
            }
        }
