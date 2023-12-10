# A Whatsapp Audio Messages Summarizer
I am not a big fan of Whatsapp Audio messages so I thought of using OPENAI APIs in order to transcribe and then summarize the audio messages I receive

## How it works
My code is deployed as an AWS lambda function written in Python. I have registered as a business user on whatsapp and I have registered my webhook to be called upon receipts of messages on a second phone number I own. This second number is the one registered as a business user. 

Each time I receive an audio message I forward it to my second phone number in order to trigger my wehbhook. The Lambda function will:

1. Call OPENAI's transcribe API
2. Call OPENAI's chat completion API
3. Send the result message to my first phone number

This is the basic schema behind it

![Sequence schema](https://github.com/endamaco/whatsappAudioSummarizer/blob/main/Whatsapp%20Summarizer.jpg)

## Setup Steps

In order to get the webhook working there a few steps required. The most important is to register on Meta Developer's website and then to register a Wahtsapp Business Number. Here are the summary of the steps I did.

### Register as a Meta Developer
Register as a Meta Developer at [website ](https://developers.facebook.com)

Once there click on *Create App* and compile the required info. Select *Other* as a Use Case and then select *Business*.

### Add Whatsapp Product to your App

After the creation of the app you will be prompted to select the products and you can add Whatsapp. If you don't have a business meta account you will be prompted to create one.

Deploy your webhook (for me it was on AWS Lambda). The webhook must be correctly running because it will be called by Meta to verify it at the Step n. 3 as described here.

On the interface you will be presented with some steps, I have followed them in the following order:
- **Step 1** Insert a phone number for testing purposes and verify it;
- **Step 2** Click on *Send Message* and you will receive a Whatsapp Message to the number provided at step 1
- **Step 5** Insert your business phone number (the number to which you will forward the audio messages). You will receive an sms to this number, so keep it handy
- **Step3** 
	- Go to Whatsapp -> API Setup and copy the temporary token to you env variable WHATSAPP_TOKEN
	- Create another environment variables with random string value and key VERIFY_TOKEN
	- Insert in the Step 3 of the whatsapp configuration your webhook url, in my case https://<id>.lambda-url.eu-central-1.on.aws/ and paste the VERIFY_TOKEN. Verify and save. Your webhook will be called providing the VERIFY_TOKEN and the query parameters *hub.verify_token* and *hub.challenge*
- Go to the *Basic* under *App Settings* page of your app dashboard on Meta developer console and copy the *app secret* value into the WHATSAPP_SECRET env variable

You can now test the first invocation to your webhook

### Whatsapp configuration

In order to generate a permanent access token I had to select the following scopes *business_management, whatsapp_business_management, whatsapp_business_messaging* following this [guide](https://developers.facebook.com/docs/whatsapp/business-management-api/get-started#1--acquire-an-access-token-using-a-system-user-or-facebook-login) 

From the meta developer page you can navigate to your app and then to *Webhook* page. Here you can subscribe to the *messages* event in order to subscribe your webhook to receive events each time a message is sent to your number.

## Takeaways

My AWS lambda function is configured with a 20 seconds timeout. This seems ok most of the times, but with audio messages > 2 minutes many times the function is not able to complete as most of the time is spent waiting for an answer from the *OPENAI's Transcribe API*. Please be aware that if the function is not able to process the response in time the Whatsapp API will try to contact again the webhook, and it will do so until it will receive a *200 - OK* response.


