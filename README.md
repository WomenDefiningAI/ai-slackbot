# Talk to an LLM in Slack (Slackbot template from WDAI)

A Slack bot that uses OpenAI's GPT-4o model to respond to messages, analyze images, process CSV data, and extract information from PDFs.  Originally created for the purposes of enabling more AI experiments in-channel for our Women Defining AI micro-learning program participants, this repo is a templatized version of our Slackbot implementation that is open so that others can build their own AI Slackbot

## Features
This template relies on OpenAI APIs for LLM capabiltiies, but you can continue to expand on these capabilities by integrating other LLM and providers for various features.
- **AI-Powered Conversations**: Responds to messages using OpenAI's GPT-4o model
- **Conversation Memory**: Maintains context by tracking conversation history in threads
- **Multi-Modal Capabilities**:
  - **Image Analysis**: Describes and answers questions about images
  - **Image Generation**: Creates custom images using DALL-E 3 based on text prompts
  - **CSV Processing**: Analyzes tabular data shared in CSV format
  - **PDF Extraction**: Extracts and summarizes content from PDF documents
  - **Text File Handling**: Processes plain text files

## Setup and Deployment

### Prerequisites

- Slack Workspace with Admin privileges
- OpenAI API Key
- Railway account (or other platform for deployment)
- GitHub account (for CI/CD)

### Environment Variables

- `SLACK_BOT_TOKEN`: Your Slack Bot User OAuth Token
- `SLACK_SIGNING_SECRET`: Your Slack App Signing Secret
- `OPENAI_API_KEY`: Your OpenAI API Key
- `MAX_THREAD_HISTORY` (optional): Maximum number of messages to retrieve from a thread (default: 10)
- `ALLOWED_CHANNEL` (optional): Channel ID where the bot is allowed to respond (if not set, bot works in all channels)

### ⚠️ Security Warning

**IMPORTANT**: Never commit your actual `.env` file or any file containing real API keys, tokens, or secrets to your repository. Only commit the `.env.example` file with placeholder values.

- **API Tokens**: If you accidentally expose your API tokens, immediately rotate them (create new ones and invalidate the old ones) in the respective dashboards.
- **Environment Variables**: Always use environment variables for sensitive information, especially in production.
- **Git Practices**: Make sure `.env` is included in your `.gitignore` file to prevent accidental commits.

### 🔒 Enhanced Security Features

#### PII Redaction in Logs

This bot includes an advanced logging system that automatically redacts personally identifiable information (PII) from log files, including:

- Email addresses
- IP addresses
- Phone numbers
- Social Security Numbers
- Credit card numbers
- API keys and tokens

This prevents sensitive information from being exposed in log files while still providing useful debugging information. All logs are stored in the `logs/bot_activity.log` file by default.

To configure logging behavior, you can set the following environment variables:
- `LOG_DIR`: Directory where logs will be stored (default: `logs`)
- `LOG_LEVEL`: Minimum log level to record (default: `INFO`)

### Installation

1. **Create a Slack App**:
   - Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app
   - Add the following Bot Token Scopes:
     - `app_mentions:read` - For reading when your bot is mentioned
     - `channels:history` - For viewing messages in public channels where the bot is added
     - `chat:write` - For sending messages as the bot
     - `files:read` - For viewing files shared with the bot
     - `files:write` - For uploading generated images to Slack
   - Install the app to your workspace

2. **Deploy the Bot**:
   - Clone this repository
   - Connect to Railway
   - Set the required environment variables
   - Deploy the application

3. **Configure Slack Event Subscriptions**:
   - Enable Events API
   - Set the Request URL to your deployed app's URL + `/slack/events`
   - Subscribe to the following bot events:
     - `message.channels`
     - `app_mention`

## Deployment on Railway

### Setting Up Railway

1. Create a [Railway](https://railway.app/) account if you don't have one.
2. Create a new project from your GitHub repository.
3. Set up the required environment variables:
   - In the Railway dashboard, go to your project
   - Click on the "Variables" tab
   - Add all the environment variables from your `.env.example` file:
     - `SLACK_BOT_TOKEN`
     - `SLACK_SIGNING_SECRET`
     - `OPENAI_API_KEY`
     - `MAX_THREAD_HISTORY` (optional)
     - `ALLOWED_CHANNEL` (optional)
     - `PORT` (Railway will set this automatically, but you can override it)
4. Deploy your application:
   - Railway will automatically deploy your application when you push to your repository
   - You can also manually deploy from the Railway dashboard

### Network Access Requirements

For certain features to work properly, your deployment environment needs:

- **File Storage**: For processing image generation results, the bot needs temporary file storage access.

If you're experiencing issues with these features, check your deployment platform's documentation about file system access.

### Slack Configuration for Deployed Bot

1. After deployment, Railway will provide you with a URL for your application
2. Copy this URL and go to your Slack App's settings
3. Under "Event Subscriptions", enable events and set the Request URL to:
   ```
   https://your-railway-app-url.railway.app/slack/events
   ```
4. Save changes and verify the URL

### Testing Your Deployment

1. Invite your bot to a channel in your Slack workspace
2. Mention the bot with a message
3. Check Railway logs if you encounter any issues

## Usage

### Basic Interaction

Mention the bot with `@Bot Name` in any channel it's invited to, or send it a direct message.

### Image Analysis

Attach an image to your message to have the bot analyze it:
```
@Bot Name What's in this image?
[image attachment]
```

### Image Generation

Ask the bot to create images with DALL-E 3:
```
@Bot Name generate an image of a cat riding a bicycle
```
or
```
@Bot Name create a funny meme about programming
```

### CSV Analysis

Attach a CSV file to have the bot analyze the data:
```
@Bot Name analyze this data please
[CSV attachment]
```

### PDF Processing

Share a PDF document for content extraction and summarization:
```
@Bot Name extract the key points from this document
[PDF attachment]
```

### Thread Conversations

The bot maintains context in threads, so you can have a continuous conversation by replying in a thread.

## Development

### Technology Stack

- **FastAPI**: Web framework
- **Slack SDK**: For Slack API integration
- **OpenAI API**: For AI capabilities
- **DALL-E 3**: For image generation
- **Railway**: Deployment platform

### Local Development

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up environment variables (use a `.env` file for local development)
4. Run the application:
   ```
   uvicorn app:app --reload
   ```
5. Use ngrok or a similar tool to create a public URL for testing with Slack

### Automated Quality Checks

This project includes automatic code quality and security checks that run whenever new code is submitted. These checks:

- Ensure the code follows standard formatting rules
- Scan for potential security issues
- Verify all dependencies are safe to use

This means you can be confident that the bot maintains high quality and security standards without needing to run technical tests yourself. This is enabled using Github actions. See python-checks.yml for more details.

### Requirements.txt

```
fastapi==0.110.0
slack-sdk==3.27.1
openai==1.64.0
pydantic==2.10.6
python-multipart==0.0.18
requests==2.32.3
uvicorn==0.29.0
matplotlib
pandas
pillow
```

## Limitations

- The bot can process files up to 25MB (Slack file size limit)
- PDF analysis quality depends on the document's formatting and clarity
- CSV parsing works best with well-formatted data
- The bot may have slower response times when processing large files
- Image generation follows OpenAI's content policy and may reject certain prompts

## License

MIT