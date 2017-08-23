# -*- coding: utf-8 -*-

# http://joelgrus.com/2015/12/30/polyglot-twitter-bot-part-3-python-27-aws-lambda/
# rubberduckydev
# WhereIsItBot

from __future__ import print_function
from twython import Twython
from twython.exceptions import TwythonError
import json
import re
import urllib, urllib2
import random
import boto3

with open('credentials-whatisitbot.json') as f:
    credentials = json.loads(f.read())

client = Twython(credentials["twitter"]["consumer_key"],
                  credentials["twitter"]["consumer_secret"],
                  credentials["twitter"]["access_token_key"],
                  credentials["twitter"]["access_token_secret"])
rekognition = boto3.client("rekognition")

query = '"what is this" -filter:retweets -filter:safe filter:images'
twitter_permalink_url_format = "https://twitter.com/{}/status/{}"

image_local_storage_location = "/tmp/image.jpg"

def handler(event, context):
    
    results = client.search(q=query, count=1)
    print("Found", len(results["statuses"]), "tweets matching search results")
    
    for tweet in results["statuses"]:
        
        original_tweet_text = tweet["text"]
        original_tweet_id = tweet['id_str']
        original_tweet_username = tweet['user']['screen_name']
        original_tweet_permalink = twitter_permalink_url_format.format(original_tweet_username, original_tweet_id)
        print("original tweet:", original_tweet_permalink)
        
        image_url = tweet['entities']['media'][0]['media_url']
        image_file_path = download_image(image_url)
        labels = detect_labels(image_local_storage_location)
        print("Detected labels: " + str(labels))
        new_tweet_text = build_tweet_text(original_tweet_username, original_tweet_permalink, labels)
        print("Publishing tweet: " + new_tweet_text)
        publish_tweet(new_tweet_text, image_file_path, original_tweet_id)
        
def download_image(address):
    print("original image url:", address)
    
    urllib.urlretrieve(address, image_local_storage_location)
    return image_local_storage_location

def build_tweet_text(username, original_tweet_permalink, labels):
    tweet_text = "You asked 'what is this'? I think it's: "
    for label in labels:
        proposed_tweet_text = add_label_to_tweet(tweet_text, label)
        if len(proposed_tweet_text) < 140:
            tweet_text = proposed_tweet_text
    tweet_text = tweet_text[:-2]
    tweet_text += "."
            
    return tweet_text + " " + original_tweet_permalink

def add_label_to_tweet(tweet_text, label):
    return tweet_text + label['Name'].lower() + " (" + str(int(label['Confidence'])) + "%), "

def publish_tweet(tweet_text, img_file_path, original_tweet_id):
    image = open(img_file_path, 'rb')
    
    print("publishing:", tweet_text)
    print("tweet size:", len(tweet_text))
    
    upload_response = client.upload_media(media=image)
    print("uploaded media")
    
    # banned (for automated replies and mentions?) https://support.twitter.com/articles/76915
    # instead, we will just echo text with the map and retweet url
    client.update_status(status=tweet_text, media_ids=[upload_response['media_id']])
    print("updated status")
    
def detect_labels(img_file_path, min_confidence=0):
    image_bytes = open(img_file_path, 'rb').read()
    response = rekognition.detect_labels(
        Image={
            "Bytes": image_bytes
        },
        MinConfidence=min_confidence
    )
    return response['Labels']
